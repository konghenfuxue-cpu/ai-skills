#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计 CBZ 图片页数并写入 ComicInfo.xml 的 PageCount 与 Summary。"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp",
    ".tif", ".tiff", ".avif", ".jxl", ".heic", ".heif", ".svg",
}
BACKUP_DIR_NAME = "_CBZ元数据备份"
PAGE_LINE_RE = re.compile(
    r"(?im)^[ \t]*(?:页数|頁數|page[ \t]*count|pages?)[ \t]*[:：][ \t]*"
    r"\d+[ \t]*(?:页|頁)?[ \t]*$"
)
PAGE_HTML_RE = re.compile(
    r"(?is)<(?:p|div)[^>]*>\s*(?:页数|頁數|page\s*count|pages?)\s*[:：]\s*"
    r"\d+\s*(?:页|頁)?\s*</(?:p|div)>"
)
PAGE_TAIL_RE = re.compile(
    r"(?is)(?:^|\n)[ \t]*((?:页数|頁數|page[ \t]*count|pages?)[ \t]*[:：][ \t]*"
    r"\d+[ \t]*(?:页|頁)?)[ \t]*$"
)
INLINE_PAGE_TAIL_RE = re.compile(
    r"(?is)[ \t]+(?:页数|頁數|page[ \t]*count|pages?)[ \t]*[:：][ \t]*"
    r"\d+[ \t]*(?:页|頁)?[ \t]*$"
)
MERGED_LIST_HEADER_RE = re.compile(r"本合集按以下顺序合并[ \t]*[:：]")
MERGED_LIST_ENTRY_RE = re.compile(r"(?<!\d)(\d{1,3})\\?\.[ \t]*")


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


def is_page_image(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = normalized.split("/")
    if not normalized or normalized.endswith("/"):
        return False
    if "__MACOSX" in parts or any(part.startswith(".") for part in parts):
        return False
    return Path(parts[-1]).suffix.casefold() in IMAGE_EXTENSIONS


def normalize_merged_list(summary: str) -> str:
    """修复合并脚本曾写成单行的 01\\.、02\\.…条目。"""
    if re.search(r"(?is)<(?:p|div|br|ul|ol|li|table|blockquote|h[1-6])\b", summary):
        return summary
    header = MERGED_LIST_HEADER_RE.search(summary)
    if header is None:
        return summary

    tail = summary[header.end():]
    matches = list(MERGED_LIST_ENTRY_RE.finditer(tail))
    if len(matches) < 2:
        return summary

    # 只对从 0 或 1 开始且至少有两个连续编号的合集清单动手，
    # 避免把作品名中偶然出现的数字加句点误当成新条目。
    first_number = int(matches[0].group(1))
    second_number = int(matches[1].group(1))
    if first_number not in (0, 1) or second_number != first_number + 1:
        return summary

    intro = summary[:header.end()].strip()
    entries: list[str] = []
    expected = first_number
    accepted: list[re.Match[str]] = []
    for match in matches:
        number = int(match.group(1))
        if number == expected:
            accepted.append(match)
            expected += 1
    if len(accepted) < 2:
        return summary

    for index, match in enumerate(accepted):
        end = accepted[index + 1].start() if index + 1 < len(accepted) else len(tail)
        body = tail[match.end():end].strip()
        entries.append(f"{int(match.group(1)):02d}. {body}".rstrip())
    return intro + "\n" + "\n".join(entries)


def clean_and_append_page_count(summary: str | None, page_count: int) -> str:
    text = (summary or "").replace("\r\n", "\n").replace("\r", "\n")
    text = PAGE_HTML_RE.sub("", text)
    text = INLINE_PAGE_TAIL_RE.sub("", text)
    text = PAGE_LINE_RE.sub("", text)
    text = normalize_merged_list(text)
    text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text).strip()
    page_line = f"页数：{page_count} 页"
    return f"{text}\n\n{page_line}" if text else page_line


