"""One-click front end for txt_to_epub.py; no AI service required."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from posixpath import dirname, join, normpath
from xml.etree import ElementTree as ET
from zipfile import ZIP_STORED, BadZipFile, ZipFile


SITE_PROMPTS = {
    "『加入书签，方便阅读』": "加入书签，方便阅读",
    "『点击章节报错』": "点击章节报错",
}


def infer_metadata(path: Path) -> tuple[str, str | None]:
    stem = path.stem.strip()
    match = re.fullmatch(r"(.+?)\s+-\s+(.+)", stem)
    if not match:
        match = re.fullmatch(r"(.+?)\s*[（(]([^()（）]+)[）)]", stem)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return stem, None


def choose_output(folder: Path, title: str, author: str) -> Path:
    base = f"{title} - {author}（黑背雪制作）"
    for suffix in ("", *(f"_{i}" for i in range(2, 1000))):
        candidate = folder / f"{base}{suffix}.epub"
        report = candidate.with_suffix(".检查报告.txt")
        if not candidate.exists() and not report.exists():
            return candidate
    raise RuntimeError("同名输出过多，请整理输出目录。")


def prepare_text(text: str) -> tuple[str, dict[str, int]]:
    counts = {label: 0 for label in SITE_PROMPTS.values()}
    prepared = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        label = SITE_PROMPTS.get(line.strip())
        if label:
            counts[label] += 1
            continue
        # Web scrapers sometimes left literal HTML indentation entities in TXT.
        line = re.sub(r"^\s*(?:&emsp;)+", "    ", line)
        prepared.append(line)
    return "\n".join(prepared), counts


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别 TXT 编码。")


def _chapter_number(token: str) -> int:
    if token.isdigit():
        return int(token)
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    total = current = 0
    for char in token:
        if char in digits:
            current = digits[char]
        elif char in "十百千":
            unit = {"十": 10, "百": 100, "千": 1000}[char]
            total += (current or 1) * unit
            current = 0
    return total + current


def detect_number_gaps(text: str) -> list[int]:
    numbers: set[int] = set()
    numeral = r"[0-9〇零一二三四五六七八九十百千两]+"
    pattern = re.compile(rf"^第({numeral})章(?:(?:到|至)第({numeral})章|\s|$)")
    for line in text.splitlines():
        if len(line) > 100 or line != line.lstrip():
            continue
        match = pattern.match(line)
        if not match:
            continue
        start = _chapter_number(match.group(1))
        end = _chapter_number(match.group(2)) if match.group(2) else start
        if 0 < start <= end <= 9999:
            numbers.update(range(start, end + 1))
    if not numbers or max(numbers) - min(numbers) > 2000:
        return []
    return sorted(set(range(min(numbers), max(numbers) + 1)) - numbers)


def inspect_epub(path: Path) -> dict:
    errors: list[str] = []
    chapter_count = 0
    try:
        with ZipFile(path) as book:
            names = set(book.namelist())
            first = book.infolist()[0]
            if first.filename != "mimetype" or first.compress_type != ZIP_STORED:
                errors.append("mimetype 不是首项未压缩文件")
            if book.read("mimetype") != b"application/epub+zip":
                errors.append("mimetype 内容错误")
            damaged = book.testzip()
            if damaged:
                errors.append(f"ZIP 成员损坏：{damaged}")
            container = ET.fromstring(book.read("META-INF/container.xml"))
            opf_name = next(
                item.attrib["full-path"]
                for item in container.iter()
                if item.tag.endswith("}rootfile")
            )
            opf = ET.fromstring(book.read(opf_name))
            base = dirname(opf_name)
            manifest = {
                item.attrib["id"]: item.attrib
                for item in opf.iter()
                if item.tag.endswith("}item")
            }
            for item in manifest.values():
                target = normpath(join(base, item["href"].split("#")[0]))
                if target not in names:
                    errors.append(f"manifest 缺文件：{target}")
            chapter_count = sum(
                item["href"].startswith("Text/chapter-")
                for item in manifest.values()
            )
            for item in opf.iter():
                if item.tag.endswith("}itemref") and item.attrib["idref"] not in manifest:
                    errors.append(f"spine 缺项目：{item.attrib['idref']}")
            nav_item = next(
                (item for item in manifest.values() if "nav" in item.get("properties", "").split()),
                None,
            )
            ncx_item = next((item for item in manifest.values() if item["href"].endswith(".ncx")), None)
            if not nav_item or not ncx_item:
                errors.append("缺少 nav.xhtml 或 toc.ncx")
            else:
                nav_path = normpath(join(base, nav_item["href"]))
                nav = ET.fromstring(book.read(nav_path))
                for link in nav.iter():
                    if link.tag.endswith("}a") and "href" in link.attrib:
                        target = normpath(join(dirname(nav_path), link.attrib["href"].split("#")[0]))
                        if target not in names:
                            errors.append(f"目录目标不存在：{target}")
                ET.fromstring(book.read(normpath(join(base, ncx_item["href"]))))
    except (BadZipFile, KeyError, StopIteration, ET.ParseError, IndexError, OSError) as error:
        errors.append(f"EPUB 读取失败：{error}")
    return {"ok": not errors, "errors": errors, "chapters": chapter_count}


def find_cover(folder: Path, title: str) -> Path | None:
    for name in (f"{title}.jpg", f"{title}.jpeg", f"{title}.png", "cover.jpg", "cover.jpeg", "cover.png"):
        candidate = folder / name
        if candidate.is_file():
            return candidate
    return None


def request_gui_input() -> Path | None:
    from tkinter import Tk, filedialog

    root = Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title="选择小说 TXT", filetypes=[("TXT 小说", "*.txt")])
    root.destroy()
    return Path(path) if path else None


def request_author(title: str) -> str | None:
    from tkinter import Tk, simpledialog

    root = Tk()
    root.withdraw()
    value = simpledialog.askstring("作者", f"请输入《{title}》的作者：", parent=root)
    root.destroy()
    return value.strip() if value and value.strip() else None


def run(args: argparse.Namespace) -> tuple[Path, Path, dict]:
    source = Path(args.input).resolve()
    if not source.is_file() or source.suffix.lower() != ".txt":
        raise ValueError("请选择存在的 .txt 文件。")
    inferred_title, inferred_author = infer_metadata(source)
    title = (args.title or inferred_title).strip()
    author = (args.author or inferred_author or "").strip()
    if not author and not args.no_gui:
        author = request_author(title) or ""
    if not title or not author:
        raise ValueError("缺少书名或作者；可将文件命名为『书名 - 作者.txt』，或提供 --title/--author。")

    output_folder = Path(args.output_dir).resolve() if args.output_dir else source.parent / "已制作EPUB"
    output_folder.mkdir(parents=True, exist_ok=True)
    output = choose_output(output_folder, title, author)
    cover = Path(args.cover).resolve() if args.cover else find_cover(source.parent, title)
    if cover and not cover.is_file():
        raise ValueError(f"封面文件不存在：{cover}")
    builder = Path(args.builder).resolve() if args.builder else Path(__file__).with_name("txt_to_epub.py")
    if not builder.is_file():
        raise ValueError(f"找不到模板转换器：{builder}")

    prepared, removed = prepare_text(read_text(source))
    number_gaps = detect_number_gaps(prepared)
    warnings = []
    if not cover:
        warnings.append("没有 JPG/PNG 封面；模板会生成 SVG 文字封面，旧版阅读器可能不显示缩略图。")
    if number_gaps:
        sample = "、".join(str(number) for number in number_gaps[:30])
        warnings.append(f"章节编号疑似断档 {len(number_gaps)} 处：{sample}；仅凭编号不能判定缺正文。")
    with tempfile.TemporaryDirectory(prefix="txt-to-epub-", dir=output_folder) as temp:
        staging = Path(temp) / "prepared.txt"
        staging.write_text(prepared, encoding="utf-8")
        command = [sys.executable, str(builder), str(staging), "--title", title, "--author", author, "--output", str(output)]
        if cover:
            command.extend(["--cover", str(cover)])
        if args.description:
            command.extend(["--description", args.description])
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if result.returncode:
        raise RuntimeError(f"转换失败（退出码 {result.returncode}）：\n{result.stdout}\n{result.stderr}")
    check = inspect_epub(output)
    status = "通过" if check["ok"] else "警告：EPUB 结构检查未通过"
    report = output.with_suffix(".检查报告.txt")
    lines = [
        f"状态：{status}",
        f"原稿：{source}",
        f"成品：{output}",
        f"书名：{title}",
        f"作者：{author}",
        f"识别章节文件：{check['chapters']}",
        f"网页提示清理：{sum(removed.values())} 行（加入书签 {removed['加入书签，方便阅读']}；章节报错 {removed['点击章节报错']}）",
        f"章节编号疑似断档：{len(number_gaps)} 处",
        "",
        "转换器输出：",
        result.stdout.strip(),
    ]
    if warnings or check["errors"]:
        lines.extend(["", "需要注意：", *(f"- {item}" for item in warnings + check["errors"])])
    report.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return output, report, check


def main() -> int:
    parser = argparse.ArgumentParser(description="双击选择 TXT 或将 TXT 拖到启动器，自动转 EPUB 并生成检查报告。")
    parser.add_argument("input", nargs="?", help="TXT 路径；省略时弹出文件选择框")
    parser.add_argument("--title", help="书名；默认从文件名识别")
    parser.add_argument("--author", help="作者；默认从文件名识别或弹窗输入")
    parser.add_argument("--cover", help="JPG/PNG 封面；默认寻找同目录封面")
    parser.add_argument("--description", help="简介；默认使用 TXT 首章前文字")
    parser.add_argument("--output-dir", help="输出目录；默认 TXT 同目录下的『已制作EPUB』")
    parser.add_argument("--builder", help=argparse.SUPPRESS)
    parser.add_argument("--no-gui", action="store_true", help="不弹窗；适合命令行批量调用")
    args = parser.parse_args()
    if not args.input:
        if args.no_gui:
            parser.error("--no-gui 模式需要 TXT 路径")
        selected = request_gui_input()
        if not selected:
            return 0
        args.input = str(selected)
    try:
        output, report, check = run(args)
    except (ValueError, RuntimeError, OSError) as error:
        print(f"失败：{error}", file=sys.stderr)
        return 1
    print(f"EPUB：{output}\n报告：{report}")
    return 0 if check["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
