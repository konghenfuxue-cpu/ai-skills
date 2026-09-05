#!/usr/bin/env python3
"""检查 EPUB 结构，并安全修复确定性的 ZIP 包装与 container.xml 问题。"""

from __future__ import annotations

import argparse
import copy
import posixpath
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET


MIMETYPE_NAME = "mimetype"
MIMETYPE_VALUE = b"application/epub+zip"
CONTAINER_NAME = "META-INF/container.xml"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"


@dataclass
class Finding:
    level: str
    code: str
    message: str
    repairable: bool = False


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def normalized_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def archive_name_map(archive: zipfile.ZipFile) -> dict[str, str]:
    return {normalized_name(info.filename): info.filename for info in archive.infolist()}


def resolve_href(opf_name: str, href: str) -> str | None:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    if not path:
        return None
    return posixpath.normpath(posixpath.join(posixpath.dirname(opf_name), path))


def parse_container(
    archive: zipfile.ZipFile, names: dict[str, str]
) -> tuple[list[str], list[Finding]]:
    actual = names.get(CONTAINER_NAME)
    if actual is None:
        return [], [Finding("ERROR", "container_missing", "缺少 META-INF/container.xml", True)]
    try:
        root = ET.fromstring(archive.read(actual))
    except Exception as exc:
        return [], [Finding("ERROR", "container_invalid", f"container.xml 无法解析：{exc}", True)]
    opfs = []
    for node in root.iter():
        if local_name(node.tag).casefold() == "rootfile":
            value = normalized_name(node.attrib.get("full-path", ""))
            if value:
                opfs.append(value)
    findings: list[Finding] = []
    if not opfs:
        findings.append(Finding("ERROR", "container_no_rootfile", "container.xml 没有 rootfile", True))
    for opf in opfs:
        if opf not in names:
            findings.append(Finding("ERROR", "opf_missing", f"容器指向不存在的 OPF：{opf}", True))
    return opfs, findings


def inspect_opf(
    archive: zipfile.ZipFile, opf_name: str, names: dict[str, str]
) -> list[Finding]:
    actual = names.get(opf_name)
    if actual is None:
        return []
    try:
        root = ET.fromstring(archive.read(actual))
    except Exception as exc:
        return [Finding("ERROR", "opf_invalid", f"OPF 无法解析 {opf_name}：{exc}")]

    findings: list[Finding] = []
    manifest: dict[str, tuple[str, str, str]] = {}
    for node in root.iter():
        if local_name(node.tag).casefold() != "item":
            continue
        item_id = node.attrib.get("id", "")
        href = node.attrib.get("href", "")
        if not item_id or not href:
            findings.append(Finding("ERROR", "manifest_item_invalid", "manifest 项缺少 id 或 href"))
            continue
        manifest[item_id] = (
            href,
            node.attrib.get("media-type", ""),
            node.attrib.get("properties", ""),
        )
        resolved = resolve_href(opf_name, href)
        if resolved is not None and resolved not in names:
            findings.append(
                Finding("ERROR", "manifest_target_missing", f"manifest 引用不存在：{href} -> {resolved}")
            )

    spine_nodes = [node for node in root.iter() if local_name(node.tag).casefold() == "spine"]
    if not spine_nodes:
        findings.append(Finding("ERROR", "spine_missing", f"OPF 缺少 spine：{opf_name}"))
    else:
        itemrefs = [
            node for node in spine_nodes[0]
            if local_name(node.tag).casefold() == "itemref"
        ]
        if not itemrefs:
            findings.append(Finding("ERROR", "spine_empty", f"spine 没有阅读项：{opf_name}"))
        for node in itemrefs:
            idref = node.attrib.get("idref", "")
            if not idref or idref not in manifest:
                findings.append(
                    Finding("ERROR", "spine_idref_missing", f"spine 引用未知 manifest ID：{idref or '(空)'}")
                )

    has_nav = any("nav" in properties.split() for _, _, properties in manifest.values())
    has_ncx = any(
        media_type == "application/x-dtbncx+xml"
        for _, media_type, _ in manifest.values()
    )
    if not has_nav and not has_ncx:
        findings.append(
            Finding("WARN", "navigation_missing", f"未发现 EPUB 3 nav 或 EPUB 2 NCX：{opf_name}")
        )
    return findings


