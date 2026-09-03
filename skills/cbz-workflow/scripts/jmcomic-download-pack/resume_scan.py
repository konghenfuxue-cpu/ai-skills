from __future__ import annotations

import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


ALBUM_RE = re.compile(r"^JM(\d+)-(.+)$", re.IGNORECASE)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def configure_console():
    if os.name == "nt":
        os.system("chcp 65001 >nul")
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def image_stats(folders: list[Path]):
    chapters, images = set(), 0
    for root in folders:
        for folder in root.iterdir():
            if not folder.is_dir() or not folder.name.isdigit():
                continue
            count = sum(1 for p in folder.rglob("*")
                        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
            if count:
                chapters.add(int(folder.name))
                images += count
    return len(chapters), images


def completed(base_dir: Path, album_id: str):
    output = base_dir / "CBZ"
    return bool(list(output.glob(f"JM{album_id}-*-分卷报告.txt")))


def choose_width():
    print("\n图片宽度：1=1440；2=1600（推荐）；3=1800；4=原图")
    choice = input("请选择 [2]：").strip() or "2"
    return {"1": 1440, "2": 1600, "3": 1800, "4": 0}.get(choice, 1600)


def main():
    configure_console()
    if len(sys.argv) != 4:
        print("参数错误。")
        return 2
    base_dir, option_path, packer = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    grouped = defaultdict(list)
    for folder in base_dir.iterdir():
        if not folder.is_dir() or folder.name.casefold() == "cbz":
            continue
        match = ALBUM_RE.match(folder.name)
        if match:
            grouped[match.group(1)].append(folder)
    rows = []
    for album_id, folders in sorted(grouped.items(), key=lambda item: int(item[0])):
        chapters, images = image_stats(folders)
        if images:
            title = max(folders, key=lambda p: p.stat().st_mtime).name.split("-", 1)[1]
            rows.append((album_id, title, folders, chapters, images, completed(base_dir, album_id)))
    if not rows:
        print("没有扫描到可处理的 JMComic 图片目录。")
        return 0
    print("\n扫描到以下已下载作品（相同 JM 号的简繁目录已合并）：\n")
    for index, (album_id, title, folders, chapters, images, done) in enumerate(rows, 1):
        state = "已有报告，可检查/续做" if done else "待生成 CBZ"
        duplicate = f"，合并 {len(folders)} 个目录" if len(folders) > 1 else ""
        print(f"{index:>2}. JM{album_id}｜{title}｜{chapters}章／{images}图｜{state}{duplicate}")
    print("\n输入序号处理单本；A 处理全部待生成作品；R 重新检查全部；Q 退出")
    choice = input("请选择：").strip().lower()
    if choice == "q" or not choice:
        return 0
    if choice == "a":
        selected = [row for row in rows if not row[5]]
    elif choice == "r":
        selected = rows
    elif choice.isdigit() and 1 <= int(choice) <= len(rows):
        selected = [rows[int(choice) - 1]]
    else:
        print("输入无效。")
        return 1
    if not selected:
        print("没有待生成作品；如需重新检查，请选择 R。")
        return 0
    width = choose_width()
    failures = []
    for number, (album_id, title, _folders, _chapters, _images, _done) in enumerate(selected, 1):
        print(f"\n[{number}/{len(selected)}] 续做 JM{album_id} {title}")
        result = subprocess.run([
            sys.executable, str(packer), album_id, str(base_dir), "25", str(width), "85", str(option_path), "0"
        ])
        if result.returncode != 0:
            failures.append(album_id)
    if failures:
        print("\n以下作品处理失败：" + ", ".join("JM" + item for item in failures))
        return 1
    print("\n扫描续做完成。CBZ 位于：" + str(base_dir / "CBZ"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
