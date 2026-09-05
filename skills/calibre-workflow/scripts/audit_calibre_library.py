#!/usr/bin/env python3
"""以 SQLite 只读方式审计 Calibre 书库，不修改数据库或书籍文件。"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import quote


REQUIRED_BOOK_COLUMNS = {"id", "title", "path"}
REQUIRED_DATA_COLUMNS = {"book", "format", "name"}


def normalized_title(value: str) -> str:
    value = re.sub(r"[\W_]+", " ", value, flags=re.UNICODE).casefold()
    return re.sub(r"\s+", " ", value).strip()


def safe_relative(value: str) -> bool:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    return bool(normalized) and not path.is_absolute() and ".." not in path.parts


def open_readonly(database: Path) -> sqlite3.Connection:
    uri = "file:" + quote(str(database.resolve()).replace("\\", "/")) + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def audit_library(library: Path) -> dict:
    library = library.resolve()
    database = library / "metadata.db"
    if not library.is_dir():
        raise ValueError(f"书库目录不存在：{library}")
    if not database.is_file():
        raise ValueError(f"未找到 metadata.db：{database}")

    with open_readonly(database) as connection:
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing_tables = {"books", "data"} - tables
        if missing_tables:
            raise ValueError(f"不是受支持的 Calibre 基础架构，缺少表：{', '.join(sorted(missing_tables))}")
        missing_book_columns = REQUIRED_BOOK_COLUMNS - table_columns(connection, "books")
        missing_data_columns = REQUIRED_DATA_COLUMNS - table_columns(connection, "data")
        if missing_book_columns or missing_data_columns:
            details = []
            if missing_book_columns:
                details.append("books." + ", books.".join(sorted(missing_book_columns)))
            if missing_data_columns:
                details.append("data." + ", data.".join(sorted(missing_data_columns)))
            raise ValueError("Calibre 表结构不受支持，缺少字段：" + "; ".join(details))

        quick_check = [row[0] for row in connection.execute("PRAGMA quick_check")]
        books = [dict(row) for row in connection.execute("SELECT id, title, path FROM books ORDER BY id")]
        formats = [
            dict(row)
            for row in connection.execute(
                "SELECT b.id AS book_id, b.title, b.path, d.format, d.name "
                "FROM books b JOIN data d ON d.book = b.id ORDER BY b.id, d.format"
            )
        ]
    connection.close()
    missing_files = []
    unsafe_paths = []
    for item in formats:
        book_path = str(item["path"] or "")
        data_name = str(item["name"] or "")
        extension = str(item["format"] or "").lower()
        if not safe_relative(book_path) or not safe_relative(data_name):
            unsafe_paths.append(
                {
                    "book_id": item["book_id"],
                    "title": item["title"],
                    "path": book_path,
                    "name": data_name,
                }
            )
            continue
        expected = library / Path(book_path) / f"{data_name}.{extension}"
        if not expected.is_file():
            missing_files.append(
                {
                    "book_id": item["book_id"],
                    "title": item["title"],
                    "format": item["format"],
                    "expected_path": str(expected),
                }
            )

    by_title: dict[str, list[dict]] = defaultdict(list)
    for item in books:
        key = normalized_title(str(item["title"] or ""))
        if key:
            by_title[key].append({"book_id": item["id"], "title": item["title"]})
    duplicate_candidates = [
        {"normalized_title": title, "books": entries}
        for title, entries in sorted(by_title.items())
        if len(entries) > 1
    ]

    return {
        "library": str(library),
        "database": str(database),
        "read_only": True,
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "database_quick_check": quick_check,
        "book_count": len(books),
        "format_count": len(formats),
        "missing_format_files": missing_files,
        "unsafe_paths": unsafe_paths,
        "duplicate_title_candidates": duplicate_candidates,
    }


def print_summary(report: dict) -> None:
    print(f"书库：{report['library']}")
    print(f"只读模式：是；书籍：{report['book_count']}；格式：{report['format_count']}")
    print("数据库检查：" + ", ".join(report["database_quick_check"]))
    print(f"缺失格式文件：{len(report['missing_format_files'])}")
    print(f"不安全路径：{len(report['unsafe_paths'])}")
    print(f"重复标题候选：{len(report['duplicate_title_candidates'])}")
    for item in report["missing_format_files"][:20]:
        print(f"  [缺失] #{item['book_id']} {item['title']} ({item['format']}): {item['expected_path']}")
    for item in report["duplicate_title_candidates"][:20]:
        ids = ", ".join(str(book["book_id"]) for book in item["books"])
        print(f"  [候选重复] {item['normalized_title']}: #{ids}")


def main() -> int:
    parser = argparse.ArgumentParser(description="只读审计 Calibre 书库")
    parser.add_argument("library", help="包含 metadata.db 的 Calibre 书库目录")
    parser.add_argument("--report", help="可选 JSON 报告输出路径")
    args = parser.parse_args()
    try:
        report = audit_library(Path(args.library.strip('"')))
        print_summary(report)
        if args.report:
            output = Path(args.report.strip('"')).resolve()
            if output.exists():
                raise ValueError(f"报告文件已存在，为避免覆盖已停止：{output}")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"JSON 报告：{output}")
        has_issues = any(
            report[key]
            for key in ("missing_format_files", "unsafe_paths", "duplicate_title_candidates")
        ) or report["database_quick_check"] != ["ok"]
        return 2 if has_issues else 0
    except Exception as exc:
        print(f"[失败] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
