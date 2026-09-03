#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将新版可逆合并 CBZ 完整拆回原 CBZ，或将旧版数字分组合集兼容拆分。"""

from __future__ import annotations

import base64
import html
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path
from tkinter import Tk, filedialog, messagebox
from xml.etree import ElementTree as ET


MANIFEST_PATH = "META-INF/cbz-merge-manifest.json"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
SUPPORTED_COMPRESSION = {
    zipfile.ZIP_STORED,
    zipfile.ZIP_DEFLATED,
    zipfile.ZIP_BZIP2,
    zipfile.ZIP_LZMA,
}


def sanitize_filename(name: str, fallback: str) -> str:
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).rstrip(" .")
    if not name.casefold().endswith(".cbz"):
        name += ".cbz"
    return name or fallback


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def unique_dir(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.name} ({counter})")
        if not candidate.exists():
            return candidate
        counter += 1


def zipinfo_from_record(record: dict) -> zipfile.ZipInfo:
    filename = str(record.get("filename", ""))
    date_time = record.get("date_time", [1980, 1, 1, 0, 0, 0])
    try:
        date_tuple = tuple(int(value) for value in date_time[:6])
        info = zipfile.ZipInfo(filename, date_tuple)
    except Exception:
        info = zipfile.ZipInfo(filename)
    compression = int(record.get("compress_type", zipfile.ZIP_DEFLATED))
    info.compress_type = compression if compression in SUPPORTED_COMPRESSION else zipfile.ZIP_DEFLATED
    try:
        info.comment = base64.b64decode(record.get("comment_b64", ""))
    except Exception:
        info.comment = b""
    # 不复用原 ZIP extra，因其中可能含旧 Zip64 尺寸和偏移量。
    info.create_system = int(record.get("create_system", 0))
    info.create_version = int(record.get("create_version", 20))
    info.extract_version = int(record.get("extract_version", 20))
    info.internal_attr = int(record.get("internal_attr", 0))
    info.external_attr = int(record.get("external_attr", 0))
    if record.get("is_dir") and not info.filename.endswith("/"):
        info.filename += "/"
    return info


def validate_manifest(payload: dict) -> list[dict]:
    if payload.get("format") != "openai-cbz-reversible-merge":
        raise ValueError("拆分清单格式不受支持")
    if int(payload.get("version", 0)) != 1:
        raise ValueError(f"不支持的拆分清单版本：{payload.get('version')}")
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("拆分清单中没有原 CBZ 记录")
    return sources