def calibre_comments_html(summary: str | None) -> str:
    """将 ComicInfo 的纯文本换行转成 Calibre 可显示的 HTML。

    Calibre 的 comments 字段按 HTML 渲染，普通 ``\n`` 会被浏览器折叠。
    若原内容已明显是 HTML，则保留原有标记。
    """
    text = (summary or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    tail = PAGE_TAIL_RE.search(text)
    page_line = tail.group(1).strip() if tail else ""
    body = text[:tail.start()].strip() if tail else text
    if re.search(r"(?is)<(?:p|div|br|ul|ol|li|table|blockquote|h[1-6])\b", text):
        return body + (f"<p>{html.escape(page_line)}</p>" if page_line else "")

    paragraphs = re.split(r"\n[ \t]*\n+", body)
    rendered = []
    for paragraph in paragraphs:
        lines = [html.escape(line.strip()) for line in paragraph.split("\n") if line.strip()]
        if lines:
            rendered.append(f"<p>{'<br/>'.join(lines)}</p>")
    if page_line:
        rendered.append(f"<p>{html.escape(page_line)}</p>")
    return "".join(rendered)


def read_comicinfo(zf: zipfile.ZipFile) -> tuple[ET.Element, set[str]]:
    comicinfo_names = {
        info.filename
        for info in zf.infolist()
        if Path(info.filename.replace("\\", "/")).name.casefold() == "comicinfo.xml"
    }
    if not comicinfo_names:
        return ET.Element("ComicInfo"), comicinfo_names

    preferred = min(comicinfo_names, key=lambda value: (value.count("/"), len(value)))
    try:
        root = ET.fromstring(zf.read(preferred))
        if local_name(root.tag).casefold() != "comicinfo":
            raise ValueError("根元素不是 ComicInfo")
        return root, comicinfo_names
    except Exception as exc:
        raise ValueError(f"ComicInfo.xml 无法解析：{exc}") from exc


def serialize_comicinfo(root: ET.Element) -> bytes:
    try:
        ET.indent(root, space="  ")
    except AttributeError:
        pass
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def xml_text(root: ET.Element, name: str) -> str:
    node = find_child(root, name)
    return (node.text or "").strip() if node is not None else ""


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


def build_comicbookinfo_comment(
    root: ET.Element, page_count: int, old_comment: bytes
) -> bytes:
    """生成供 Calibre 原生 CBZ 导入读取的 ZIP ComicBookInfo 注释。"""
    container = parse_comicbookinfo(old_comment)
    if container is None:
        container = {
            "appID": "CBZ PageCount Metadata Tool/1.3",
            "lastModified": datetime.now(timezone.utc).isoformat(),
            "ComicBookInfo/1.0": {},
        }
        if old_comment:
            container["originalZipComment"] = old_comment.decode("utf-8", errors="replace")
    else:
        container["lastModified"] = datetime.now(timezone.utc).isoformat()

    cbi = container["ComicBookInfo/1.0"]
    mapping = {
        "title": "Title",
        "series": "Series",
        "issue": "Number",
        "publisher": "Publisher",
        "genre": "Genre",
        "language": "LanguageISO",
    }
    for cbi_name, xml_name in mapping.items():
        value = xml_text(root, xml_name)
        if value and not cbi.get(cbi_name):
            cbi[cbi_name] = value

    integer_mapping = {
        "volume": "Volume",
        "numberOfIssues": "Count",
        "publicationYear": "Year",
        "publicationMonth": "Month",
    }
    for cbi_name, xml_name in integer_mapping.items():
        value = xml_text(root, xml_name)
        if value and not cbi.get(cbi_name):
            try:
                cbi[cbi_name] = int(value)
            except ValueError:
                pass

    tags = xml_text(root, "Tags")
    if tags and not cbi.get("tags"):
        cbi["tags"] = [item.strip() for item in re.split(r"[,，;；]", tags) if item.strip()]

    if not cbi.get("credits"):
        role_mapping = {
            "Writer": "Writer",
            "Penciller": "Penciller",
            "Inker": "Inker",
            "Colorist": "Colorist",
            "Letterer": "Letterer",
            "CoverArtist": "Cover",
            "Editor": "Editor",
            "Translator": "Translator",
        }
        credits = []
        for xml_name, role in role_mapping.items():
            value = xml_text(root, xml_name)
            for person in re.split(r"[,，;；]", value):
                if person.strip():
                    credits.append({"person": person.strip(), "role": role})
        if credits:
            cbi["credits"] = credits

    writer_value = xml_text(root, "Writer")
    if writer_value:
        writer_credits = [
            {"person": person.strip(), "role": "Writer"}
            for person in re.split(r"[,，;；]", writer_value)
            if person.strip()
        ]
        other_credits = [
            item for item in cbi.get("credits", [])
            if item.get("role") != "Writer"
        ]
        cbi["credits"] = writer_credits + other_credits

    cbi["comments"] = calibre_comments_html(xml_text(root, "Summary"))
    cbi["pageCount"] = page_count
    encoded = json.dumps(container, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > 65535:
        raise ValueError("Calibre ZIP 元数据超过 65535 字节，无法写入")
    return encoded


def unique_backup_path(cbz_path: Path) -> tuple[Path, bool]:
    backup_dir = cbz_path.parent / BACKUP_DIR_NAME
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / cbz_path.name
    return backup_path, backup_path.exists()


def update_cbz(
    cbz_path: Path, make_backup: bool = True, author: str | None = None
) -> tuple[int, str]:
    if not cbz_path.is_file():
        raise FileNotFoundError("文件不存在")
    if cbz_path.suffix.casefold() != ".cbz":
        raise ValueError("不是 CBZ 文件")

    with zipfile.ZipFile(cbz_path, "r") as source:
        bad_file = source.testzip()
        if bad_file:
            raise zipfile.BadZipFile(f"压缩包内文件损坏：{bad_file}")
        infos = source.infolist()
        page_count = sum(is_page_image(info.filename) for info in infos)
        if page_count <= 0:
            raise ValueError("未找到可统计的图片页面")
        root, old_comicinfo_names = read_comicinfo(source)
        cbi_container = parse_comicbookinfo(source.comment)
        if author and author.strip():
            writer = get_or_create_child(root, "Writer")
            writer.text = author.strip()
        summary = get_or_create_child(root, "Summary")
        base_summary = summary.text
        if not (base_summary or "").strip() and cbi_container is not None:
            base_summary = cbi_container["ComicBookInfo/1.0"].get("comments", "")
        summary.text = clean_and_append_page_count(base_summary, page_count)
        page_node = get_or_create_child(root, "PageCount")
        page_node.text = str(page_count)
        comicinfo_bytes = serialize_comicinfo(root)
        archive_comment = build_comicbookinfo_comment(root, page_count, source.comment)

        if make_backup:
            backup_path, existed = unique_backup_path(cbz_path)
            if not existed:
                shutil.copy2(cbz_path, backup_path)
            backup_message = "备份已存在，未覆盖" if existed else f"已备份到 {BACKUP_DIR_NAME}"
        else:
            backup_message = "未备份"

        fd, temp_name = tempfile.mkstemp(
            prefix=f".{cbz_path.stem}_", suffix=".tmp.cbz", dir=str(cbz_path.parent)
        )
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            with zipfile.ZipFile(temp_path, "w", allowZip64=True) as target:
                target.comment = archive_comment
                for info in infos:
                    if info.filename in old_comicinfo_names:
                        continue
                    target.writestr(info, source.read(info.filename))
                xml_info = zipfile.ZipInfo("ComicInfo.xml")
                xml_info.compress_type = zipfile.ZIP_DEFLATED
                xml_info.external_attr = 0o600 << 16
                target.writestr(xml_info, comicinfo_bytes)
            with zipfile.ZipFile(temp_path, "r") as check:
                if check.testzip() is not None:
                    raise zipfile.BadZipFile("更新后的 CBZ 校验失败")
                parsed = ET.fromstring(check.read("ComicInfo.xml"))
                stored = find_child(parsed, "PageCount")
                if stored is None or stored.text != str(page_count):
                    raise ValueError("更新后的 PageCount 校验失败")
                if author and xml_text(parsed, "Writer") != author.strip():
                    raise ValueError("更新后的 Writer 校验失败")
                cbi_check = parse_comicbookinfo(check.comment)
                if cbi_check is None or f"页数：{page_count} 页" not in cbi_check["ComicBookInfo/1.0"].get("comments", ""):
                    raise ValueError("更新后的 Calibre 简介元数据校验失败")
                if author:
                    writer_credits = {
                        item.get("person", "").strip()
                        for item in cbi_check["ComicBookInfo/1.0"].get("credits", [])
                        if item.get("role") == "Writer"
                    }
                    expected_writers = {
                        item.strip()
                        for item in re.split(r"[,，;；]", author)
                        if item.strip()
                    }
                    if not expected_writers.issubset(writer_credits):
                        raise ValueError("更新后的 Calibre 作者元数据校验失败")
            # Windows 不允许替换仍由当前进程打开的文件。
            # 提前关闭读取句柄；外层 with 退出时再次 close 是安全的。
            source.close()
            try:
                os.replace(temp_path, cbz_path)
            except PermissionError as exc:
                raise PermissionError(
                    "无法替换原 CBZ。请关闭 Calibre、漫画阅读器及可能正在使用该文件的程序后重试；"
                    "同时确认文件不是只读。"
                ) from exc
        finally:
            if temp_path.exists():
                temp_path.unlink()

    return page_count, backup_message


def collect_cbz(paths: list[str], recursive: bool) -> list[Path]:
    found: dict[str, Path] = {}
    for raw in paths:
        path = Path(raw.strip('"')).expanduser()
        if path.is_file() and path.suffix.casefold() == ".cbz":
            found[str(path.resolve()).casefold()] = path.resolve()
        elif path.is_dir():
            iterator = path.rglob("*.cbz") if recursive else path.glob("*.cbz")
            for item in iterator:
                if BACKUP_DIR_NAME not in item.parts:
                    found[str(item.resolve()).casefold()] = item.resolve()
    return sorted(found.values(), key=lambda value: str(value).casefold())


def choose_paths_with_gui() -> tuple[list[str], bool]:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except Exception:
        return [], False

    root = tk.Tk()
    root.withdraw()
    root.update()
    choose_folder = messagebox.askyesno(
        "CBZ 页数写入元数据",
        "是否批量处理一个文件夹？\n\n选择“是”：选择文件夹\n选择“否”：选择一个或多个 CBZ",
        parent=root,
    )
    recursive = False
    if choose_folder:
        selected = filedialog.askdirectory(title="选择包含 CBZ 的文件夹", parent=root)
        if selected:
            recursive = messagebox.askyesno(
                "是否包含子文件夹？", "是否同时扫描所有子文件夹？", parent=root
            )
            paths = [selected]
        else:
            paths = []
    else:
        paths = list(
            filedialog.askopenfilenames(
                title="选择一个或多个 CBZ",
                filetypes=[("CBZ 漫画", "*.cbz"), ("所有文件", "*.*")],
                parent=root,
            )
        )
    root.destroy()
    return paths, recursive


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="统计 CBZ 页数并写入 ComicInfo.xml")
    parser.add_argument("paths", nargs="*", help="CBZ 文件或文件夹，可传入多个")
    parser.add_argument("-r", "--recursive", action="store_true", help="递归扫描子文件夹")
    parser.add_argument("--no-backup", action="store_true", help="不创建原文件备份")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    paths = args.paths
    recursive = args.recursive
    if not paths:
        paths, recursive = choose_paths_with_gui()
    files = collect_cbz(paths, recursive)
    if not files:
        print("[提示] 没有选择或找到 CBZ 文件。")
        return 1

    print(f"共找到 {len(files)} 个 CBZ，开始处理……\n")
    success = 0
    failed = 0
    for index, path in enumerate(files, 1):
        try:
            page_count, backup_message = update_cbz(path, not args.no_backup)
            print(f"[{index}/{len(files)}] [成功] {path.name}｜{page_count} 页｜{backup_message}")
            success += 1
        except Exception as exc:
            print(f"[{index}/{len(files)}] [失败] {path}｜{exc}")
            failed += 1

    print(f"\n完成：成功 {success}，失败 {failed}。")
    if failed:
        print("失败文件保持原样；请查看上面的原因。")
    return 2 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n已取消。")
        raise SystemExit(130)
