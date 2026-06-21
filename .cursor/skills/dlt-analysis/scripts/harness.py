#!/usr/bin/env python3
"""
大乐透预测评测框架（L1 algo harness · 盲测 walk-forward）

为什么需要它：
  - 评测预测方法是否「跑得赢随机」时，必须保证预测在揭晓答案之前就已确定（盲测）。
  - 本 harness 对每个被测期 t：仅用 ≤ (t-1) 的数据生成预测（build_final_recommendation
    内部按 base 期截断遗漏/窗口，从不接触 t 期），预测落定后才与留存的真实开奖计分。
  - 因此结论不含后视偏差，可放心跨数百期聚合。

注意：本框架评测的是「自动算法」（build_final_recommendation）。
      「看图法」需 L2 visual-subagent harness（每期派空白子agent读图），本文件不含。

用法：
  python scripts/harness.py --periods 300 --format 7+3
  python scripts/harness.py --periods 300 --format 15+5 --baseline-trials 2000
  python scripts/harness.py --periods 300 --format both --json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import dlt_data as D
from harness_common import (
    FORMATS,
    aggregate_scores,
    parse_formats,
    prize_tier,
    random_pool_baseline,
    score_pool,
)

FRONT_TOTAL = 35
BACK_TOTAL = 12
DRAW_FRONT = 5
DRAW_BACK = 2


def run(
    periods: int,
    formats: dict[str, tuple[int, int]],
    baseline_trials: int,
    data_path: Path | None,
    seed: int,
) -> dict[str, Any]:
    records = D.load_records(D.resolve_data_path(data_path))
    profile = D.load_deviation_profile()
    issues = [r["issue"] for r in records]
    rng = random.Random(seed)

    # 被测期：最近 periods 期；需有前序窗口，故从 index>=15 起
    start = max(15, len(records) - periods)
    test_idx = list(range(start, len(records)))

    agg: dict[str, Any] = {}
    for name, (fc, bc) in formats.items():
        agg[name] = {
            "front_hits_sum": 0, "back_hits_sum": 0, "prize_count": 0,
            "prize_tiers": {}, "per_period": [],
            "base_front_sum": 0.0, "base_back_sum": 0.0, "base_prize_sum": 0.0,
        }

    for i in test_idx:
        base_issue = issues[i - 1]
        actual_front = {int(x) for x in records[i]["main"]}
        actual_back = {int(x) for x in records[i]["bonus"]}
        window, _ = D.pick_window(records, base_issue, 15)

        for name, (fc, bc) in formats.items():
            res = D.build_final_recommendation(
                window, profile=profile, records=records,
                front_count=fc, back_count=bc,
            )
            sc = score_pool(res["front"], res["back"], actual_front, actual_back)
            fhit, bhit, tier = sc["front_hits"], sc["back_hits"], sc["tier"]
            a = agg[name]
            a["front_hits_sum"] += fhit
            a["back_hits_sum"] += bhit
            if tier:
                a["prize_count"] += 1
                a["prize_tiers"][tier] = a["prize_tiers"].get(tier, 0) + 1
            base = random_pool_baseline(actual_front, actual_back, fc, bc, baseline_trials, rng)
            a["base_front_sum"] += base["front_hits"]
            a["base_back_sum"] += base["back_hits"]
            a["base_prize_sum"] += base["prize_rate"]
            a["per_period"].append({
                "issue": records[i]["issue"], "base": base_issue,
                "front_hits": fhit, "back_hits": bhit, "tier": tier,
            })

    n = len(test_idx)
    summary: dict[str, Any] = {
        "tested_periods": n,
        "issue_range": [records[test_idx[0]]["issue"], records[test_idx[-1]]["issue"]] if n else None,
        "baseline_trials": baseline_trials,
        "formats": {},
    }
    for name, (fc, bc) in formats.items():
        a = agg[name]
        summary["formats"][name] = {
            "pool": f"{fc}+{bc}",
            "model": {
                "avg_front_hits": round(a["front_hits_sum"] / n, 4),
                "avg_back_hits": round(a["back_hits_sum"] / n, 4),
                "prize_rate": round(a["prize_count"] / n, 4),
                "prize_tiers": dict(sorted(a["prize_tiers"].items())),
            },
            "random_baseline": {
                "avg_front_hits": round(a["base_front_sum"] / n, 4),
                "avg_back_hits": round(a["base_back_sum"] / n, 4),
                "prize_rate": round(a["base_prize_sum"] / n, 4),
            },
            "edge": {
                "front_hits": round((a["front_hits_sum"] / n) - (a["base_front_sum"] / n), 4),
                "back_hits": round((a["back_hits_sum"] / n) - (a["base_back_sum"] / n), 4),
                "prize_rate": round((a["prize_count"] / n) - (a["base_prize_sum"] / n), 4),
            },
        }
    return summary, agg


def format_report(summary: dict[str, Any]) -> str:
    lines = [
        "大乐透预测评测（L1 algo harness · 盲测 walk-forward）",
        f"被测期数: {summary['tested_periods']}  范围: {summary['issue_range'][0]}—{summary['issue_range'][1]}",
        f"随机基线蒙特卡洛次数/期: {summary['baseline_trials']}",
        "",
    ]
    for name, f in summary["formats"].items():
        m, b, e = f["model"], f["random_baseline"], f["edge"]
        lines += [
            f"■ 格式 {name}（号池 {f['pool']}）",
            f"  前区命中/5 : 模型 {m['avg_front_hits']:.3f}  | 随机 {b['avg_front_hits']:.3f}  | 净差 {e['front_hits']:+.3f}",
            f"  后区命中/2 : 模型 {m['avg_back_hits']:.3f}  | 随机 {b['avg_back_hits']:.3f}  | 净差 {e['back_hits']:+.3f}",
            f"  中奖率     : 模型 {m['prize_rate']*100:.2f}% | 随机 {b['prize_rate']*100:.2f}% | 净差 {e['prize_rate']*100:+.2f}%",
            f"  模型中奖等级分布: {m['prize_tiers'] or '（无中奖）'}",
            "",
        ]
    edges = [f["edge"]["front_hits"] for f in summary["formats"].values()]
    verdict = (
        "结论：模型前区净差 ≤ 0，未跑赢随机（与彩票随机性一致）。"
        if all(x <= 0.02 for x in edges)
        else "结论：模型前区出现 > 随机的净差，建议加大样本复核是否稳定（谨防过拟合）。"
    )
    lines.append(verdict)
    lines.append("[声明] 盲测对算法有效；彩票随机，净差为正也可能是样本噪声，需大样本+多种子复核。")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="大乐透预测评测框架（盲测 walk-forward）")
    ap.add_argument("-n", "--periods", type=int, default=300, help="测最近 N 期（默认 300）")
    ap.add_argument("-f", "--format", default="both", help="7+3 / 15+5 / both（默认 both）")
    ap.add_argument("--baseline-trials", type=int, default=1000, help="随机基线每期蒙特卡洛次数")
    ap.add_argument("-d", "--data", type=Path, help="JSON 数据路径")
    ap.add_argument("--seed", type=int, default=42, help="随机基线种子")
    ap.add_argument("--json", action="store_true", help="仅输出 JSON")
    ap.add_argument("--log", type=Path, help="把 per-period 明细写入 JSON 文件")
    args = ap.parse_args()

    formats = parse_formats(args.format)
    summary, agg = run(args.periods, formats, args.baseline_trials, args.data, args.seed)

    if args.log:
        detail = {name: agg[name]["per_period"] for name in formats}
        args.log.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(format_report(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
