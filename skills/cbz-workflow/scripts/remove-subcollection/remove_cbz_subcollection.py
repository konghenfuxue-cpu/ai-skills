#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从按数字顶层文件夹分组的 CBZ 大合集中安全删除一项。

默认生成新 CBZ，不覆盖原文件。同时更新 ComicInfo.xml 和
Calibre 使用的 ComicBookInfo ZIP 注释。
"""

from __future__ import annotations

import argparse
import copy
import html
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from tkinter import Tk, filedialog
from xml.etree import ElementTree as ET


IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp",
    ".tif", ".tiff", ".avif", ".jxl", ".heic", ".heif", ".svg",
}
COMICINFO_BASENAME = "comicinfo.xml"
MANIFEST_PATH = "META-INF/cbz-merge-manifest.json"
RESTORE_ROOT = ".cbz-restore"
PAGE_LINE_RE = re.compile(
    r"(?im)^[ \t]*(?:页数|頁數|page[ \t]*count|pages?)[ \t]*[:：][ \t]*"
    r"\d+[ \t]*(?:页|頁)?[ \t]*$"
)
INLINE_PAGE_TAIL_RE = re.compile(
    r"(?is)[ \t]+(?:页数|頁數|page[ \t]*count|pages?)[ \t]*[:：][ \t]*"
    r"\d+[ \t]*(?:页|頁)?[ \t]*$"
)
LIST_HEADER_RE = re.compile(r"本合集按以下顺序合并[ \t]*[:：]")
LIST_ENTRY_RE = re.compile(r"(?<!\d)(\d{1,3})\\?\.[ \t]*")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def find_child(root: ET.Element, name: str) -> ET.Element | None:
    wanted = name.casefold()
    for child in root:
        if local_name(child.tag).casefold() == wanted:
            return child
    return None


def get_or_create_child(root: ET.Element, name: str) -> ET.Element:
    child = find_child(root, name)
    if child is None:
        child = ET.SubElement(root, name)
    return child


def is_image(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if not normalized or normalized.endswith("/"):
        return False
    parts = normalized.split("/")
    if "__MACOSX" in parts or any(part.startswith(".") for part in parts):
        return False
    return Path(parts[-1]).suffix.casefold() in IMAGE_EXTENSIONS


def numeric_top_group(name: str) -> tuple[int, str] | None:
    normalized = name.replace("\\", "/")
    if "/" not in normalized:
        return None
    first = normalized.split("/", 1)[0]
    if not first.isdigit():
        return None
    return int(first), first


def renamed_path(name: str, target_number: int) -> str | None:
    """返回删除或重排后的路径；None 表示该项应删除。"""
    normalized = name.replace("\\", "/")
    group = numeric_top_group(normalized)
    if group is None:
        return normalized
    number, label = group
    if number == target_number:
        return None
    if number > target_number:
        suffix = normalized.split("/", 1)[1]
        new_label = str(number - 1).zfill(len(label))
        return new_label + "/" + suffix
    return normalized


def read_merge_manifest(zf: zipfile.ZipFile) -> tuple[dict | None, str | None]:
    """读取新版可逆合并清单；存在但损坏时停止，避免破坏还原能力。"""
    matches = [
        info.filename
        for info in zf.infolist()
        if info.filename.replace("\\", "/").casefold() == MANIFEST_PATH.casefold()
    ]
    if not matches:
        return None, None
    if len(matches) != 1:
        raise ValueError("发现多个可逆合并清单，为避免误改已停止")
    try:
        payload = json.loads(zf.read(matches[0]).decode("utf-8-sig"))
    except Exception as exc:
        raise ValueError(f"可逆合并清单无法解析，为保护还原元数据已停止：{exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("可逆合并清单不是 JSON 对象，为保护还原元数据已停止")
    if payload.get("format") != "openai-cbz-reversible-merge":
        raise ValueError("可逆合并清单格式不受支持，为保护还原元数据已停止")
    if int(payload.get("version", 0)) != 1:
        raise ValueError(f"不支持的可逆合并清单版本：{payload.get('version')}")
    if not isinstance(payload.get("sources"), list) or not payload["sources"]:
        raise ValueError("可逆合并清单中没有原 CBZ 记录")
    return payload, matches[0]


def update_merge_manifest(manifest: dict, target_number: int) -> dict:
    """删除对应来源，并同步清单中的位置、分组路径和还原区路径。"""
    sources = manifest["sources"]
    matches = [
        index
        for index, record in enumerate(sources)
        if str(record.get("folder", "")).isdigit()
        and int(record["folder"]) == target_number
    ]
    if len(matches) != 1:
        raise ValueError(
            f"可逆合并清单中应有且仅有一个分组 {target_number:03d}，实际找到 {len(matches)} 个"
        )

    removed_index = matches[0]
    updated = copy.deepcopy(manifest)
    removed_record = updated["sources"].pop(removed_index)
    removed_stored_names: set[str] = set()
    removed_mapped_names: set[str] = set()
    stored_renames: dict[str, str] = {}

    for member in removed_record.get("members", []):
        if member.get("storage") == "stored" and member.get("stored_name"):
            removed_stored_names.add(str(member["stored_name"]).replace("\\", "/"))
        elif member.get("storage") == "mapped" and member.get("merged_name"):
            removed_mapped_names.add(str(member["merged_name"]).replace("\\", "/"))

    for new_position, record in enumerate(updated["sources"], 1):
        old_position = int(record.get("position", new_position))
        record["position"] = new_position
        folder = str(record.get("folder", ""))
        if folder.isdigit() and int(folder) > target_number:
            record["folder"] = str(int(folder) - 1).zfill(len(folder))
        for member in record.get("members", []):
            if member.get("storage") == "mapped" and member.get("merged_name"):
                old_name = str(member["merged_name"]).replace("\\", "/")
                new_name = renamed_path(old_name, target_number)
                if new_name is None:
                    raise ValueError(f"剩余来源错误引用被删除分组：{old_name}")
                member["merged_name"] = new_name
            elif member.get("storage") == "stored" and member.get("stored_name"):
                old_name = str(member["stored_name"]).replace("\\", "/")
                prefix = f"{RESTORE_ROOT}/{old_position:03d}/"
                new_name = (
                    f"{RESTORE_ROOT}/{new_position:03d}/" + old_name[len(prefix):]
                    if old_name.startswith(prefix)
                    else old_name
                )
                member["stored_name"] = new_name
                if new_name != old_name:
                    stored_renames[old_name] = new_name

    return {
        "manifest": updated,
        "removed_record": removed_record,
        "removed_position": removed_index + 1,
        "removed_stored_names": removed_stored_names,
        "removed_mapped_names": removed_mapped_names,
        "stored_renames": stored_renames,
    }


def rewritten_member_path(name: str, target_number: int, manifest_update: dict | None) -> str | None:
    normalized = name.replace("\\", "/")
    if manifest_update is not None:
        if (
            normalized in manifest_update["removed_stored_names"]
            or normalized in manifest_update["removed_mapped_names"]
        ):
            return None
        renamed_stored = manifest_update["stored_renames"].get(normalized)
        if renamed_stored is not None:
            return renamed_stored
    return renamed_path(normalized, target_number)


class _HTMLToText(HTMLParser):
    BLOCKS = {"p", "div", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def _newline(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() == "br":
            self._newline()
        elif tag.casefold() in self.BLOCKS:
            self._newline()

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in self.BLOCKS:
            self._newline()

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def to_plain_text(value: str | None) -> str:
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    if re.search(r"(?is)<(?:p|div|br|ul|ol|li|table|blockquote|h[1-6])\b", text):
        parser = _HTMLToText()
        parser.feed(text)
        text = "".join(parser.parts)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def without_page_line(text: str) -> str:
    text = PAGE_LINE_RE.sub("", text)
    text = INLINE_PAGE_TAIL_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_collection_entries(text: str) -> tuple[str, list[str]] | None:
    """返回（清单标题之前的前缀，条目列表）。"""
    plain = without_page_line(to_plain_text(text))
    header = LIST_HEADER_RE.search(plain)
    if header is None:
        return None
    tail = plain[header.end():]
    candidates = list(LIST_ENTRY_RE.finditer(tail))
    if len(candidates) < 2:
        return None

    start_at = None
    for index, match in enumerate(candidates):
        if int(match.group(1)) in (0, 1):
            start_at = index
            break
    if start_at is None:
        return None

    accepted: list[re.Match[str]] = []
    expected = int(candidates[start_at].group(1))
    for match in candidates[start_at:]:
        number = int(match.group(1))
        if number == expected:
            accepted.append(match)
            expected += 1
    if len(accepted) < 2:
        return None

    entries: list[str] = []
    for index, match in enumerate(accepted):
        end = accepted[index + 1].start() if index + 1 < len(accepted) else len(tail)
        body = tail[match.end():end].strip()
        entries.append(re.sub(r"[ \t\n]+", " ", body).strip())
    prefix = plain[:header.end()].strip()
    return prefix, entries


def update_collection_summary(
    original: str | None, target_number: int, page_count: int
) -> tuple[str, str, bool]:
    parsed = split_collection_entries(original or "")
    page_line = f"页数：{page_count} 页"
    if parsed is None:
        base = without_page_line(to_plain_text(original))
        return (f"{base}\n\n{page_line}" if base else page_line), "", False

    prefix, entries = parsed
    # 合并清单通常从 01 开始，因此用户输入 16 对应第 16 个条目。
    index = target_number - 1
    if index < 0 or index >= len(entries):
        base = without_page_line(to_plain_text(original))
        return (f"{base}\n\n{page_line}" if base else page_line), "", False
    removed_title = entries[index]
    del entries[index]
    width = max(2, len(str(len(entries))))
    lines = [prefix]
    lines.extend(f"{number:0{width}d}. {entry}" for number, entry in enumerate(entries, 1))
    return "\n".join(lines) + f"\n\n{page_line}", removed_title, True


def calibre_html(summary: str) -> str:
    text = to_plain_text(summary)
    paragraphs = re.split(r"\n[ \t]*\n+", text)
    output: list[str] = []
    for paragraph in paragraphs:
        lines = [html.escape(line.strip()) for line in paragraph.split("\n") if line.strip()]
        if lines:
            output.append(f"<p>{'<br/>'.join(lines)}</p>")
    return "".join(output)


def parse_comicbookinfo(comment: bytes) -> dict | None:
    if not comment:
        return None
    try:
        data = json.loads(comment.decode("utf-8-sig"))
        if isinstance(data, dict) and isinstance(data.get("ComicBookInfo/1.0"), dict):
            return data
    except Exception:
        pass
    return None


def read_comicinfo(
    zf: zipfile.ZipFile,
) -> tuple[ET.Element, set[str], bool]:
    names = {
        info.filename
        for info in zf.infolist()
        if Path(info.filename.replace("\\", "/")).name.casefold() == COMICINFO_BASENAME
    }
    if not names:
        return ET.Element("ComicInfo"), names, False
    preferred = min(names, key=lambda value: (value.count("/"), len(value)))
    try:
        root = ET.fromstring(zf.read(preferred))
    except Exception as exc:
        raise ValueError(f"ComicInfo.xml 无法解析，为保护元数据已停止：{exc}") from exc
    if local_name(root.tag).casefold() != "comicinfo":
        raise ValueError("ComicInfo.xml 根元素不是 ComicInfo，为保护元数据已停止")
    return root, names, True


def update_pages_metadata(
    root: ET.Element,
    old_image_names: list[str],
    retained_image_names: list[str],
    target_number: int,
) -> tuple[int, int]:
    pages = find_child(root, "Pages")
    if pages is None:
        return 0, 0
    new_index = {name: index for index, name in enumerate(retained_image_names)}
    removed = 0
    reindexed = 0
    for page in list(pages):
        if local_name(page.tag).casefold() != "page":
            continue
        raw = page.attrib.get("Image")
        try:
            old_index = int(raw) if raw is not None else None
        except ValueError:
            old_index = None
        if old_index is None or old_index < 0 or old_index >= len(old_image_names):
            continue
        old_name = old_image_names[old_index]
        renamed = renamed_path(old_name, target_number)
        if renamed is None:
            pages.remove(page)
            removed += 1
            continue
        target_index = new_index.get(renamed)
        if target_index is not None and target_index != old_index:
            page.set("Image", str(target_index))
            reindexed += 1
    return removed, reindexed


def serialize_comicinfo(root: ET.Element) -> bytes:
    try:
        ET.indent(root, space="  ")
    except AttributeError:
        pass
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def updated_zip_comment(old_comment: bytes, summary: str, page_count: int) -> tuple[bytes, bool]:
    container = parse_comicbookinfo(old_comment)
    preserved_unknown = False
    if container is None:
        container = {
            "appID": "CBZ Subcollection Remover/1.0",
            "lastModified": datetime.now(timezone.utc).isoformat(),
            "ComicBookInfo/1.0": {},
        }
        if old_comment:
            container["originalZipComment"] = old_comment.decode("utf-8", errors="replace")
            preserved_unknown = True
    else:
        container["lastModified"] = datetime.now(timezone.utc).isoformat()
    cbi = container["ComicBookInfo/1.0"]
    cbi["comments"] = calibre_html(summary)
    cbi["pageCount"] = page_count
    encoded = json.dumps(container, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > 65535:
        raise ValueError("Calibre ZIP 元数据超过 65535 字节，无法安全写入")
    return encoded, preserved_unknown


def choose_cbz() -> Path | None:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    selected = filedialog.askopenfilename(
        title="选择要删除子合集的 CBZ",
        filetypes=[("CBZ 漫画", "*.cbz"), ("所有文件", "*.*")],
    )
    root.destroy()
    return Path(selected) if selected else None


def unique_output_path(source: Path, target_number: int) -> Path:
    base = source.with_name(f"{source.stem}_已删除第{target_number:03d}项.cbz")
    if not base.exists():
        return base
    counter = 2
    while True:
        candidate = source.with_name(
            f"{source.stem}_已删除第{target_number:03d}项({counter}).cbz"
        )
        if not candidate.exists():
            return candidate
        counter += 1


def human_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{value} B"


def writable_zipinfo(source: zipfile.ZipInfo, new_name: str) -> zipfile.ZipInfo:
    """复制安全的成员属性，不继承来源中可能过时的 ZIP64 标记。"""
    target = zipfile.ZipInfo(new_name, date_time=source.date_time)
    target.compress_type = source.compress_type
    target.comment = source.comment
    target.internal_attr = source.internal_attr
    target.external_attr = source.external_attr
    target.create_system = source.create_system
    target.create_version = source.create_version
    target.file_size = source.file_size
    # ZipFile.open 会按真实 file_size 自动决定是否需要 ZIP64。普通文件保持
    # extract_version=20，避免小型 CBZ 被错误标为“每个成员都需要 ZIP64”。
    target.extract_version = 20
    return target


def analyze(source_path: Path, target_number: int) -> dict:
    if not source_path.is_file() or source_path.suffix.casefold() != ".cbz":
        raise ValueError("请选择有效的 .cbz 文件")
    with zipfile.ZipFile(source_path, "r") as source:
        infos = source.infolist()
        manifest, manifest_name = read_merge_manifest(source)
        manifest_update = (
            update_merge_manifest(manifest, target_number) if manifest is not None else None
        )
        summary_item_number = (
            manifest_update["removed_position"]
            if manifest_update is not None else target_number
        )
        groups: dict[int, set[str]] = {}
        for info in infos:
            group = numeric_top_group(info.filename)
            if group is not None:
                groups.setdefault(group[0], set()).add(group[1])
        if target_number not in groups:
            available = ", ".join(f"{number:03d}" for number in sorted(groups))
            raise ValueError(
                f"未找到顶层数字分组 {target_number:03d}。\n"
                f"已识别分组：{available or '无'}"
            )
        if len(groups[target_number]) != 1:
            raise ValueError(
                f"数字 {target_number} 对应多个目录名：{sorted(groups[target_number])}"
            )
        target_label = next(iter(groups[target_number]))
        target_infos = [
            info for info in infos
            if (numeric_top_group(info.filename) or (-1, ""))[0] == target_number
        ]
        target_images = [info.filename for info in target_infos if is_image(info.filename)]
        if not target_images:
            raise ValueError(f"分组 {target_label} 内没有图片，为避免误删已停止")

        root, _, _ = read_comicinfo(source)
        summary_node = find_child(root, "Summary")
        summary = summary_node.text if summary_node is not None else ""
        cbi = parse_comicbookinfo(source.comment)
        if not (summary or "").strip() and cbi is not None:
            summary = str(cbi["ComicBookInfo/1.0"].get("comments", ""))
        parsed = split_collection_entries(summary or "")
        title = ""
        if parsed is not None and 0 < summary_item_number <= len(parsed[1]):
            title = parsed[1][summary_item_number - 1]

        old_image_names = [info.filename.replace("\\", "/") for info in infos if is_image(info.filename)]
        retained_names = []
        prospective_names: set[str] = set()
        for info in infos:
            if manifest_name is not None and info.filename == manifest_name:
                new_name = MANIFEST_PATH
            else:
                new_name = rewritten_member_path(
                    info.filename, target_number, manifest_update
                )
            if new_name is None:
                continue
            key = new_name.casefold()
            if key in prospective_names:
                raise ValueError(f"重排后会产生重名路径：{new_name}")
            prospective_names.add(key)
            if is_image(info.filename):
                retained_names.append(new_name)

        return {
            "infos": infos,
            "groups": sorted(groups),
            "target_label": target_label,
            "target_images": target_images,
            "target_file_count": len(target_infos),
            "title": title,
            "old_page_count": len(old_image_names),
            "new_page_count": len(retained_names),
            "old_image_names": old_image_names,
            "retained_image_names": retained_names,
            "manifest_name": manifest_name,
            "manifest_update": manifest_update,
            "summary_item_number": summary_item_number,
        }


def rewrite_cbz(source_path: Path, output_path: Path, target_number: int, analysis: dict) -> dict:
    with zipfile.ZipFile(source_path, "r") as source:
        infos = source.infolist()
        root, comicinfo_names, had_comicinfo = read_comicinfo(source)
        summary_node = get_or_create_child(root, "Summary")
        base_summary = summary_node.text or ""
        cbi = parse_comicbookinfo(source.comment)
        if not base_summary.strip() and cbi is not None:
            base_summary = str(cbi["ComicBookInfo/1.0"].get("comments", ""))

        new_page_count = int(analysis["new_page_count"])
        new_summary, removed_title, summary_updated = update_collection_summary(
            base_summary, int(analysis["summary_item_number"]), new_page_count
        )
        summary_node.text = new_summary
        get_or_create_child(root, "PageCount").text = str(new_page_count)
        removed_page_meta, reindexed_page_meta = update_pages_metadata(
            root,
            analysis["old_image_names"],
            analysis["retained_image_names"],
            target_number,
        )
        comicinfo_bytes = serialize_comicinfo(root)
        archive_comment, preserved_unknown_comment = updated_zip_comment(
            source.comment, new_summary, new_page_count
        )
        manifest_name = analysis.get("manifest_name")
        manifest_update = analysis.get("manifest_update")

        total_to_copy = sum(
            info.filename not in comicinfo_names
            and info.filename != manifest_name
            and rewritten_member_path(info.filename, target_number, manifest_update) is not None
            for info in infos
        )
        copied = 0
        try:
            with zipfile.ZipFile(output_path, "w", allowZip64=True) as target:
                target.comment = archive_comment
                for info in infos:
                    if info.filename in comicinfo_names:
                        continue
                    if info.filename == manifest_name:
                        continue
                    new_name = rewritten_member_path(
                        info.filename, target_number, manifest_update
                    )
                    if new_name is None:
                        continue
                    new_info = writable_zipinfo(info, new_name)
                    if info.is_dir():
                        target.writestr(new_info, b"")
                    else:
                        with source.open(info, "r") as src, target.open(
                            new_info, "w"
                        ) as dst:
                            shutil.copyfileobj(src, dst, length=1024 * 1024)
                    copied += 1
                    if copied % 100 == 0 or copied == total_to_copy:
                        print(f"  已写入 {copied}/{total_to_copy} 个文件……", flush=True)

                xml_info = zipfile.ZipInfo("ComicInfo.xml")
                xml_info.compress_type = zipfile.ZIP_DEFLATED
                xml_info.external_attr = 0o600 << 16
                target.writestr(xml_info, comicinfo_bytes)
                if manifest_update is not None:
                    manifest_info = zipfile.ZipInfo(MANIFEST_PATH)
                    manifest_info.compress_type = zipfile.ZIP_DEFLATED
                    manifest_info.external_attr = 0o600 << 16
                    target.writestr(
                        manifest_info,
                        json.dumps(
                            manifest_update["manifest"], ensure_ascii=False, indent=2
                        ).encode("utf-8"),
                    )
        except Exception:
            if output_path.exists():
                output_path.unlink()
            raise

    # 快速结构校验：不再全量解压一遍，避免大合集耗时翻倍。
    try:
        with zipfile.ZipFile(output_path, "r") as check:
            names = check.namelist()
            if len(names) != len({name.casefold() for name in names}):
                raise ValueError("输出 CBZ 存在重名路径")
            if any(
                (numeric_top_group(name) or (-1, ""))[0] == max(analysis["groups"])
                for name in names
            ) and max(analysis["groups"]) > target_number:
                raise ValueError("后续分组编号校验失败")
            image_count = sum(is_image(name) for name in names)
            if image_count != analysis["new_page_count"]:
                raise ValueError(
                    f"输出页数校验失败：应为 {analysis['new_page_count']}，实际 {image_count}"
                )
            parsed_root = ET.fromstring(check.read("ComicInfo.xml"))
            stored_count = find_child(parsed_root, "PageCount")
            if stored_count is None or stored_count.text != str(analysis["new_page_count"]):
                raise ValueError("ComicInfo.xml 页数校验失败")
            check_cbi = parse_comicbookinfo(check.comment)
            if check_cbi is None or check_cbi["ComicBookInfo/1.0"].get("pageCount") != analysis["new_page_count"]:
                raise ValueError("Calibre 元数据页数校验失败")
            if manifest_update is not None:
                checked_manifest, checked_name = read_merge_manifest(check)
                if checked_name != MANIFEST_PATH or checked_manifest is None:
                    raise ValueError("可逆合并清单写回校验失败")
                expected_sources = manifest_update["manifest"]["sources"]
                if checked_manifest.get("sources") != expected_sources:
                    raise ValueError("可逆合并清单内容校验失败")
                available = set(names)
                for source_record in expected_sources:
                    for member in source_record.get("members", []):
                        storage = member.get("storage")
                        data_name = (
                            member.get("merged_name") if storage == "mapped"
                            else member.get("stored_name") if storage == "stored"
                            else None
                        )
                        if data_name and data_name not in available:
                            raise ValueError(f"可逆还原数据缺失：{data_name}")
    except Exception:
        if output_path.exists():
            output_path.unlink()
        raise

    return {
        "removed_title": removed_title or analysis.get("title", ""),
        "summary_updated": summary_updated,
        "removed_page_meta": removed_page_meta,
        "reindexed_page_meta": reindexed_page_meta,
        "had_comicinfo": had_comicinfo,
        "preserved_unknown_comment": preserved_unknown_comment,
        "manifest_updated": manifest_update is not None,
        "removed_manifest_title": (
            manifest_update["removed_record"].get("display_title", "")
            if manifest_update is not None else ""
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="安全删除 CBZ 大合集中的指定数字分组")
    parser.add_argument("cbz", nargs="?", help="CBZ 文件路径")
    parser.add_argument("--item", type=int, help="要删除的项目编号，例如 16")
    args = parser.parse_args()

    source_path = Path(args.cbz.strip('"')) if args.cbz else choose_cbz()
    if source_path is None:
        print("已取消。")
        return 1
    source_path = source_path.resolve()

    target_number = args.item
    if target_number is None:
        raw = input("输入要删除的子合集编号 [16]：").strip() or "16"
        if not raw.isdigit() or int(raw) <= 0:
            print("[失败] 请输入大于 0 的整数。")
            return 1
        target_number = int(raw)
    if target_number <= 0:
        print("[失败] 项目编号必须大于 0。")
        return 1

    try:
        details = analyze(source_path, target_number)
    except Exception as exc:
        print(f"\n[失败] {exc}")
        return 1

    output_path = unique_output_path(source_path, target_number)
    source_size = source_path.stat().st_size
    free_space = shutil.disk_usage(source_path.parent).free
    required = source_size + 128 * 1024 * 1024

    print("\n" + "=" * 68)
    print("CBZ 删除指定子合集 - 执行前预览")
    print("=" * 68)
    print(f"原文件：{source_path}")
    print(f"目标数字分组：{details['target_label']}")
    print(f"作品名：{details['title'] or '简介中未识别到名称'}")
    print(f"将删除：{len(details['target_images'])} 张图片，{details['target_file_count']} 个文件")
    print(f"总页数：{details['old_page_count']} -> {details['new_page_count']}")
    if details["manifest_update"] is not None:
        removed_source = details["manifest_update"]["removed_record"]
        print(
            "可逆清单：将删除来源记录 "
            f"{removed_source.get('original_name') or removed_source.get('display_title') or details['target_label']}"
        )
        print(f"清单位置：第 {details['summary_item_number']} 项")
    print(f"新文件：{output_path}")
    print(f"原文件大小：{human_size(source_size)}")
    print(f"可用空间：{human_size(free_space)}")
    print("原 CBZ 不会被修改。")

    if free_space < required:
        print(
            f"\n[失败] 可用空间不足。建议至少保留 {human_size(required)} 空间。"
        )
        return 1

    confirmation = input(f"\n确认删除上述第 {target_number} 项，请输入 DELETE：").strip()
    if confirmation != "DELETE":
        print("已取消，未修改任何文件。")
        return 1

    print("\n开始生成新 CBZ，请不要关闭窗口……")
    try:
        result = rewrite_cbz(source_path, output_path, target_number, details)
    except Exception as exc:
        print(f"\n[失败] {exc}")
        print("输出不完整文件已清理，原 CBZ 保持不变。")
        return 1

    print("\n" + "=" * 68)
    print("[成功] 已生成新 CBZ")
    print(f"输出：{output_path}")
    print(f"已删除：{result['removed_title'] or details['target_label']}")
    print(f"页数：{details['old_page_count']} -> {details['new_page_count']}")
    print(f"简介清单：{'已删除指定项并重新编号' if result['summary_updated'] else '未识别标准清单，仅更新页数'}")
    print(
        "可逆清单："
        + (
            "已删除对应来源记录并重排还原路径"
            if result["manifest_updated"]
            else "原文件不含新版可逆合并清单"
        )
    )
    print(
        f"页面索引：删除 {result['removed_page_meta']} 条，"
        f"重排 {result['reindexed_page_meta']} 条"
    )
    print("请先用 OpenComic 检查新文件，确认后再替换 Calibre 中的 CBZ。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n已取消，原 CBZ 保持不变。")
        raise SystemExit(130)
