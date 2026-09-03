from __future__ import annotations

import io
import os
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import jmcomic
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from zhconv import convert

# Skill 仓库中页数工具保存在相邻目录；只引用唯一正式版本，避免维护重复副本。
PAGECOUNT_TOOL_DIR = Path(__file__).resolve().parent.parent / "pagecount-metadata"
if not (PAGECOUNT_TOOL_DIR / "cbz_pagecount_metadata.py").is_file():
    raise ImportError(f"未找到页数元数据工具：{PAGECOUNT_TOOL_DIR}")
sys.path.insert(0, str(PAGECOUNT_TOOL_DIR))

from cbz_pagecount_metadata import update_cbz


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
NOTICE_RE = re.compile(
    r"休[刊載载]|停[更刊]|公告|通知|更新說明|更新说明|作者的話|作者的话|"
    r"請假|请假|延期|復刊|复刊|連載再開|连载再开|hiatus|notice", re.IGNORECASE
)
STORY_RE = re.compile(r"番外|後記|后记|特別篇|特别篇|序章|終章|终章")
NUMBER_PATTERNS = (
    re.compile(r"第\s*0*(\d{1,4})\s*[話话回章]", re.IGNORECASE),
    re.compile(r"^\s*0*(\d{1,4})(?:\s|[-—_:：.]|$)"),
)


@dataclass
class Chapter:
    folder: Path
    images: list[Path]
    site_index: int
    title: str
    actual_no: int | None = None
    notice_reason: str = ""


@dataclass
class IntegrityRow:
    site_index: int
    title: str
    expected: int
    downloaded: int
    missing: list[str]
    corrupt: list[str]


def configure_console():
    if os.name == "nt":
        os.system("chcp 65001 >nul")
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def natural_key(value):
    name = value.name if isinstance(value, Path) else str(value)
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", name)]


def safe_name(text: str) -> str:
    text = convert(text, "zh-cn")
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")
    return text[:150] or "JMComic"


def find_album_dirs(base_dir: Path, album_id: str) -> list[Path]:
    candidates = [p for p in base_dir.glob(f"JM{album_id}-*") if p.is_dir()]
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)


def fetch_metadata(album_id: str, option_path: Path):
    option = jmcomic.create_option_by_file(str(option_path))
    client = option.build_jm_client()
    album = client.get_album_detail(album_id)
    metadata = {}
    for episode in album.episode_list:
        photo_id, site_index, title = episode[:3]
        metadata[int(site_index)] = {"photo_id": str(photo_id), "title": str(title or "").strip()}
    return album, metadata, client


def page_key(value: str) -> str:
    """Ignore extension and leading-zero differences between webp/jpg names."""
    stem = Path(str(value)).stem
    return str(int(stem)) if stem.isdigit() else stem.casefold()


