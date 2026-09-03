#!/usr/bin/env python3
"""Scan JMComic split-volume reports and list incomplete downloads."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REPORT_SUFFIX = "分卷报告.txt"
DEFAULT_SCAN_ROOT = Path(r"D:\JMComic\download\CBZ")


@dataclass
class ReportResult:
    path: Path
    jm_id: str
    title: str
    status: str
    expected: int | None
    existing: int | None
    missing: int | None
    damaged: int | None
    missing_files: list[str]
    incomplete: bool
    reason: str


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def first_match(pattern: str, text: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def to_int(value: str) -> int | None:
    return int(value) if value else None


def parse_report(path: Path) -> ReportResult:
    text = read_text(path)
    status = first_match(r"【下载状态】\s*([^\r\n]+)", text)
    title = first_match(r"^作品[：:]\s*(.+)$", text, re.MULTILINE)
    jm_id = first_match(r"(?i)\bJM\s*(\d+)\b", title + "\n" + path.name)

    totals = re.search(
        r"网站应有[：:]\s*(\d+)\s*张\s*[｜|]\s*"
        r"本地已有[：:]\s*(\d+)\s*张\s*[｜|]\s*"
        r"缺失[：:]\s*(\d+)\s*张\s*[｜|]\s*"
        r"损坏[：:]\s*(\d+)\s*张",
        text,
    )
    if totals:
        expected, existing, missing, damaged = map(int, totals.groups())
    else:
        expected = to_int(first_match(r"网站应有[：:]\s*(\d+)\s*张", text))
        existing = to_int(first_match(r"本地已有[：:]\s*(\d+)\s*张", text))
        missing = to_int(first_match(r"缺失[：:]\s*(\d+)\s*张", text))
        damaged = to_int(first_match(r"损坏[：:]\s*(\d+)\s*张", text))

    missing_files: list[str] = []
    for line in text.splitlines():
        match = re.match(r"\s*缺少[：:]\s*(.+)", line)
        if match:
            missing_files.extend(
                item.strip() for item in match.group(1).split(",") if item.strip()
            )

    reasons: list[str] = []
    if status and status != "完整":
        reasons.append(f"状态={status}")
    if missing is not None and missing > 0:
        reasons.append(f"缺失={missing}张")
    if damaged is not None and damaged > 0:
        reasons.append(f"损坏={damaged}张")
    if expected is not None and existing is not None and existing < expected:
        difference = expected - existing
        if missing in (None, 0):
            reasons.append(f"应有与已有相差={difference}张")

    recognized = bool(status) or any(
        value is not None for value in (expected, existing, missing, damaged)
    )
    if not recognized:
        reasons.append("报告格式无法识别，需人工检查")

    incomplete = bool(reasons)
    return ReportResult(
        path=path,
        jm_id=jm_id or "未知",
        title=title or path.stem,
        status=status or "未知",
        expected=expected,
        existing=existing,
        missing=missing,
        damaged=damaged,
        missing_files=missing_files,
        incomplete=incomplete,
        reason="；".join(reasons) if reasons else "完整",
    )


def format_count(value: int | None) -> str:
    return str(value) if value is not None else "未知"


def display_title(item: ReportResult) -> str:
    """Avoid printing the same JM number twice when it is part of the title."""
    if not item.jm_id.isdigit():
        return item.title
    return re.sub(
        rf"^\s*JM\s*{re.escape(item.jm_id)}\s*[-—_:：]*\s*",
        "",
        item.title,
        count=1,
        flags=re.IGNORECASE,
    ) or item.title


def choose_root() -> Path:
    if len(sys.argv) > 1:
        raw = " ".join(sys.argv[1:]).strip().strip('"')
        return Path(raw).expanduser()

    default = DEFAULT_SCAN_ROOT
    print("请输入要扫描的文件夹路径。")
    print(f"直接按回车：扫描默认文件夹\n默认路径：{default}")
    raw = input("文件夹路径：").strip().strip('"')
    return Path(raw).expanduser() if raw else default


def main() -> int:
    root = choose_root().resolve()
    if not root.is_dir():
        print(f"\n[错误] 文件夹不存在：{root}")
        return 2

    print(f"\n正在递归扫描：{root}")
    paths = sorted(
        (p for p in root.rglob("*.txt") if p.name.endswith(REPORT_SUFFIX)),
        key=lambda p: str(p).casefold(),
    )
    if not paths:
        print(f"[未找到] 没有发现 *{REPORT_SUFFIX}")
        return 1

    results = [parse_report(path) for path in paths]
    incomplete = [item for item in results if item.incomplete]
    complete = [item for item in results if not item.incomplete]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = root / f"未完成检测结果_{stamp}"
    output_dir.mkdir(parents=False, exist_ok=False)

    report_lines = [
        "JMComic 分卷报告完整性检测结果",
        f"扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"扫描目录：{root}",
        f"报告总数：{len(results)}",
        f"完整：{len(complete)}",
        f"未完成或异常：{len(incomplete)}",
        "",
        "【未完成或异常】",
    ]

    if not incomplete:
        report_lines.append("无，所有报告均显示完整。")
    else:
        for index, item in enumerate(incomplete, 1):
            report_lines.extend(
                [
                    f"{index}. JM{item.jm_id}  {display_title(item)}",
                    f"   原因：{item.reason}",
                    "   数量："
                    f"应有 {format_count(item.expected)} / "
                    f"已有 {format_count(item.existing)} / "
                    f"缺失 {format_count(item.missing)} / "
                    f"损坏 {format_count(item.damaged)}",
                    f"   报告：{item.path}",
                ]
            )
            if item.missing_files:
                report_lines.append("   缺少：" + ", ".join(item.missing_files))
            report_lines.append("")

    report_lines.extend(["【完整】"])
    if complete:
        for item in complete:
            report_lines.append(f"JM{item.jm_id}  {display_title(item)}")
    else:
        report_lines.append("无")

    report_path = output_dir / "未完成检测报告.txt"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8-sig")

    valid_ids = []
    seen = set()
    for item in incomplete:
        if item.jm_id.isdigit() and item.jm_id not in seen:
            valid_ids.append(item.jm_id)
            seen.add(item.jm_id)
    selected_path = output_dir / "selected_id.txt"
    selected_path.write_text(
        "".join(f"{jm_id}\n" for jm_id in valid_ids), encoding="utf-8"
    )

    # A single comma-separated line can be pasted directly into download tools
    # that accept continuous/batch JM IDs.
    continuous_ids = ",".join(valid_ids)
    continuous_path = output_dir / "JM连续下载ID_逗号分隔.txt"
    continuous_path.write_text(
        continuous_ids + ("\n" if continuous_ids else ""), encoding="utf-8-sig"
    )

    print("\n========== 检测完成 ==========")
    print(f"报告总数：{len(results)}")
    print(f"完整：{len(complete)}")
    print(f"未完成或异常：{len(incomplete)}")
    if incomplete:
        print("\n需要重新下载：")
        for item in incomplete:
            print(f"  JM{item.jm_id}  {item.reason}  {display_title(item)}")
        if continuous_ids:
            print("\n【可直接复制到 JM 连续下载】")
            print(continuous_ids)
    else:
        print("\n所有报告均显示完整。")
    print(f"\n结果文件夹：{output_dir}")
    print(f"详细报告：{report_path.name}")
    print(f"续传列表：{selected_path.name}")
    print(f"连续下载：{continuous_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