def inspect_epub(path: Path) -> dict:
    if not path.is_file() or path.suffix.casefold() != ".epub":
        raise ValueError("请选择有效的 .epub 文件")
    findings: list[Finding] = []
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            names = archive_name_map(archive)
            folded: dict[str, list[str]] = {}
            for name in names:
                folded.setdefault(name.casefold(), []).append(name)
                if name.startswith("../") or "/../" in f"/{name}":
                    findings.append(Finding("ERROR", "unsafe_path", f"发现不安全路径：{name}"))
            for variants in folded.values():
                if len(variants) > 1:
                    findings.append(
                        Finding("ERROR", "case_collision", f"路径大小写冲突：{variants}")
                    )

            mime_info = next(
                (info for info in infos if normalized_name(info.filename) == MIMETYPE_NAME), None
            )
            if mime_info is None:
                findings.append(Finding("ERROR", "mimetype_missing", "缺少根目录 mimetype", True))
            else:
                if archive.read(mime_info) != MIMETYPE_VALUE:
                    findings.append(Finding("ERROR", "mimetype_value", "mimetype 内容不正确", True))
                if not infos or infos[0].filename != mime_info.filename:
                    findings.append(Finding("ERROR", "mimetype_order", "mimetype 不是 ZIP 第一个成员", True))
                if mime_info.compress_type != zipfile.ZIP_STORED:
                    findings.append(Finding("ERROR", "mimetype_compressed", "mimetype 必须不压缩存储", True))

            opfs, container_findings = parse_container(archive, names)
            findings.extend(container_findings)
            discovered_opfs = sorted(
                name for name in names if PurePosixPath(name).suffix.casefold() == ".opf"
            )
            valid_opfs = [name for name in opfs if name in names]
            if not valid_opfs and len(discovered_opfs) == 1:
                valid_opfs = discovered_opfs
            elif not valid_opfs and len(discovered_opfs) != 1:
                findings.append(
                    Finding("ERROR", "opf_ambiguous", f"无法唯一确定 OPF；发现 {len(discovered_opfs)} 个候选")
                )
            for opf in dict.fromkeys(valid_opfs):
                findings.extend(inspect_opf(archive, opf, names))

            if "META-INF/encryption.xml" in names:
                findings.append(
                    Finding("WARN", "encryption_present", "存在 encryption.xml；不会移除或绕过加密")
                )
            bad_member = archive.testzip()
            if bad_member:
                findings.append(Finding("ERROR", "crc_failure", f"ZIP CRC 校验失败：{bad_member}"))
            return {
                "path": path,
                "findings": findings,
                "opf_candidates": discovered_opfs,
                "member_count": len(infos),
            }
    except zipfile.BadZipFile as exc:
        raise ValueError(f"不是有效的 ZIP/EPUB：{exc}") from exc


def container_xml(opf_name: str) -> bytes:
    root = ET.Element("container", {"version": "1.0", "xmlns": CONTAINER_NS})
    rootfiles = ET.SubElement(root, "rootfiles")
    ET.SubElement(
        rootfiles,
        "rootfile",
        {"full-path": opf_name, "media-type": "application/oebps-package+xml"},
    )
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def unique_output(path: Path) -> Path:
    candidate = path.with_name(path.stem + "_已修复.epub")
    counter = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_已修复({counter}).epub")
        counter += 1
    return candidate


def repair_epub(source_path: Path, output_path: Path, report: dict) -> dict:
    container_codes = {"container_missing", "container_invalid", "container_no_rootfile", "opf_missing"}
    needs_container = any(item.code in container_codes for item in report["findings"])
    replacement_container = None
    if needs_container:
        if len(report["opf_candidates"]) != 1:
            raise ValueError("container.xml 需要修复，但无法唯一确定 OPF，已停止")
        replacement_container = container_xml(report["opf_candidates"][0])

    try:
        with zipfile.ZipFile(source_path, "r") as source, zipfile.ZipFile(
            output_path, "w", allowZip64=True
        ) as target:
            mime_info = zipfile.ZipInfo(MIMETYPE_NAME)
            mime_info.compress_type = zipfile.ZIP_STORED
            mime_info.external_attr = 0o600 << 16
            target.writestr(mime_info, MIMETYPE_VALUE)
            target.comment = source.comment
            for info in source.infolist():
                normalized = normalized_name(info.filename)
                if normalized == MIMETYPE_NAME:
                    continue
                if replacement_container is not None and normalized == CONTAINER_NAME:
                    continue
                new_info = copy.copy(info)
                new_info.orig_filename = new_info.filename
                if info.is_dir():
                    target.writestr(new_info, b"")
                else:
                    with source.open(info, "r") as src, target.open(new_info, "w") as dst:
                        shutil.copyfileobj(src, dst, length=1024 * 1024)
            if replacement_container is not None:
                info = zipfile.ZipInfo(CONTAINER_NAME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                target.writestr(info, replacement_container)
    except Exception:
        if output_path.exists():
            output_path.unlink()
        raise

    checked = inspect_epub(output_path)
    fatal_codes = {
        "mimetype_missing", "mimetype_value", "mimetype_order", "mimetype_compressed",
        "container_missing", "container_invalid", "container_no_rootfile", "opf_missing", "crc_failure",
    }
    if any(item.code in fatal_codes for item in checked["findings"]):
        output_path.unlink(missing_ok=True)
        raise ValueError("修复后包装或容器验证失败，输出已清理")
    return checked


def print_report(report: dict) -> None:
    print(f"文件：{report['path']}")
    print(f"ZIP 成员：{report['member_count']}")
    if not report["findings"]:
        print("[通过] 未发现结构问题。")
    for item in report["findings"]:
        suffix = "（可安全修复）" if item.repairable else ""
        print(f"[{item.level}] {item.code}: {item.message}{suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="检查并安全修复 EPUB 包装和基础结构")
    parser.add_argument("epub", help="EPUB 文件路径")
    parser.add_argument("--repair", action="store_true", help="生成修复后的新 EPUB")
    parser.add_argument("--output", help="指定修复输出路径")
    args = parser.parse_args()
    source = Path(args.epub.strip('"')).resolve()
    try:
        report = inspect_epub(source)
        print_report(report)
        if not args.repair:
            return 2 if any(item.level == "ERROR" for item in report["findings"]) else 0
        output = Path(args.output).resolve() if args.output else unique_output(source)
        if output == source:
            raise ValueError("不能覆盖原 EPUB，请指定其他输出路径")
        repaired = repair_epub(source, output, report)
        print(f"\n[完成] 已生成：{output}")
        unresolved = [item for item in repaired["findings"] if item.level == "ERROR"]
        if unresolved:
            print(f"仍有 {len(unresolved)} 个结构错误需要人工处理。")
            return 2
        print("修复后基础结构检查通过。")
        return 0
    except Exception as exc:
        print(f"[失败] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
