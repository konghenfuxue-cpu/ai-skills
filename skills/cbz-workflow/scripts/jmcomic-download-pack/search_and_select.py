from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import jmcomic
from zhconv import convert


def configure_console():
    if os.name == "nt":
        os.system("chcp 65001 >nul")
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def unpack_item(item):
    if isinstance(item, (tuple, list)):
        album_id = str(item[0])
        raw = item[1] if len(item) > 1 else ""
    elif isinstance(item, dict):
        album_id = str(item.get("id", ""))
        raw = item
    else:
        return "", "", "", []
    if isinstance(raw, dict):
        title = str(raw.get("name") or raw.get("title") or "(无标题)")
        author = raw.get("author") or ""
        if isinstance(author, (list, tuple)):
            author = ", ".join(map(str, author))
        tags = raw.get("tags") or []
    else:
        title = str(raw)
        author = ""
        tags = item[2] if isinstance(item, (tuple, list)) and len(item) > 2 else []
    return album_id, title, str(author), tags


def query_variants(query: str):
    variants = []
    for value in (query, convert(query, "zh-cn"), convert(query, "zh-tw")):
        value = value.strip()
        if value and value not in variants:
            variants.append(value)
    return variants


def get_results(client, query: str, page_no: int):
    merged = {}
    variants = query_variants(query)
    print("搜索变体：" + " ｜ ".join(variants))
    for variant in variants:
        page = client.search_site(search_query=variant, page=page_no)
        for item in page:
            album_id, title, author, tags = unpack_item(item)
            if album_id and album_id not in merged:
                merged[album_id] = (album_id, title, author, tags)
    return list(merged.values())


def parse_selection(text: str, count: int):
    """解析 1,3,5-8 / 空格分隔 / A 全选，并保持显示顺序。"""
    text = text.strip().lower().replace("，", ",").replace("、", ",")
    if text in {"a", "all", "全选"}:
        return list(range(1, count + 1))
    if not text:
        return None
    selected = set()
    for part in re.split(r"[\s,;；]+", text):
        if not part:
            continue
        if re.fullmatch(r"\d+", part):
            number = int(part)
            if not 1 <= number <= count:
                return None
            selected.add(number)
            continue
        match = re.fullmatch(r"(\d+)\s*[-~～—]\s*(\d+)", part)
        if not match:
            return None
        start, end = map(int, match.groups())
        if start > end:
            start, end = end, start
        if not 1 <= start <= end <= count:
            return None
        selected.update(range(start, end + 1))
    return sorted(selected) if selected else None


def main():
    configure_console()
    if len(sys.argv) != 3:
        print("参数错误。")
        return 2
    option_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    output_path.unlink(missing_ok=True)
    print("\n搜索模式（自动合并简体、繁体结果并按 JM 号去重）")
    print("可输入作品名、作者或标签，例如：社团学姐、QRQ、韩漫 姐姐")
    query = input("搜索内容：").strip()
    if not query:
        return 0
    option = jmcomic.create_option_by_file(str(option_path))
    client = option.build_jm_client()
    page_no = 1
    while True:
        print(f"\n正在搜索“{query}”第 {page_no} 页……")
        results = get_results(client, query, page_no)
        if not results:
            print("没有搜索结果。")
            if page_no > 1:
                page_no -= 1
                continue
            return 0
        print("\n序号  JM号       标题 / 作者")
        print("-" * 78)
        for index, (album_id, title, author, _tags) in enumerate(results, 1):
            title = title.replace("\n", " ").strip()
            if len(title) > 54:
                title = title[:53] + "…"
            author_text = f"  ｜作者：{author}" if author else ""
            print(f"{index:>3}   JM{album_id:<9} {title}{author_text}")
        print("\n多选：1,3,5-8；A 全选本页；N 下一页；P 上一页；S 换关键词；Q 退出")
        choice = input("请选择：").strip().lower()
        if choice == "q":
            return 0
        if choice == "n":
            page_no += 1
            continue
        if choice == "p":
            page_no = max(1, page_no - 1)
            continue
        if choice == "s":
            query = input("新的搜索内容：").strip()
            if not query:
                return 0
            page_no = 1
            continue
        selected_numbers = parse_selection(choice, len(results))
        if selected_numbers:
            selected = [results[number - 1] for number in selected_numbers]
            print(f"\n已选择 {len(selected)} 项：")
            for album_id, title, _author, _tags in selected:
                print(f"  JM{album_id}  {title}")
            if input(f"确认依次下载这 {len(selected)} 项并生成CBZ？[Y/n]：").strip().lower() in ("", "y", "yes"):
                output_path.write_text("\n".join(item[0] for item in selected) + "\n", encoding="ascii")
                return 0
            continue
        print("输入无效，请重新选择。")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[错误] {type(exc).__name__}: {exc}")
        raise SystemExit(1)
