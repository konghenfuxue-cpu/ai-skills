from __future__ import annotations

import base64
import copy
import html
import json
import os
import re
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, simpledialog
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
MANIFEST_PATH = "META-INF/cbz-merge-manifest.json"
RESTORE_ROOT = ".cbz-restore"
CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


class ProgressLog:
    """同时把进度写到控制台和 UTF-8-BOM 日志，便于 Windows 记事本查看。"""

    def __init__(self, path: Path):
        self.path = path
        self.started = time.monotonic()
        self.file = path.open("w", encoding="utf-8-sig", newline="\n")

    def write(self, message: str = ""):
        elapsed = time.monotonic() - self.started
        line = f"[{elapsed:8.1f}s] {message}"
        print(line, flush=True)
        self.file.write(line + "\n")
        self.file.flush()

    def close(self):
        self.file.close()


def cn_number(text: str) -> int | None:
    if text.isdigit():
        return int(text)
    if text == "十":
        return 10
    if "十" in text:
        left, right = text.split("十", 1)
        tens = CN_DIGITS.get(left, 1) if left else 1
        ones = CN_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    if len(text) == 1:
        return CN_DIGITS.get(text)
    return None


def chapter_number(path: Path) -> int | None:
    match = re.search(r"第\s*([0-9零〇一二两三四五六七八九十]+)\s*[话話章回]", path.stem)
    return cn_number(match.group(1)) if match else None


def natural_key(path: Path):
    chapter = chapter_number(path)
    if chapter is not None:
        return (0, chapter, path.name.casefold())
    parts = re.split(r"(\d+)", path.name.casefold())
    return (1, tuple(int(p) if p.isdigit() else p for p in parts))


def image_members(zf: ZipFile):
    names = []
    for info in zf.infolist():
        if info.is_dir() or Path(info.filename).suffix.lower() not in IMAGE_EXTS:
            continue
        if Path(info.filename).name.casefold().startswith(("000-cover.", "cover.")):
            continue
        names.append(info)
    return sorted(names, key=lambda x: natural_name_key(x.filename))


def natural_name_key(name: str):
    return tuple(int(p) if p.isdigit() else p.casefold() for p in re.split(r"(\d+)", name))


def find_cover(zf: ZipFile):
    images = [i for i in zf.infolist() if not i.is_dir() and Path(i.filename).suffix.lower() in IMAGE_EXTS]
    for info in images:
        if Path(info.filename).name.casefold().startswith(("000-cover.", "cover.")):
            return info
    return sorted(images, key=lambda x: natural_name_key(x.filename))[0] if images else None


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def source_title(zf: ZipFile, source: Path) -> str:
    """优先读取 CBZ 内部完整标题，避免 Calibre 导出文件名被截断。"""
    comicinfo_names = [
        info.filename for info in zf.infolist()
        if Path(info.filename.replace("\\", "/")).name.casefold() == "comicinfo.xml"
    ]
    if comicinfo_names:
        preferred = min(comicinfo_names, key=lambda value: (value.count("/"), len(value)))
        try:
            root = ET.fromstring(zf.read(preferred))
            for child in root:
                if local_name(child.tag).casefold() == "title" and (child.text or "").strip():
                    return child.text.strip()
        except Exception:
            pass
    if zf.comment:
        try:
            payload = json.loads(zf.comment.decode("utf-8-sig"))
            title = payload.get("ComicBookInfo/1.0", {}).get("title", "")
            if isinstance(title, str) and title.strip():
                return title.strip()
        except Exception:
            pass
    # Calibre 单文件夹导出常用“ID - 书名 - 作者”；只去掉开头的数字 ID。
    return re.sub(r"^\d+\s+-\s+", "", source.stem).strip()


def build_summary(titles: list[str]) -> str:
    summary_lines = ["本合集按以下顺序合并："]
    summary_lines.extend(f"{index:02d}. {title}" for index, title in enumerate(titles, 1))
    return "\n".join(summary_lines)


def append_page_count(summary: str, pages: int) -> str:
    """把页数追加到简介，供 Calibre/CLiB 在书籍详情中直接显示。"""
    text = summary.replace("\r\n", "\n").replace("\r", "\n").rstrip()
    return f"{text}\n\n页数：{pages} 页" if text else f"页数：{pages} 页"


def comic_info(title: str, summary: str, pages: int) -> bytes:
    """Create standard ComicInfo.xml metadata for comic readers."""
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Title>{xml_escape(title)}</Title>
  <Series>{xml_escape(title)}</Series>
  <Summary>{xml_escape(summary)}</Summary>
  <PageCount>{pages}</PageCount>
  <Manga>Yes</Manga>