def image_is_readable(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def verify_download(metadata, chapters, client):
    """Compare local files with the server page list, chapter by chapter."""
    local_by_index = {chapter.site_index: chapter for chapter in chapters}
    rows, verify_errors = [], []
    for site_index in sorted(metadata):
        item = metadata[site_index]
        try:
            photo = client.get_photo_detail(item["photo_id"], fetch_album=False)
            expected_names = [str(name) for name in (getattr(photo, "page_arr", None) or [])]
        except Exception as exc:
            expected_names = []
            verify_errors.append(f"站点序号 {site_index:03d}：无法读取网站页数（{type(exc).__name__}: {exc}）")
        chapter = local_by_index.get(site_index)
        local_images = chapter.images if chapter else []
        local_map = {page_key(path.name): path for path in local_images}
        missing = [name for name in expected_names if page_key(name) not in local_map]
        corrupt = [path.name for path in local_images if not image_is_readable(path)]
        rows.append(IntegrityRow(site_index, item.get("title", ""), len(expected_names),
                                 len(local_images), missing, corrupt))
    return rows, verify_errors


def find_cover(album_dirs: list[Path]):
    for album_dir in album_dirs:
        for pattern in ("000-cover.*", "*cover*.*"):
            candidates = [p for p in album_dir.glob(pattern)
                          if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES]
            if candidates:
                return candidates[0]
    return None


def scan_chapters(album_dirs: list[Path], metadata):
    by_index = {}
    for album_dir in album_dirs:
        for folder in album_dir.iterdir():
            if not folder.is_dir() or not folder.name.isdigit():
                continue
            images = sorted((p for p in folder.rglob("*")
                             if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES), key=natural_key)
            if not images:
                continue
            site_index = int(folder.name)
            current = by_index.get(site_index)
            # 同一 JM 号的简繁目录可能重复；优先采用图片更完整的一份。
            if current is None or len(images) > len(current.images):
                by_index[site_index] = Chapter(
                    folder, images, site_index, metadata.get(site_index, {}).get("title", "")
                )
    return [by_index[index] for index in sorted(by_index)]


def valid_cbz(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None and bool(archive.namelist())
    except (OSError, zipfile.BadZipFile):
        return False


def explicit_number(title: str):
    for pattern in NUMBER_PATTERNS:
        match = pattern.search(title)
        if match:
            return int(match.group(1))
    return None


def classify_and_number(chapters):
    body, notices = [], []
    previous_no = 0
    for chapter in chapters:
        title = chapter.title.strip()
        if NOTICE_RE.search(title):
            chapter.notice_reason = "标题命中公告关键词"
            notices.append(chapter)
            continue
        number = explicit_number(title)
        if len(chapter.images) < 3 and number is None and not STORY_RE.search(title):
            chapter.notice_reason = f"仅 {len(chapter.images)} 张图片且无正文话号"
            notices.append(chapter)
            continue
        chapter.actual_no = number if number is not None else previous_no + 1
        if chapter.actual_no <= previous_no and number is None:
            chapter.actual_no = previous_no + 1
        previous_no = max(previous_no, chapter.actual_no)
        body.append(chapter)
    return body, notices


def load_font(size: int):
    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/msyh.ttc",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/simhei.ttf",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def generated_volume_cover(source: Path | None, title: str, first_no: int, last_no: int):
    width, height = 1600, 2400
    if source:
        with Image.open(source) as image:
            base = ImageOps.fit(image.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)
        base = ImageEnhance.Brightness(base.filter(ImageFilter.GaussianBlur(22))).enhance(0.42)
    else:
        base = Image.new("RGB", (width, height), (35, 39, 48))
    draw = ImageDraw.Draw(base, "RGBA")
    draw.rectangle((100, 1420, 1500, 2200), fill=(0, 0, 0, 150),
                   outline=(255, 255, 255, 80), width=3)
    title_font, range_font, small_font = load_font(92), load_font(126), load_font(54)
    lines, current = [], ""
    for char in convert(title, "zh-cn"):
        test = current + char
        if draw.textlength(test, font=title_font) > 1220 and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    y = 1510
    for line in lines[:3]:
        draw.text((800, y), line, font=title_font, fill="white", anchor="ma")
        y += 125
    draw.text((800, 1960), f"第 {first_no:03d}–{last_no:03d} 话", font=range_font,
              fill=(255, 230, 150), anchor="mm")
    draw.text((800, 2130), "JMComic · CBZ 分卷", font=small_font,
              fill=(220, 220, 220), anchor="mm")
    output = io.BytesIO()
    base.save(output, "JPEG", quality=92, optimize=True, progressive=True)
    return output.getvalue()


def processed_image_bytes(path: Path, max_width: int, quality: int):
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        if getattr(image, "is_animated", False):
            image.seek(0)
        image = image.convert("RGB")
        if max_width > 0 and image.width > max_width:
            height = max(1, round(image.height * max_width / image.width))
            image = image.resize((max_width, height), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, "JPEG", quality=quality, optimize=True, progressive=True, subsampling="4:2:0")
        return output.getvalue()


def make_cbz(output: Path, chapters, cover_bytes: bytes | None, max_width: int, quality: int):
    temp = output.with_suffix(".cbz.tmp")
    temp.unlink(missing_ok=True)
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        if cover_bytes:
            archive.writestr("000-cover.jpg", cover_bytes)
        for chapter in chapters:
            chapter_no = chapter.actual_no or chapter.site_index
            for image_no, image in enumerate(chapter.images, 1):
                archive.writestr(f"{chapter_no:03d}/{image_no:04d}.jpg",
                                 processed_image_bytes(image, max_width, quality))
    temp.replace(output)


def make_notice_cbz(output: Path, notices, max_width: int, quality: int):
    if not notices:
        return
    temp = output.with_suffix(".cbz.tmp")
    temp.unlink(missing_ok=True)
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for idx, chapter in enumerate(notices, 1):
            for image_no, image in enumerate(chapter.images, 1):
                archive.writestr(f"{idx:03d}-{chapter.site_index:03d}/{image_no:04d}.jpg",
                                 processed_image_bytes(image, max_width, quality))
    temp.replace(output)


def write_pagecount_in_place(output: Path, author: str | None = None) -> int:
    """Write page-count and author metadata without a backup copy."""
    page_count, _backup_message = update_cbz(
        output, make_backup=False, author=author
    )
    return page_count


def main():
    configure_console()
    if len(sys.argv) < 7:
        print("用法：pack_cbz.py JM号 下载根目录 每卷话数 最大宽度 JPEG质量 option.yml")
        return 2
    album_id = re.sub(r"\D", "", sys.argv[1])
    base_dir, group_size = Path(sys.argv[2]), int(sys.argv[3])
    max_width, quality, option_path = int(sys.argv[4]), int(sys.argv[5]), Path(sys.argv[6])
    album_dirs = find_album_dirs(base_dir, album_id)
    print("正在读取章节标题和实际话数……")
    download_exit_code = int(sys.argv[7]) if len(sys.argv) > 7 else 0
    album, metadata, client = fetch_metadata(album_id, option_path)
    chapters = scan_chapters(album_dirs, metadata)
    integrity, verify_errors = verify_download(metadata, chapters, client)
    expected_total = sum(row.expected for row in integrity)
    downloaded_total = sum(row.downloaded for row in integrity)
    missing_total = sum(len(row.missing) for row in integrity)
    corrupt_total = sum(len(row.corrupt) for row in integrity)
    incomplete = bool(download_exit_code or not integrity or downloaded_total != expected_total
                      or missing_total or corrupt_total or verify_errors
                      or any(row.expected == 0 for row in integrity))
    body, notices = classify_and_number(chapters)
    fallback_title = album_dirs[0].name.split("-", 1)[-1] if album_dirs else f"JM{album_id}"
    title = convert(album.name or fallback_title, "zh-cn")
    author = ", ".join(
        str(item).strip() for item in (getattr(album, "authors", None) or [])
        if str(item).strip()
    )
    if not author:
        author = str(getattr(album, "author", "") or "").strip()
    cover = find_cover(album_dirs)
    output_dir = base_dir / "CBZ"
    output_dir.mkdir(parents=True, exist_ok=True)
    report = []
    original_cover = processed_image_bytes(cover, max_width, quality) if cover else None
    for volume_index, start in enumerate(range(0, len(body), group_size), 1):
        group = body[start:start + group_size]
        first_no = group[0].actual_no or group[0].site_index
        last_no = group[-1].actual_no or group[-1].site_index
        if volume_index == 1 and original_cover:
            cover_bytes, cover_kind = original_cover, "原始作品封面"
        else:
            cover_bytes = generated_volume_cover(cover, title, first_no, last_no)
            cover_kind = "自动卷封面"
        output = output_dir / (safe_name(f"{title} {first_no:03d}-{last_no:03d}话") + ".cbz")
        if valid_cbz(output):
            print(f"已存在且完整，跳过：{output.name}")
        else:
            make_cbz(output, group, cover_bytes, max_width, quality)
        page_count = write_pagecount_in_place(output, author)
        size_mb = output.stat().st_size / 1024 / 1024
        print(f"已生成：{output.name}（{page_count} 页，{size_mb:.1f} MB，{cover_kind}；页数元数据已原地写入）")
        report.append(
            f"{output.name}\t{len(group)}话\t{page_count}页\t{size_mb:.1f} MB\t{cover_kind}\t页数元数据已写入"
        )
    notice_output = output_dir / (safe_name(f"{title} 公告附录") + ".cbz")
    if notices and not valid_cbz(notice_output):
        make_notice_cbz(notice_output, notices, max_width, quality)
    if notices:
        notice_page_count = write_pagecount_in_place(notice_output, author)
        print(f"公告附录：{notice_output.name}（{len(notices)} 项，{notice_page_count} 页；页数元数据已原地写入）")
    report_path = output_dir / (safe_name(f"JM{album_id}-{title}-分卷报告") + ".txt")
    status = "未完成" if incomplete else "完整"
    lines = [
        f"【下载状态】{status}",
        f"作品：JM{album_id} {title}",
        f"作者：{author or '(网站未提供)'}",
        f"网站应有：{expected_total} 张｜本地已有：{downloaded_total} 张｜缺失：{missing_total} 张｜损坏：{corrupt_total} 张",
        f"下载程序退出码：{download_exit_code}",
        f"下载条目：{len(chapters)}", f"正文识别：{len(body)}",
        "扫描目录：" + (" ｜ ".join(str(path) for path in album_dirs) or "未创建下载目录"),
        f"公告/疑似公告：{len(notices)}",
        f"分卷规则：每 {group_size} 个正文话一个 CBZ，文件名使用识别出的实际话数",
        f"图片模式：JPEG 质量 {quality}；最大宽度：{'原图' if max_width == 0 else str(max_width) + 'px'}",
        "第一卷使用原始封面，后续卷使用自动生成的卷封面。",
        "每个 CBZ 已自动原地写入页数和作者元数据，不生成处理后副本或备份文件。",
        "原始图片仍然保留。", "",
        "【完整性检查】",
    ]
    if incomplete:
        if download_exit_code:
            lines.append(f"下载程序本次返回错误（退出码 {download_exit_code}）。")
        for row in integrity:
            if row.downloaded != row.expected or row.missing or row.corrupt or row.expected == 0:
                lines.append(f"站点序号 {row.site_index:03d}\t{row.title or '(无标题)'}\t"
                             f"应有 {row.expected or '?'} 张／已有 {row.downloaded} 张")
                if row.missing:
                    lines.append("  缺少：" + ", ".join(row.missing))
                if row.corrupt:
                    lines.append("  损坏：" + ", ".join(row.corrupt))
        lines.extend(verify_errors)
    else:
        lines.append("完整：本地图片与网站每章页面清单一致，且图片均可正常读取。")
    lines.extend(["", "【生成文件】", *report, "", "【公告与疑似公告】"])
    if notices:
        for chapter in notices:
            lines.append(f"站点序号 {chapter.site_index:03d}\t{chapter.title or '(无标题)'}\t"
                         f"{len(chapter.images)} 张\t{chapter.notice_reason}")
    else:
        lines.append("无")
    lines.extend(["", "【正文实际话数映射】"])
    for chapter in body:
        lines.append(f"站点序号 {chapter.site_index:03d} → 第 {chapter.actual_no:03d} 话\t"
                     f"{chapter.title or '(标题未写话数，按前一正文话顺延)'}\t{len(chapter.images)} 张")
    report_path.write_text("\n".join(lines), encoding="utf-8-sig")
    print(f"分卷报告：{report_path}")
    return 3 if incomplete else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[错误] {type(exc).__name__}: {exc}")
        raise SystemExit(1)
