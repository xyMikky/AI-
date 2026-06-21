#!/usr/bin/env python3
"""大乐透趋势偏差值回测 — 验证纯趋势命中率与推荐偏差带."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from dlt_data import (
    DEVIATION_PROFILE_PATH,
    apply_deviation_band,
    analyze_local_trends,
    load_deviation_profile,
    load_records,
    pick_window,
    resolve_data_path,
    run_deviation_backtest,
)


def format_report(profile: dict) -> str:
    p = profile["params"]
    s = profile["sample"]
    il = profile["issue_level"]
    ff = profile["front"]
    bf = profile["back"]

    lines = [
        "大乐透趋势偏差值回测报告",
        f"方法: {profile['method']} · 窗口 {p['window']} 期 · 回测 {s['test_count']} 期",
        f"期号范围 {s['issue_range'][0]}—{s['issue_range'][1]}",
        "",
        "[核心结论] 纯趋势落点无法覆盖大多数实际开奖，需在落点基础上加减偏差带。",
        "",
        "■ 期级命中率（至少 1 个球精确落在趋势落点列）",
        f"  前区: {il['front_any_exact_rate'] * 100:.1f}%",
        f"  后区: {il['back_any_exact_rate'] * 100:.1f}%",
        "",
        "■ 球级精确命中率（单个球 = 最近趋势落点）",
        f"  前区: {ff['exact_hit_rate'] * 100:.1f}%  ({ff['ball_count']} 球样本)",
        f"  后区: {bf['exact_hit_rate'] * 100:.1f}%  ({bf['ball_count']} 球样本)",
        "",
        "■ 前区偏差带命中率（落点 ±N 列）",
    ]
    for k, rate in ff["band_hit_rate"].items():
        mark = " <- 推荐" if int(k) == ff["recommended_band"] else ""
        lines.append(f"  ±{k}: {rate * 100:.1f}%{mark}")

    lines.extend(
        [
            "",
            "■ 前区绝对偏差分布",
            f"  均值 {ff['abs_deviation']['mean']} · 中位 {ff['abs_deviation']['median']} · "
            f"P80 {ff['abs_deviation']['p80']} · P90 {ff['abs_deviation']['p90']}",
            "",
            "■ 后区推荐偏差带",
            f"  ±{bf['recommended_band']} · 精确率 {bf['exact_hit_rate'] * 100:.1f}%",
            "",
            "[说明] 档案会随回测样本扩大而更新；预测时勿只押纯落点，应使用偏差带扩展候选。",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="趋势偏差值回测与档案更新")
    parser.add_argument("-d", "--data", type=Path, help="JSON 数据路径")
    parser.add_argument("-n", "--window", type=int, default=15, help="局部趋势窗口（默认 15）")
    parser.add_argument(
        "-t", "--test-issues", type=int, default=300, help="回测最近 N 期（默认 300）"
    )
    parser.add_argument("--no-save", action="store_true", help="不写入 deviation_profile.json")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON")
    parser.add_argument(
        "--preview-adjust",
        action="store_true",
        help="用最新档案对当前期局部趋势做偏差带扩展预览",
    )
    args = parser.parse_args()

    data_path = resolve_data_path(args.data)
    records = load_records(data_path)
    profile = run_deviation_backtest(
        records, window=args.window, test_issues=args.test_issues
    )
    profile["updated"] = date.today().isoformat()
    profile["data_path"] = str(data_path.resolve())
    fe = profile["front"].get("exact_hit_rate", 0)
    profile["notes"] = (
        f"纯趋势落点球级精确率：前区 {fe * 100:.1f}%（800期回测约11%，与用户经验~20%同量级偏低）。"
        "预测时须对落点做 recommended_band 扩展，勿只押纯落点列。"
        "样本扩大后请重新运行 deviation_backtest.py 更新本档案。"
    )

    save_path = DEVIATION_PROFILE_PATH
    if not args.no_save:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.preview_adjust:
        window, target_issue = pick_window(records, None, args.window)
        analysis = analyze_local_trends(window)
        adjusted = apply_deviation_band(analysis, profile)
        profile["preview"] = {"target_issue": target_issue, "adjusted": adjusted}

    if args.json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        print(format_report(profile))
        if not args.no_save:
            print()
            print(f"档案已写入: {save_path.resolve()}")
        if args.preview_adjust and "preview" in profile:
            adj = profile["preview"]["adjusted"]
            print()
            print(f"■ 偏差带扩展预览 · 基准期 {profile['preview']['target_issue']}")
            print(f"  前区推荐带 ±{adj['recommended_band']['front']} · 精确率参考 {adj['exact_hit_rate_ref']['front']}")
            front_nums = " ".join(f"{x['num']:02d}" for x in adj["front_adjusted"][:8])
            print(f"  前区扩展候选: {front_nums}")
            back_nums = " ".join(f"{x['num']:02d}" for x in adj["back_adjusted"][:4])
            print(f"  后区扩展候选: {back_nums}")
        print()
        print(json.dumps(profile, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