def restore_reversible(source_path: Path, output_dir: Path, manifest: dict) -> list[Path]:
    sources = validate_manifest(manifest)
    outputs: list[Path] = []
    with zipfile.ZipFile(source_path, "r") as merged:
        available = set(merged.namelist())
        for position, source_record in enumerate(sources, 1):
            original_name = sanitize_filename(
                str(source_record.get("original_name", "")), f"{position:03d}.cbz"
            )
            output = unique_path(output_dir / original_name)
            members = source_record.get("members", [])
            if not isinstance(members, list) or not members:
                raise ValueError(f"第 {position} 项没有文件记录")
            print(f"[{position}/{len(sources)}] 还原：{original_name}（{len(members)} 项）", flush=True)
            try:
                with zipfile.ZipFile(output, "w", allowZip64=True) as restored:
                    try:
                        restored.comment = base64.b64decode(
                            source_record.get("zip_comment_b64", "")
                        )
                    except Exception:
                        restored.comment = b""
                    for member_index, record in enumerate(members, 1):
                        storage = record.get("storage")
                        info = zipinfo_from_record(record)
                        if storage == "directory":
                            restored.writestr(info, b"")
                            continue
                        data_name = (
                            record.get("merged_name") if storage == "mapped"
                            else record.get("stored_name") if storage == "stored"
                            else None
                        )
                        if not data_name or data_name not in available:
                            raise ValueError(
                                f"第 {position} 项缺少还原数据：{record.get('filename')}"
                            )
                        restored.writestr(info, merged.read(data_name))
                        if member_index % 100 == 0:
                            print(f"    {member_index}/{len(members)}", flush=True)
                with zipfile.ZipFile(output, "r") as check:
                    bad = check.testzip()
                    if bad:
                        raise ValueError(f"还原后 CRC 校验失败：{bad}")
                    expected_files = sum(not bool(item.get("is_dir")) for item in members)
                    actual_files = sum(not info.is_dir() for info in check.infolist())
                    if actual_files != expected_files:
                        raise ValueError(
                            f"还原后文件数不一致：{actual_files}/{expected_files}"
                        )
            except Exception:
                if output.exists():
                    output.unlink()
                raise
            outputs.append(output)
    return outputs


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def legacy_titles(archive: zipfile.ZipFile) -> list[str]:
    comicinfo = next(
        (
            name for name in archive.namelist()
            if Path(name.replace("\\", "/")).name.casefold() == "comicinfo.xml"
        ),
        None,
    )
    summary = ""
    if comicinfo:
        try:
            root = ET.fromstring(archive.read(comicinfo))
            for child in root:
                if local_name(child.tag).casefold() == "summary":
                    summary = "".join(child.itertext())
                    break
        except Exception:
            pass
    if not summary and archive.comment:
        try:
            summary = json.loads(archive.comment.decode("utf-8-sig")).get(
                "ComicBookInfo/1.0", {}
            ).get("comments", "")
        except Exception:
            pass
    summary = summary.replace("\\n", "\n")
    summary = re.sub(r"(?is)<br\s*/?>", "\n", summary)
    summary = re.sub(r"(?is)</?(?:p|div)[^>]*>", "\n", summary)
    summary = html.unescape(re.sub(r"(?is)<[^>]+>", "", summary))
    matches = list(re.finditer(r"(?m)^\s*(\d{1,3})\\?\.\s*(.+?)\s*$", summary))
    if matches:
        return [match.group(2).strip() for match in matches]
    # 兼容旧版中被 Calibre 折叠成单行的清单。
    candidates = list(re.finditer(r"(?<!\d)(\d{1,3})\\?\.\s*", summary))
    titles: list[str] = []
    for index, match in enumerate(candidates):
        end = candidates[index + 1].start() if index + 1 < len(candidates) else len(summary)
        titles.append(summary[match.end():end].strip())
    return titles


def xml_escape(value: str) -> str:
    return html.escape(value, quote=True)


def basic_comicinfo(title: str, pages: int) -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        f"  <Title>{xml_escape(title)}</Title>\n"
        f"  <Series>{xml_escape(title)}</Series>\n"
        f"  <Summary>从旧版数字分组合集拆分还原。</Summary>\n"
        f"  <PageCount>{pages}</PageCount>\n"
        "  <Manga>Yes</Manga>\n"
        "</ComicInfo>"
    ).encode("utf-8")