</ComicInfo>'''
    return xml.encode("utf-8")


def calibre_zip_comment(title: str, summary: str, pages: int) -> bytes:
    """Create the ComicBookInfo JSON that Calibre reads from a CBZ ZIP comment."""
    def encode(value: str) -> bytes:
        payload = {
            "ComicBookInfo/1.0": {
                "title": title,
                "series": title,
                "comments": "<p>" + "<br/>".join(
                    html.escape(line) for line in value.splitlines()
                ) + "</p>",
                "pageCount": pages,
            }
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    comment = encode(summary)
    # ZIP comments are limited to 65535 bytes. Keep valid JSON even for huge selections.
    if len(comment) > 65535:
        suffix = "\n……合并清单过长，Calibre 简介已截断；ComicInfo.xml 中仍保留完整清单。"
        keep = summary
        while keep and len(encode(keep + suffix)) > 65535:
            keep = keep[:-200]
        comment = encode(keep.rstrip() + suffix)
    return comment


def zipinfo_record(info) -> dict:
    return {
        "filename": info.filename,
        "date_time": list(info.date_time),
        "compress_type": info.compress_type,
        "comment_b64": base64.b64encode(info.comment or b"").decode("ascii"),
        "extra_b64": base64.b64encode(info.extra or b"").decode("ascii"),
        "create_system": info.create_system,
        "create_version": info.create_version,
        "extract_version": info.extract_version,
        "flag_bits": info.flag_bits,
        "volume": info.volume,
        "internal_attr": info.internal_attr,
        "external_attr": info.external_attr,
        "is_dir": info.is_dir(),
    }


def xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def validate_cbz(path: Path, log: ProgressLog):
    """逐项校验 CRC，并定期报告进度，避免 testzip() 长时间无输出。"""
    with ZipFile(path) as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        total = len(members)
        log.write(f"开始完整校验：共 {total} 个文件（此阶段会重新读取整个合集）")
        for index, info in enumerate(members, 1):
            try:
                with archive.open(info) as source:
                    while source.read(1024 * 1024):
                        pass
            except (BadZipFile, OSError, RuntimeError) as exc:
                raise RuntimeError(f"压缩包校验失败：{info.filename}：{exc}") from exc
            if index == total or index % 100 == 0:
                log.write(f"校验进度：{index}/{total}（{index / total:.0%}）")


def copy_member_streaming(out: ZipFile, target_name: str, source: ZipFile, info) -> None:
    """以固定缓冲区复制一个成员，避免大图一次读入内存。"""
    # ZipFile 无法预先推断用字符串名称创建的超大成员尺寸；大成员明确
    # 请求 ZIP64，小成员保持普通 ZIP 成员以兼容更多漫画阅读器。
    force_zip64 = info.file_size >= (1 << 31) - 1
    with source.open(info, "r") as input_file, out.open(
        target_name, "w", force_zip64=force_zip64
    ) as output_file:
        shutil.copyfileobj(input_file, output_file, length=1024 * 1024)


def merge_cbz(inputs: list[Path], output: Path, title: str, log: ProgressLog):
    inputs = sorted(inputs, key=natural_key)
    page_total = 0
    source_titles: list[str] = []
    for source in inputs:
        with ZipFile(source) as archive:
            source_titles.append(source_title(archive, source))
    summary = build_summary(source_titles)
    manifest = {
        "format": "openai-cbz-reversible-merge",
        "version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "merged_title": title,
        "sources": [],
    }
    log.write(f"开始合并：{len(inputs)} 个 CBZ")
    log.write(f"输出文件：{output}")
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=6, allowZip64=True) as out:
        first_cover_name = ""
        first_cover_info = None
        with ZipFile(inputs[0]) as first:
            cover = find_cover(first)
            if cover:
                first_cover_name = "000-cover" + Path(cover.filename).suffix.lower()
                first_cover_info = cover.filename
                copy_member_streaming(out, first_cover_name, first, cover)
                log.write(f"已写入封面：{inputs[0].name} -> {cover.filename}")
        for position, (source, display_title) in enumerate(zip(inputs, source_titles), 1):
            chapter = chapter_number(source)
            folder = f"{chapter:03d}" if chapter is not None else f"{position:03d}"
            with ZipFile(source) as src:
                images = image_members(src)
                image_ids = {id(info): page for page, info in enumerate(images, 1)}
                source_record = {
                    "position": position,
                    "folder": folder,
                    "original_name": source.name,
                    "display_title": display_title,
                    "zip_comment_b64": base64.b64encode(src.comment or b"").decode("ascii"),
                    "members": [],
                }
                log.write(f"[{position}/{len(inputs)}] 正在处理：{source.name}（{len(images)} 张）")
                for member_index, info in enumerate(src.infolist(), 1):
                    record = zipinfo_record(info)
                    if info.is_dir():
                        record["storage"] = "directory"
                    elif id(info) in image_ids:
                        page = image_ids[id(info)]
                        suffix = Path(info.filename).suffix.lower()
                        merged_name = f"{folder}/{page:04d}{suffix}"
                        copy_member_streaming(out, merged_name, src, info)
                        record["storage"] = "mapped"
                        record["merged_name"] = merged_name
                        page_total += 1
                        if page % 100 == 0:
                            log.write(f"    当前文件：{page}/{len(images)}；累计 {page_total} 张")
                    elif position == 1 and first_cover_info and info.filename == first_cover_info:
                        # 第一本的显式封面已作为合集封面写入，无需再存一份。
                        record["storage"] = "mapped"
                        record["merged_name"] = first_cover_name
                    else:
                        # 其他封面、ComicInfo.xml 和小型附加文件放到阅读器忽略的还原区。
                        stored_name = f"{RESTORE_ROOT}/{position:03d}/{member_index:06d}.bin"
                        copy_member_streaming(out, stored_name, src, info)
                        record["storage"] = "stored"
                        record["stored_name"] = stored_name
                    source_record["members"].append(record)
                log.write(f"[{position}/{len(inputs)}] 已完成：{source.name}；累计 {page_total} 张")
                manifest["sources"].append(source_record)
        # 同时兼容两种元数据：其他漫画阅读器读 ComicInfo.xml，
        # Calibre 原生导入 CBZ 时读 ZIP comment 中的 ComicBookInfo JSON。
        actual_pages = page_total + (1 if first_cover_name else 0)
        metadata_summary = append_page_count(summary, actual_pages)
        out.writestr("ComicInfo.xml", comic_info(title, metadata_summary, actual_pages))
        out.writestr(
            MANIFEST_PATH,
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        out.comment = calibre_zip_comment(title, metadata_summary, actual_pages)
    log.write("图片和元数据写入完成，准备校验。")
    validate_cbz(output, log)
    log.write(
        f"全部完成：{len(inputs)} 个 CBZ，{page_total} 张正文图片；"
        f"元数据页数 {actual_pages} 页，已写入简介、PageCount 和可逆拆分清单。"
    )
    return inputs, page_total


def main():
    if os.name == "nt":
        os.system("chcp 65001 >nul")
    root = Tk()
    root.withdraw()
    selected = filedialog.askopenfilenames(title="选择要合并的 CBZ（可按 Ctrl/Shift 多选）",
                                           filetypes=[("CBZ 漫画", "*.cbz")])
    if len(selected) < 2:
        messagebox.showinfo("未合并", "请至少选择两个 CBZ 文件。")
        return 0
    inputs = [Path(p) for p in selected]
    default_title = re.sub(r"\s*第\s*[0-9零〇一二两三四五六七八九十]+\s*[话話章回].*$", "", inputs[0].stem).strip()
    title = simpledialog.askstring("合集名称", "请输入合并后的书名：", initialvalue=default_title, parent=root)
    if not title:
        return 0
    target = filedialog.asksaveasfilename(title="保存合并后的 CBZ", defaultextension=".cbz",
                                          initialfile=title + " - 合集.cbz",
                                          filetypes=[("CBZ 漫画", "*.cbz")])
    if not target:
        return 0
    target_path = Path(target)
    log_path = target_path.with_name(target_path.stem + " - 合并日志.txt")
    log = ProgressLog(log_path)
    try:
        ordered, pages = merge_cbz(inputs, target_path, title, log)
    except Exception as exc:
        log.write("合并失败：" + f"{type(exc).__name__}: {exc}")
        log.file.write("\n" + traceback.format_exc())
        log.file.flush()
        messagebox.showerror(
            "合并失败",
            f"{type(exc).__name__}: {exc}\n\n详细记录：{log_path}",
            parent=root,
        )
        return 1
    finally:
        log.close()
    messagebox.showinfo(
        "合并完成",
        f"共 {len(ordered)} 个 CBZ、{pages} 张正文图片。\n"
        "页数已自动写入合集简介和 PageCount（不生成备份）。\n\n"
        f"输出：{target}\n日志：{log_path}",
        parent=root,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        try:
            error_root = Tk()
            error_root.withdraw()
            messagebox.showerror("CBZ 合并工具启动失败", message)
            error_root.destroy()
        except Exception:
            print("[ERROR] " + message)
            input("Press Enter to close...")
        raise SystemExit(1)
