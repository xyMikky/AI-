#!/usr/bin/env python3
"""大乐透冷热号、和值、区间分布统计报告."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dlt_data import data_summary, load_records, resolve_data_path, window_stats


def format_report(stats: dict, summary: dict, data_path: Path) -> str:
    lines = [
        f"大乐透统计分析 · 基准期 {stats['target_issue']} · 窗口 {stats['periods']} 期",
        f"期号范围 {stats['range'][0]}—{stats['range'][1]} · 全库 {summary['total']} 期 "
        f"({summary['first_issue']}—{summary['last_issue']})",
        f"数据源 {data_path.name}",
        "",
        f"■ 最新开奖 {stats['latest_draw']['issue']}: "
        f"前区 {' '.join(stats['latest_draw']['main'])} + "
        f"后区 {' '.join(stats['latest_draw']['bonus'])}",
        "",
        "■ 和值",
        f"  窗口均值 {stats['sum']['avg']} · 最小 {stats['sum']['min']} · "
        f"最大 {stats['sum']['max']} · 最近一期 {stats['sum']['last']}",
        "",
        "■ 区间 / 奇偶 / 大小（窗口累计球数）",
        f"  三区间 {stats['zone_total']['01-12']} / "
        f"{stats['zone_total']['13-24']} / {stats['zone_total']['25-35']}",
        f"  奇偶 {stats['odd_even_total']['odd']}:{stats['odd_even_total']['even']}",
        f"  大小 {stats['size_total']['small_01_17']}:{stats['size_total']['large_18_35']}",
        "",
        f"■ 前区热号 Top8（期望约 {stats['expected']['front_per_num']} 次/号）",
    ]
    for item in stats["front_hot"]:
        lines.append(f"  {item['num']:02d} · {item['count']} 次")

    lines.append("")
    lines.append("■ 前区冷号 Bottom8")
    for item in stats["front_cold"]:
        lines.append(f"  {item['num']:02d} · {item['count']} 次")

    lines.append("")
    lines.append("■ 前区超期冷号（遗漏 ≥ 12，回补候选）")
    if stats["front_overdue"]:
        for item in stats["front_overdue"]:
            lines.append(f"  {item['num']:02d} · 遗漏 {item['miss']} 期")
    else:
        lines.append("  （无显著超期号）")

    lines.append("")
    lines.append(f"■ 后区热号 Top5（期望约 {stats['expected']['back_per_num']} 次/号）")
    for item in stats["back_hot"]:
        lines.append(f"  {item['num']:02d} · {item['count']} 次")

    lines.append("")
    lines.append("■ 后区超期冷号（遗漏 ≥ 10）")
    if stats["back_overdue"]:
        for item in stats["back_overdue"]:
            lines.append(f"  {item['num']:02d} · 遗漏 {item['miss']} 期")
    else:
        lines.append("  （无显著超期号）")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="大乐透冷热号与和值统计")
    parser.add_argument("-i", "--issue", help="基准期号（默认最新一期）")
    parser.add_argument("-n", "--count", type=int, default=50, help="统计窗口期数（默认 50）")
    parser.add_argument("-d", "--data", type=Path, help="JSON 数据路径")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON")
    args = parser.parse_args()

    if args.count < 1:
        print("错误: count 必须 >= 1", file=sys.stderr)
        return 1

    data_path = resolve_data_path(args.data)
    if not data_path.is_file():
        print(f"错误: 数据文件不存在 {data_path}", file=sys.stderr)
        return 1

    records = load_records(data_path)
    summary = data_summary(records)
    stats = window_stats(records, args.issue, args.count)
    stats["data_path"] = str(data_path.resolve())
    stats["library"] = summary

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        print(format_report(stats, summary, data_path))
        print()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