def basic_comment(title: str, pages: int) -> bytes:
    return json.dumps(
        {
            "ComicBookInfo/1.0": {
                "title": title,
                "series": title,
                "comments": "<p>从旧版数字分组合集拆分还原。</p>",
                "pageCount": pages,
            }
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def numeric_group(name: str) -> tuple[int, str] | None:
    normalized = name.replace("\\", "/")
    if "/" not in normalized:
        return None
    first = normalized.split("/", 1)[0]
    return (int(first), first) if first.isdigit() else None


def restore_legacy(source_path: Path, output_dir: Path) -> list[Path]:
    outputs: list[Path] = []
    with zipfile.ZipFile(source_path, "r") as merged:
        groups: dict[int, list[zipfile.ZipInfo]] = {}
        labels: dict[int, str] = {}
        for info in merged.infolist():
            group = numeric_group(info.filename)
            if group is not None and not info.is_dir():
                groups.setdefault(group[0], []).append(info)
                labels[group[0]] = group[1]
        if not groups:
            raise ValueError("未找到 001、002…数字子合集，无法兼容拆分")
        titles = legacy_titles(merged)
        cover = next(
            (info for info in merged.infolist() if Path(info.filename).name.casefold().startswith("000-cover.")),
            None,
        )
        ordered = sorted(groups)
        for position, number in enumerate(ordered, 1):
            title = titles[position - 1] if position <= len(titles) else f"第{labels[number]}项"
            output = unique_path(
                output_dir / sanitize_filename(title + ".cbz", f"{labels[number]}.cbz")
            )
            members = sorted(groups[number], key=lambda info: info.filename.casefold())
            print(f"[{position}/{len(ordered)}] 兼容拆分：{output.name}（{len(members)} 张）", flush=True)
            try:
                with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as restored:
                    page_count = 0
                    if position == 1 and cover is not None:
                        restored.writestr(Path(cover.filename).name, merged.read(cover))
                        page_count += 1
                    for info in members:
                        relative = info.filename.replace("\\", "/").split("/", 1)[1]
                        restored.writestr(relative, merged.read(info))
                        if Path(relative).suffix.casefold() in IMAGE_EXTS:
                            page_count += 1
                    restored.writestr("ComicInfo.xml", basic_comicinfo(title, page_count))
                    restored.comment = basic_comment(title, page_count)
                with zipfile.ZipFile(output, "r") as check:
                    bad = check.testzip()
                    if bad:
                        raise ValueError(f"CRC 校验失败：{bad}")
            except Exception:
                if output.exists():
                    output.unlink()
                raise
            outputs.append(output)
    return outputs


def choose_source() -> Path | None:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    selected = filedialog.askopenfilename(
        title="选择要拆分的合集 CBZ",
        filetypes=[("CBZ 漫画", "*.cbz"), ("所有文件", "*.*")],
    )
    root.destroy()
    return Path(selected) if selected else None


def choose_destination(source: Path) -> Path | None:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    selected = filedialog.askdirectory(
        title="选择拆分结果的保存位置", initialdir=str(source.parent)
    )
    root.destroy()
    if not selected:
        return None
    return unique_dir(Path(selected) / f"{source.stem} - 拆分还原")


def human_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}"
        size /= 1024
    return str(value)


def main() -> int:
    if os.name == "nt":
        os.system("chcp 65001 >nul")
    source = Path(sys.argv[1].strip('"')) if len(sys.argv) > 1 else choose_source()
    if source is None:
        print("已取消。")
        return 1
    source = source.resolve()
    if not source.is_file() or source.suffix.casefold() != ".cbz":
        print("[失败] 请选择有效的 CBZ。")
        return 1
    destination = choose_destination(source)
    if destination is None:
        print("已取消。")
        return 1

    required = source.stat().st_size + 128 * 1024 * 1024
    free = shutil.disk_usage(destination.parent).free
    print(f"合集：{source}")
    print(f"输出：{destination}")
    print(f"可用空间：{human_size(free)}；建议需要：{human_size(required)}")
    if free < required:
        print("[失败] 可用空间不足。")
        return 1

    with zipfile.ZipFile(source, "r") as archive:
        if MANIFEST_PATH in archive.namelist():
            manifest = json.loads(archive.read(MANIFEST_PATH).decode("utf-8"))
            sources = validate_manifest(manifest)
            mode = "完整还原"
            count = len(sources)
        else:
            manifest = None
            mode = "旧合集兼容拆分"
            count = len({numeric_group(name)[0] for name in archive.namelist() if numeric_group(name)})
    print(f"模式：{mode}；预计输出 {count} 个 CBZ")
    confirmation = input("输入 SPLIT 开始拆分：").strip()
    if confirmation != "SPLIT":
        print("已取消，未生成文件。")
        return 1

    destination.mkdir(parents=True, exist_ok=False)
    try:
        outputs = (
            restore_reversible(source, destination, manifest)
            if manifest is not None
            else restore_legacy(source, destination)
        )
    except Exception as exc:
        print(f"\n[失败] {type(exc).__name__}: {exc}")
        print(f"已完成的文件保留在：{destination}")
        return 1
    print(f"\n[成功] 已拆分 {len(outputs)} 个 CBZ：{destination}")
    if manifest is None:
        print("注意：这是旧合集兼容拆分，原元数据和丢失封面无法恢复。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n已取消。")
        raise SystemExit(130)
