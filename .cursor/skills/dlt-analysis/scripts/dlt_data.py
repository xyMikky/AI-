#!/usr/bin/env python3
"""大乐透历史数据加载与统计工具（供 trend_chart / stats_report 共用）."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FRONT_RANGE = range(1, 36)
BACK_RANGE = range(1, 13)
FRONT_GROUPS = (range(1, 13), range(13, 25), range(25, 36))

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = SKILL_ROOT / "assets" / "lotto_history.json"
FALLBACK_DATA = Path.home() / "Desktop" / "lotto-20260101.json"


def resolve_data_path(path: Path | None = None) -> Path:
    """优先 skill 内 assets，其次用户桌面备份."""
    if path is not None:
        return path.expanduser()
    if DEFAULT_DATA.is_file():
        return DEFAULT_DATA
    return FALLBACK_DATA


def _parse_nums(raw: list[str], lo: int, hi: int, field: str, issue: str) -> set[int]:
    nums = {int(x) for x in raw}
    if len(nums) != len(raw):
        raise ValueError(f"期号 {issue} {field} 含重复号码: {raw}")
    for n in nums:
        if n < lo or n > hi:
            raise ValueError(f"期号 {issue} {field} 号码 {n:02d} 超出范围 {lo:02d}–{hi:02d}")
    return nums


def validate_record(rec: dict[str, Any]) -> None:
    issue = str(rec.get("issue", ""))
    if not issue:
        raise ValueError(f"记录缺少 issue: {rec}")
    main = rec.get("main")
    bonus = rec.get("bonus")
    if not isinstance(main, list) or len(main) != 5:
        raise ValueError(f"期号 {issue} main 须为 5 个号码")
    if not isinstance(bonus, list) or len(bonus) != 2:
        raise ValueError(f"期号 {issue} bonus 须为 2 个号码")
    _parse_nums(main, 1, 35, "main", issue)
    _parse_nums(bonus, 1, 12, "bonus", issue)


def load_records(data_path: Path | None = None) -> list[dict[str, Any]]:
    path = resolve_data_path(data_path)
    if not path.is_file():
        raise FileNotFoundError(f"数据文件不存在: {path}")
    with path.open(encoding="utf-8") as f:
        records = json.load(f)
    if not records:
        raise ValueError(f"数据文件为空: {path}")
    for rec in records:
        validate_record(rec)
    return sorted(records, key=lambda r: r["issue"])


def pick_window(
    records: list[dict[str, Any]], issue: str | None, count: int
) -> tuple[list[dict[str, Any]], str]:
    issues = [r["issue"] for r in records]
    if issue is None:
        target_issue = issues[-1]
        end_idx = len(records) - 1
    else:
        if issue not in issues:
            raise ValueError(f"期号 {issue} 不存在，最新期为 {issues[-1]}")
        end_idx = issues.index(issue)
        target_issue = issue
    start_idx = max(0, end_idx - count + 1)
    return records[start_idx : end_idx + 1], target_issue


def data_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(records),
        "first_issue": records[0]["issue"],
        "last_issue": records[-1]["issue"],
    }


@dataclass
class MissState:
    front: dict[int, int]
    back: dict[int, int]


def init_miss() -> MissState:
    return MissState(
        front={n: 0 for n in FRONT_RANGE},
        back={n: 0 for n in BACK_RANGE},
    )


def update_miss(state: MissState, main: set[int], bonus: set[int]) -> None:
    for n in FRONT_RANGE:
        state.front[n] = 0 if n in main else state.front[n] + 1
    for n in BACK_RANGE:
        state.back[n] = 0 if n in bonus else state.back[n] + 1


def compute_miss_at(records: list[dict[str, Any]], target_issue: str) -> MissState:
    """计算指定期号开奖前的遗漏值."""
    state = init_miss()
    for rec in records:
        if rec["issue"] >= target_issue:
            break
        main = {int(x) for x in rec["main"]}
        bonus = {int(x) for x in rec["bonus"]}
        update_miss(state, main, bonus)
    return state


def build_chart_rows(
    records: list[dict[str, Any]], window: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """从全量历史计算遗漏，仅输出 window 内行."""
    window_start = window[0]["issue"]
    history = [r for r in records if r["issue"] < window_start]
    state = init_miss()
    for rec in history:
        main = {int(x) for x in rec["main"]}
        bonus = {int(x) for x in rec["bonus"]}
        update_miss(state, main, bonus)

    rows: list[dict[str, Any]] = []
    for rec in window:
        main = {int(x) for x in rec["main"]}
        bonus = {int(x) for x in rec["bonus"]}
        sum_tail = sum(main) % 10
        front_cells: dict[int, tuple[str, int]] = {}
        back_cells: dict[int, tuple[str, int]] = {}

        for n in FRONT_RANGE:
            if n in main:
                front_cells[n] = ("hit", n)
                state.front[n] = 0
            else:
                state.front[n] += 1
                front_cells[n] = ("miss", state.front[n])

        for n in BACK_RANGE:
            if n in bonus:
                back_cells[n] = ("hit", n)
                state.back[n] = 0
            else:
                state.back[n] += 1
                back_cells[n] = ("miss", state.back[n])

        rows.append(
            {
                "issue": rec["issue"],
                "sum_tail": sum_tail,
                "front": front_cells,
                "back": back_cells,
            }
        )
    return rows


def window_stats(
    records: list[dict[str, Any]], issue: str | None = None, count: int = 50
) -> dict[str, Any]:
    """窗口内冷热号、和值、区间分布等统计."""
    window, target_issue = pick_window(records, issue, count)
    miss = compute_miss_at(records, target_issue)

    front_freq: dict[int, int] = {n: 0 for n in FRONT_RANGE}
    back_freq: dict[int, int] = {n: 0 for n in BACK_RANGE}
    sums: list[int] = []
    zone_counts = [0, 0, 0]
    odd_even = [0, 0]
    size_ratio = [0, 0]

    for rec in window:
        main = sorted(int(x) for x in rec["main"])
        bonus = [int(x) for x in rec["bonus"]]
        s = sum(main)
        sums.append(s)
        for n in main:
            front_freq[n] += 1
            if n <= 17:
                size_ratio[0] += 1
            else:
                size_ratio[1] += 1
            if n % 2:
                odd_even[0] += 1
            else:
                odd_even[1] += 1
            if n <= 12:
                zone_counts[0] += 1
            elif n <= 24:
                zone_counts[1] += 1
            else:
                zone_counts[2] += 1
        for n in bonus:
            back_freq[n] += 1

    n_periods = len(window)
    front_expected = n_periods * 5 / 35
    back_expected = n_periods * 2 / 12

    def rank_freq(freq: dict[int, int], num_range: range) -> list[dict[str, Any]]:
        items = [{"num": n, "count": freq[n]} for n in num_range]
        items.sort(key=lambda x: (-x["count"], x["num"]))
        return items

    def rank_miss(miss_map: dict[int, int], num_range: range) -> list[dict[str, Any]]:
        items = [{"num": n, "miss": miss_map[n]} for n in num_range]
        items.sort(key=lambda x: (-x["miss"], x["num"]))
        return items

    front_by_freq = rank_freq(front_freq, FRONT_RANGE)
    back_by_freq = rank_freq(back_freq, BACK_RANGE)
    front_by_miss = rank_miss(miss.front, FRONT_RANGE)
    back_by_miss = rank_miss(miss.back, BACK_RANGE)

    return {
        "target_issue": target_issue,
        "periods": n_periods,
        "range": [window[0]["issue"], window[-1]["issue"]],
        "expected": {
            "front_per_num": round(front_expected, 2),
            "back_per_num": round(back_expected, 2),
            "front_miss_avg": round(35 / 5 - 1, 2),
            "back_miss_avg": round(12 / 2 - 1, 2),
        },
        "sum": {
            "min": min(sums),
            "max": max(sums),
            "avg": round(sum(sums) / len(sums), 1),
            "last": sums[-1],
        },
        "zone_total": {
            "01-12": zone_counts[0],
            "13-24": zone_counts[1],
            "25-35": zone_counts[2],
        },
        "odd_even_total": {"odd": odd_even[0], "even": odd_even[1]},
        "size_total": {"small_01_17": size_ratio[0], "large_18_35": size_ratio[1]},
        "front_hot": front_by_freq[:8],
        "front_cold": front_by_freq[-8:][::-1],
        "front_overdue": [x for x in front_by_miss if x["miss"] >= 12][:8],
        "back_hot": back_by_freq[:5],
        "back_cold": back_by_freq[-5:][::-1],
        "back_overdue": [x for x in back_by_miss if x["miss"] >= 10][:5],
        "latest_draw": {
            "issue": window[-1]["issue"],
            "main": window[-1]["main"],
            "bonus": window[-1]["bonus"],
        },
    }


def _hits_by_row(window: list[dict[str, Any]], zone: str) -> list[list[int]]:
    key = "main" if zone == "front" else "bonus"
    return [sorted(int(x) for x in rec[key]) for rec in window]


def _classify_steps(steps: list[int]) -> str:
    if not steps:
        return "flat"
    avg = sum(steps) / len(steps)
    if all(s == 0 for s in steps):
        return "vertical"
    if avg >= 0.5:
        return "diagonal_down_right"
    if avg <= -0.5:
        return "diagonal_down_left"
    return "flat"


def _chain_key(points: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    return tuple(points)


def _find_trend_chains(
    hits_by_row: list[list[int]],
    *,
    min_len: int = 3,
    max_step: int = 6,
    step_tolerance: int = 3,
) -> list[dict[str, Any]]:
    """在相邻行间寻找步长一致的连线链（至少 min_len 个点）."""
    n_rows = len(hits_by_row)
    raw_chains: list[dict[str, Any]] = []

    def dfs(path: list[tuple[int, int]], steps: list[int]) -> None:
        row, num = path[-1]
        if len(path) >= min_len:
            raw_chains.append(
                {
                    "points": path[:],
                    "steps": steps[:],
                    "type": _classify_steps(steps),
                    "length": len(path),
                    "end_row": row,
                }
            )
        if row >= n_rows - 1:
            return
        for n2 in hits_by_row[row + 1]:
            delta = n2 - num
            if abs(delta) > max_step:
                continue
            new_steps = steps + [delta]
            if len(new_steps) >= 2:
                anchor = new_steps[0]
                if not all(abs(s - anchor) <= step_tolerance for s in new_steps):
                    continue
            dfs(path + [(row + 1, n2)], new_steps)

    for start_row in range(max(0, n_rows - min_len + 1)):
        for num in hits_by_row[start_row]:
            dfs([(start_row, num)], [])

    # 去重：保留更长、更靠近最新期的链
    raw_chains.sort(key=lambda c: (-c["length"], -c["end_row"]))
    kept: list[dict[str, Any]] = []
    seen_paths: set[tuple[tuple[int, int], ...]] = set()
    for chain in raw_chains:
        pts = chain["points"]
        # 若已被更长链完全包含则跳过
        if any(
            len(other["points"]) > len(pts)
            and _is_subpath(pts, other["points"])
            for other in kept
        ):
            continue
        key = _chain_key(pts)
        if key in seen_paths:
            continue
        seen_paths.add(key)
        kept.append(chain)
    return kept[:12]


def _is_subpath(short: list[tuple[int, int]], long: list[tuple[int, int]]) -> bool:
    if len(short) >= len(long):
        return False
    for i in range(len(long) - len(short) + 1):
        if long[i : i + len(short)] == short:
            return True
    return False


def _extrapolate(num: int, avg_step: float, lo: int, hi: int) -> int:
    pred = round(num + avg_step)
    return max(lo, min(hi, pred))


def _find_vertical_repeats(
    window: list[dict[str, Any]], hits_by_row: list[list[int]], min_repeat: int = 3
) -> list[dict[str, Any]]:
    """同一号码在多期反复出现（纵向热柱）."""
    n_rows = len(hits_by_row)
    repeats: list[dict[str, Any]] = []
    all_nums = {n for row in hits_by_row for n in row}
    for num in all_nums:
        rows_hit = [i for i, row in enumerate(hits_by_row) if num in row]
        if len(rows_hit) < min_repeat:
            continue
        # 找最长连续或近连续段
        best_run: list[int] = []
        run: list[int] = [rows_hit[0]]
        for r in rows_hit[1:]:
            if r - run[-1] <= 2:
                run.append(r)
            else:
                if len(run) > len(best_run):
                    best_run = run
                run = [r]
        if len(run) > len(best_run):
            best_run = run
        if len(best_run) >= min_repeat:
            repeats.append(
                {
                    "num": num,
                    "rows": best_run,
                    "count": len(best_run),
                    "issues": [window[r]["issue"] for r in best_run],
                }
            )
    repeats.sort(key=lambda x: (-x["count"], -x["rows"][-1]))
    return repeats


def analyze_local_trends(
    window: list[dict[str, Any]],
    *,
    min_chain_len: int = 3,
    max_step: int = 6,
) -> dict[str, Any]:
    """15 期局部趋势：斜向链、纵向重复、延长落点、汇聚枢纽."""
    front_hits = _hits_by_row(window, "front")
    back_hits = _hits_by_row(window, "back")
    n_rows = len(window)

    front_chains = _find_trend_chains(
        front_hits, min_len=min_chain_len, max_step=max_step
    )
    back_chains = _find_trend_chains(
        back_hits, min_len=min_chain_len, max_step=max_step
    )

    def enrich_chains(
        chains: list[dict[str, Any]], lo: int, hi: int, zone: str
    ) -> list[dict[str, Any]]:
        enriched = []
        for chain in chains:
            pts = chain["points"]
            steps = chain["steps"]
            avg_step = sum(steps) / len(steps) if steps else 0.0
            last_row, last_num = pts[-1]
            pred_num = _extrapolate(last_num, avg_step, lo, hi)
            start_issue = window[pts[0][0]]["issue"]
            end_issue = window[pts[-1][0]]["issue"]
            path_nums = [p[1] for p in pts]
            enriched.append(
                {
                    **chain,
                    "zone": zone,
                    "path_nums": path_nums,
                    "path_issues": [window[r]["issue"] for r, _ in pts],
                    "start_issue": start_issue,
                    "end_issue": end_issue,
                    "avg_step": round(avg_step, 2),
                    "predict_num": pred_num,
                    "predict_row": n_rows,
                }
            )
        return enriched

    front_enriched = enrich_chains(front_chains, 1, 35, "front")
    back_enriched = enrich_chains(back_chains, 1, 12, "back")

    def hub_scores(chains: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scores: dict[int, int] = {}
        for c in chains:
            scores[c["predict_num"]] = scores.get(c["predict_num"], 0) + 1
        return [
            {"num": n, "convergence": cnt}
            for n, cnt in sorted(scores.items(), key=lambda x: (-x[1], x[0]))
            if cnt >= 2
        ]

    front_hubs = hub_scores(front_enriched)
    back_hubs = hub_scores(back_enriched)

    front_vertical = _find_vertical_repeats(window, front_hits, min_repeat=3)
    back_vertical = _find_vertical_repeats(window, back_hits, min_repeat=2)

    # 汇总下一期候选（链落点 + 汇聚加权）
    front_candidates: dict[int, float] = {}
    for c in front_enriched:
        front_candidates[c["predict_num"]] = (
            front_candidates.get(c["predict_num"], 0) + c["length"]
        )
    for h in front_hubs:
        front_candidates[h["num"]] = front_candidates.get(h["num"], 0) + h["convergence"] * 2

    back_candidates: dict[int, float] = {}
    for c in back_enriched:
        back_candidates[c["predict_num"]] = (
            back_candidates.get(c["predict_num"], 0) + c["length"]
        )
    for h in back_hubs:
        back_candidates[h["num"]] = back_candidates.get(h["num"], 0) + h["convergence"] * 2

    def top_candidates(scores: dict[int, float], k: int = 8) -> list[dict[str, Any]]:
        return [
            {"num": n, "score": round(s, 1)}
            for n, s in sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:k]
        ]

    return {
        "periods": n_rows,
        "range": [window[0]["issue"], window[-1]["issue"]],
        "front": {
            "chains": front_enriched,
            "vertical_repeats": front_vertical,
            "convergence_hubs": front_hubs,
            "next_candidates": top_candidates(front_candidates),
        },
        "back": {
            "chains": back_enriched,
            "vertical_repeats": back_vertical,
            "convergence_hubs": back_hubs,
            "next_candidates": top_candidates(back_candidates, k=5),
        },
    }


DEVIATION_PROFILE_PATH = SKILL_ROOT / "assets" / "deviation_profile.json"


def collect_trend_targets(analysis: dict[str, Any], zone: str) -> list[int]:
    """收集局部趋势给出的全部落点目标（链延长 + 候选）."""
    targets: set[int] = set()
    for chain in analysis[zone]["chains"]:
        targets.add(chain["predict_num"])
    for item in analysis[zone]["next_candidates"]:
        targets.add(item["num"])
    return sorted(targets)


def measure_number_deviations(
    actual_nums: list[int],
    targets: list[int],
) -> list[dict[str, Any]]:
    """对每个实际开奖号，找最近趋势落点并计算偏差（有符号列距）."""
    results: list[dict[str, Any]] = []
    for actual in actual_nums:
        if not targets:
            results.append(
                {
                    "actual": actual,
                    "nearest": None,
                    "deviation": None,
                    "abs_deviation": None,
                    "exact": False,
                }
            )
            continue
        nearest = min(targets, key=lambda t: abs(t - actual))
        deviation = actual - nearest
        results.append(
            {
                "actual": actual,
                "nearest": nearest,
                "deviation": deviation,
                "abs_deviation": abs(deviation),
                "exact": deviation == 0,
            }
        )
    return results


def run_deviation_backtest(
    records: list[dict[str, Any]],
    *,
    window: int = 15,
    test_issues: int = 300,
    min_chain_len: int = 3,
) -> dict[str, Any]:
    """
    滚动回测：用前 window 期做局部趋势，对比下一期实际开奖与趋势落点的偏差。
    用于验证「纯趋势约 20% 精确命中、多数结果存在列距偏差」假设。
    """
    if len(records) < window + 1:
        raise ValueError(f"数据不足，至少需要 {window + 1} 期")

    start_idx = max(window, len(records) - test_issues)
    front_deviations: list[int] = []
    back_deviations: list[int] = []
    front_exact = front_total = 0
    back_exact = back_total = 0
    issue_exact_front = issue_exact_back = 0
    issue_count = 0
    tested_range = [records[start_idx]["issue"], records[-1]["issue"]]

    for i in range(start_idx, len(records)):
        hist_window = records[i - window : i]
        actual = records[i]
        analysis = analyze_local_trends(hist_window, min_chain_len=min_chain_len)

        front_targets = collect_trend_targets(analysis, "front")
        back_targets = collect_trend_targets(analysis, "back")
        actual_front = [int(x) for x in actual["main"]]
        actual_back = [int(x) for x in actual["bonus"]]

        front_m = measure_number_deviations(actual_front, front_targets)
        back_m = measure_number_deviations(actual_back, back_targets)

        if front_targets:
            issue_count += 1
            if any(m["exact"] for m in front_m):
                issue_exact_front += 1
        if back_targets and any(m["exact"] for m in back_m):
            issue_exact_back += 1

        for m in front_m:
            if m["deviation"] is None:
                continue
            front_total += 1
            front_deviations.append(m["deviation"])
            if m["exact"]:
                front_exact += 1

        for m in back_m:
            if m["deviation"] is None:
                continue
            back_total += 1
            back_deviations.append(m["deviation"])
            if m["exact"]:
                back_exact += 1

    def _zone_stats(deviations: list[int], exact: int, total: int) -> dict[str, Any]:
        if total == 0:
            return {"ball_count": 0}
        abs_devs = sorted(abs(d) for d in deviations)
        band_rates: dict[str, float] = {}
        max_band = 12 if total > 2000 else 8
        for k in range(0, max_band + 1):
            hit = sum(1 for d in deviations if abs(d) <= k)
            band_rates[str(k)] = round(hit / total, 4)
        hist: dict[str, int] = {}
        for d in deviations:
            key = str(d)
            hist[key] = hist.get(key, 0) + 1
        abs_mean = round(sum(abs_devs) / len(abs_devs), 2)
        median = abs_devs[len(abs_devs) // 2]
        p80 = abs_devs[int(len(abs_devs) * 0.8)]
        p90 = abs_devs[int(len(abs_devs) * 0.9)]
        recommended = 0
        target_rate = 0.65
        for k in range(0, max_band + 1):
            if band_rates[str(k)] >= target_rate:
                recommended = k
                break
        else:
            recommended = max(1, round(p80 / 2))
        band_80_reached = any(band_rates[str(k)] >= 0.80 for k in range(max_band + 1))
        return {
            "ball_count": total,
            "exact_hit_rate": round(exact / total, 4),
            "band_hit_rate": band_rates,
            "abs_deviation": {
                "mean": abs_mean,
                "median": median,
                "p80": p80,
                "p90": p90,
            },
            "signed_histogram": dict(sorted(hist.items(), key=lambda x: int(x[0]))),
            "recommended_band": recommended,
            "band_80_reached": band_80_reached,
        }

    return {
        "version": 1,
        "method": "local_trend_extrapolation",
        "params": {
            "window": window,
            "test_issues": test_issues,
            "min_chain_len": min_chain_len,
        },
        "sample": {
            "test_count": issue_count,
            "issue_range": tested_range,
        },
        "issue_level": {
            "front_any_exact_rate": round(issue_exact_front / issue_count, 4) if issue_count else 0,
            "back_any_exact_rate": round(issue_exact_back / issue_count, 4) if issue_count else 0,
        },
        "front": _zone_stats(front_deviations, front_exact, front_total),
        "back": _zone_stats(back_deviations, back_exact, back_total),
    }


def load_deviation_profile(path: Path | None = None) -> dict[str, Any] | None:
    profile_path = path or DEVIATION_PROFILE_PATH
    if not profile_path.is_file():
        return None
    with profile_path.open(encoding="utf-8") as f:
        return json.load(f)


def apply_deviation_band(
    analysis: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """
    根据偏差档案，将趋势落点扩展为「落点 ± 推荐偏差带」候选池。
    核心落点保留原 score，偏差带内号码按距离衰减计分。
    """

    def expand_zone(zone: str, lo: int, hi: int) -> list[dict[str, Any]]:
        band = profile.get(zone, {}).get("recommended_band", 2)
        raw_scores: dict[int, float] = {}
        for item in analysis[zone]["next_candidates"]:
            center = item["num"]
            base = item["score"]
            for offset in range(-band, band + 1):
                num = center + offset
                if num < lo or num > hi:
                    continue
                decay = max(0.25, 1.0 - abs(offset) * 0.2)
                raw_scores[num] = max(raw_scores.get(num, 0), base * decay)
        return [
            {"num": n, "score": round(s, 2), "band": band}
            for n, s in sorted(raw_scores.items(), key=lambda x: (-x[1], x[0]))
        ]

    return {
        "profile_version": profile.get("version"),
        "recommended_band": {
            "front": profile.get("front", {}).get("recommended_band", 2),
            "back": profile.get("back", {}).get("recommended_band", 1),
        },
        "exact_hit_rate_ref": {
            "front": profile.get("front", {}).get("exact_hit_rate"),
            "back": profile.get("back", {}).get("exact_hit_rate"),
        },
        "front_adjusted": expand_zone("front", 1, 35)[:12],
        "back_adjusted": expand_zone("back", 1, 12)[:6],
    }


# ============================================================
# 程序六：空区（Empty Zone）分析
# 空区 = 单期内一段连续号码完全未开出（参考图中的绿色横条）。
# 核心假设：空区在三分区上具有周期性，能预测下期空区即可排除约 1/3 号码。
# ============================================================

EMPTY_ZONE_DEFS = ((1, 12), (13, 24), (25, 35))
EMPTY_ZONE_NAMES = ("01-12", "13-24", "25-35")


def find_empty_runs(
    hits: set[int], lo: int = 1, hi: int = 35, min_run: int = 6
) -> list[dict[str, int]]:
    """单期内的最大连续空号段（长度 ≥ min_run），对应绿色横条."""
    runs: list[dict[str, int]] = []
    start: int | None = None
    for n in range(lo, hi + 2):
        is_hit = n in hits or n > hi
        if is_hit:
            if start is not None:
                end = n - 1
                width = end - start + 1
                if width >= min_run:
                    runs.append({"start": start, "end": end, "width": width})
            start = None
        else:
            if start is None:
                start = n
    return runs


def _zone_of(num: int) -> int:
    for idx, (lo, hi) in enumerate(EMPTY_ZONE_DEFS):
        if lo <= num <= hi:
            return idx
    return -1


def _zone_emptiness_series(window: list[dict[str, Any]]) -> list[list[int]]:
    """每期三分区是否为空（1=空区，0=有球），返回 [zone][row]."""
    series = [[0] * len(window) for _ in EMPTY_ZONE_DEFS]
    for ri, rec in enumerate(window):
        present = {_zone_of(int(x)) for x in rec["main"]}
        for zi in range(len(EMPTY_ZONE_DEFS)):
            series[zi][ri] = 0 if zi in present else 1
    return series


def _gaps_between(flags: list[int]) -> list[int]:
    """两次空区之间的间隔期数."""
    idx = [i for i, v in enumerate(flags) if v == 1]
    return [idx[i] - idx[i - 1] for i in range(1, len(idx))]


def analyze_empty_zones(
    window: list[dict[str, Any]], min_run: int = 6
) -> dict[str, Any]:
    """三分区空区周期分析 + 下期空区预测."""
    n_rows = len(window)
    series = _zone_emptiness_series(window)

    # 每期最大空号段（用于绿色横条标注）
    per_period_runs: list[dict[str, Any]] = []
    for rec in window:
        hits = {int(x) for x in rec["main"]}
        runs = find_empty_runs(hits, 1, 35, min_run)
        widest = max(runs, key=lambda r: r["width"], default=None)
        per_period_runs.append(
            {
                "issue": rec["issue"],
                "runs": runs,
                "widest": widest,
            }
        )

    zones: list[dict[str, Any]] = []
    for zi, name in enumerate(EMPTY_ZONE_NAMES):
        flags = series[zi]
        empty_count = sum(flags)
        gaps = _gaps_between(flags)
        mean_gap = round(sum(gaps) / len(gaps), 2) if gaps else None
        # 距上次空区的期数（从最新行往回数）
        since_last = 0
        for v in reversed(flags):
            if v == 1:
                break
            since_last += 1
        else:
            since_last = n_rows  # 窗口内从未空过
        # 当前是否连续活跃（非空）streak
        active_streak = since_last
        # due_ratio：超过平均周期越多越「该出空区」
        if mean_gap and mean_gap > 0:
            due_ratio = round(since_last / mean_gap, 2)
        else:
            due_ratio = None
        zones.append(
            {
                "zone": name,
                "range": list(EMPTY_ZONE_DEFS[zi]),
                "empty_count": empty_count,
                "empty_rate": round(empty_count / n_rows, 3),
                "mean_gap": mean_gap,
                "since_last_empty": since_last,
                "active_streak": active_streak,
                "due_ratio": due_ratio,
                "flags": flags,
            }
        )

    # 预测方法说明（经 800 期回测，见 references/EMPTY_ZONE_ANALYSIS.md）：
    # - 朴素 "due_ratio 最该空" 命中率 ~11%，反低于结构基线 → 已弃用。
    # - 严格三等分区空区是 ~10-16%/区 的弱事件，动态预测难超基线。
    # - 唯一稳定信号：窗口内空区频率最高的区（结构性偏冷，常为 25-35，~16%）。
    # 因此预测 = 窗口内空区频率最高的区；并给出「两个最冷区」作为更宽覆盖（~26%）。
    by_empty_rate = sorted(
        zones, key=lambda z: (z["empty_rate"], z["since_last_empty"]), reverse=True
    )
    predicted_empty = by_empty_rate[0]["zone"]
    pe_idx = EMPTY_ZONE_NAMES.index(predicted_empty)
    excluded_range = list(EMPTY_ZONE_DEFS[pe_idx])

    # 近窗各区命中球数 → 最冷的两个区（候选空区，覆盖更宽）
    recent = window[-8:] if n_rows >= 8 else window
    zone_recent_hits = [0, 0, 0]
    for rec in recent:
        for x in rec["main"]:
            zone_recent_hits[_zone_of(int(x))] += 1
    cold_order = sorted(range(3), key=lambda zi: zone_recent_hits[zi])
    two_coldest = [EMPTY_ZONE_NAMES[zi] for zi in cold_order[:2]]
    hottest_zone = EMPTY_ZONE_NAMES[cold_order[-1]]
    active_zones = [z["zone"] for z in zones if z["zone"] != predicted_empty]

    return {
        "periods": n_rows,
        "range": [window[0]["issue"], window[-1]["issue"]],
        "min_run": min_run,
        "zones": zones,
        "per_period_runs": per_period_runs,
        "prediction": {
            "predicted_empty_zone": predicted_empty,
            "excluded_range": excluded_range,
            "active_zones": active_zones,
            "two_coldest_zones": two_coldest,
            "hottest_zone": hottest_zone,
            "empty_rate_ref": by_empty_rate[0]["empty_rate"],
            "method": "highest_empty_rate",
            "note": "严格三等分区空区接近基线弱事件；本预测为结构性偏冷区，非强周期信号。",
        },
    }


def run_empty_zone_backtest(
    records: list[dict[str, Any]],
    *,
    window: int = 30,
    test_issues: int = 500,
    min_run: int = 6,
) -> dict[str, Any]:
    """
    回测空区预测命中率：用前 window 期预测下期空区，对比实际。
    基线：随机猜 1/3（≈33.3%）。同时统计「实际确有空区」的频率。
    """
    if len(records) < window + 1:
        raise ValueError(f"数据不足，至少需要 {window + 1} 期")

    start_idx = max(window, len(records) - test_issues)
    tested = 0
    hit = 0  # 首选预测空区 == 实际空区之一
    hit_two = 0  # 两个最冷候选区命中实际空区
    actual_has_empty = 0  # 实际下期确有 ≥1 个空分区
    multi_empty = 0  # 实际下期 ≥2 个空分区
    zone_empty_marginal = {name: 0 for name in EMPTY_ZONE_NAMES}  # 各区边际空区频率
    per_zone_pred = {name: 0 for name in EMPTY_ZONE_NAMES}
    per_zone_hit = {name: 0 for name in EMPTY_ZONE_NAMES}

    for i in range(start_idx, len(records)):
        hist = records[i - window : i]
        actual = records[i]
        analysis = analyze_empty_zones(hist, min_run=min_run)
        pred = analysis["prediction"]["predicted_empty_zone"]
        two_cold = analysis["prediction"]["two_coldest_zones"]

        present = {_zone_of(int(x)) for x in actual["main"]}
        empty_zones_actual = [
            EMPTY_ZONE_NAMES[zi] for zi in range(len(EMPTY_ZONE_DEFS)) if zi not in present
        ]

        tested += 1
        per_zone_pred[pred] += 1
        for z in empty_zones_actual:
            zone_empty_marginal[z] += 1
        if empty_zones_actual:
            actual_has_empty += 1
        if len(empty_zones_actual) >= 2:
            multi_empty += 1
        if pred in empty_zones_actual:
            hit += 1
            per_zone_hit[pred] += 1
        if any(z in empty_zones_actual for z in two_cold):
            hit_two += 1

    marginal_rates = {
        name: round(zone_empty_marginal[name] / tested, 4) if tested else 0
        for name in EMPTY_ZONE_NAMES
    }
    baseline_marginal_mean = round(sum(marginal_rates.values()) / 3, 4)

    return {
        "version": 2,
        "method": "empty_zone_highest_empty_rate",
        "params": {"window": window, "test_issues": test_issues, "min_run": min_run},
        "sample": {
            "test_count": tested,
            "issue_range": [records[start_idx]["issue"], records[-1]["issue"]],
        },
        "results": {
            "predict_hit_rate": round(hit / tested, 4) if tested else 0,
            "two_coldest_hit_rate": round(hit_two / tested, 4) if tested else 0,
            "baseline_marginal_mean": baseline_marginal_mean,
            "baseline_best_fixed": max(marginal_rates.values()) if tested else 0,
            "zone_marginal_empty_rate": marginal_rates,
            "actual_has_empty_rate": round(actual_has_empty / tested, 4) if tested else 0,
            "multi_empty_rate": round(multi_empty / tested, 4) if tested else 0,
        },
        "per_zone": {
            name: {
                "predicted": per_zone_pred[name],
                "hit": per_zone_hit[name],
                "precision": round(per_zone_hit[name] / per_zone_pred[name], 4)
                if per_zone_pred[name]
                else None,
            }
            for name in EMPTY_ZONE_NAMES
        },
        "verdict": (
            "严格三等分区空区为弱事件(各区~10-16%)，动态预测难超随机基线；"
            "本模块作描述+结构偏冷弱信号使用，不做高确定性整区排除。"
        ),
    }


# ============================================================
# 统一定号：每次预测固定输出 7 前区 + 3 后区
# 整合 程序三(局部趋势落点) + 程序四(偏差带) + 程序五(空区弱权重)
# ============================================================

FINAL_FRONT_COUNT = 7
FINAL_BACK_COUNT = 3


def compute_recommendation_scores(
    window: list[dict[str, Any]],
    *,
    profile: dict[str, Any] | None = None,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    计算 L1 全分区评分（趋势 + 偏差带 + 超期 + 空区 + 重号），供定号或 L2 融合使用。
    """
    local = analyze_local_trends(window)
    empty = analyze_empty_zones(window)
    adjusted = apply_deviation_band(local, profile) if profile else None

    front_scores: dict[int, float] = {}
    if adjusted:
        for item in adjusted["front_adjusted"]:
            front_scores[item["num"]] = float(item["score"])
    for item in local["front"]["next_candidates"]:
        front_scores[item["num"]] = max(front_scores.get(item["num"], 0), float(item["score"]))

    back_scores: dict[int, float] = {}
    if adjusted:
        for item in adjusted["back_adjusted"]:
            back_scores[item["num"]] = float(item["score"])
    for item in local["back"]["next_candidates"]:
        back_scores[item["num"]] = max(back_scores.get(item["num"], 0), float(item["score"]))

    front_freq: dict[int, int] = {}
    back_freq: dict[int, int] = {}
    for rec in window:
        for x in rec["main"]:
            front_freq[int(x)] = front_freq.get(int(x), 0) + 1
        for x in rec["bonus"]:
            back_freq[int(x)] = back_freq.get(int(x), 0) + 1
    max_score = max(front_scores.values(), default=1.0)
    for n in range(1, 36):
        seed = front_freq.get(n, 0) * (max_score * 0.05)
        front_scores[n] = front_scores.get(n, 0) + seed + 0.01
    max_bscore = max(back_scores.values(), default=1.0)
    for n in range(1, 13):
        seed = back_freq.get(n, 0) * (max_bscore * 0.05)
        back_scores[n] = back_scores.get(n, 0) + seed + 0.01

    end_issue = window[-1]["issue"]
    fmiss = {n: 0 for n in range(1, 36)}
    bmiss = {n: 0 for n in range(1, 13)}
    miss_source = records if records is not None else window
    for rec in miss_source:
        if rec["issue"] > end_issue:
            break
        m = {int(x) for x in rec["main"]}
        b = {int(x) for x in rec["bonus"]}
        for n in range(1, 36):
            fmiss[n] = 0 if n in m else fmiss[n] + 1
        for n in range(1, 13):
            bmiss[n] = 0 if n in b else bmiss[n] + 1
    front_avg_miss = 6
    back_avg_miss = 5
    for n in range(1, 36):
        if fmiss[n] > front_avg_miss:
            front_scores[n] += (fmiss[n] - front_avg_miss) * (max_score * 0.045)
    for n in range(1, 13):
        if bmiss[n] > back_avg_miss:
            back_scores[n] += (bmiss[n] - back_avg_miss) * (max_bscore * 0.045)

    hottest = empty["prediction"]["hottest_zone"]
    coldest = empty["prediction"]["predicted_empty_zone"]
    hot_idx = EMPTY_ZONE_NAMES.index(hottest)
    cold_idx = EMPTY_ZONE_NAMES.index(coldest)
    for num in list(front_scores):
        zi = _zone_of(num)
        if zi == hot_idx:
            front_scores[num] *= 1.15
        elif zi == cold_idx:
            front_scores[num] *= 0.85

    last_front = {int(x) for x in window[-1]["main"]}
    last_back = {int(x) for x in window[-1]["bonus"]}
    front_protect = max_score * 0.45
    back_protect = max_bscore * 0.45
    for n in last_front:
        front_scores[n] = front_scores.get(n, 0) + front_protect
    for n in last_back:
        back_scores[n] = back_scores.get(n, 0) + back_protect

    return {
        "front_scores": front_scores,
        "back_scores": back_scores,
        "local": local,
        "empty": empty,
        "adjusted": adjusted,
        "last_front": last_front,
        "last_back": last_back,
    }


def select_front_pool(
    front_scores: dict[int, float],
    front_count: int,
) -> list[int]:
    """前区定号：高分优先 + 至少覆盖 2 个三分区."""
    ranked_front = sorted(front_scores.items(), key=lambda x: (-x[1], x[0]))
    chosen: list[int] = []
    zones_used: set[int] = set()
    for num, _ in ranked_front:
        chosen.append(num)
        zones_used.add(_zone_of(num))
        if len(chosen) >= front_count:
            break
    if len(zones_used) < 2 and len(ranked_front) > front_count:
        missing_zone_nums = [
            (n, s) for n, s in ranked_front
            if _zone_of(n) not in zones_used and n not in chosen
        ]
        if missing_zone_nums:
            chosen[-1] = missing_zone_nums[0][0]
    return sorted(chosen[:front_count])


def select_back_pool(back_scores: dict[int, float], back_count: int) -> list[int]:
    return sorted(
        n for n, _ in sorted(back_scores.items(), key=lambda x: (-x[1], x[0]))[:back_count]
    )


def build_final_recommendation(
    window: list[dict[str, Any]],
    *,
    profile: dict[str, Any] | None = None,
    front_count: int = FINAL_FRONT_COUNT,
    back_count: int = FINAL_BACK_COUNT,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    汇总各程序信号，产出固定 front_count 前区 + back_count 后区 的推荐池。

    评分来源：
      1. 局部趋势候选 next_candidates（趋势落点加权）
      2. 偏差带扩展 apply_deviation_band（落点 ±N，若有偏差档案）
      3. 超期回补：遗漏 > 平均间隔的冷号按超期幅度加分（均值回归核心）
      4. 空区弱权重：最热活跃区 ×1.15，结构性偏冷区 ×0.85
      5. 重号保护：上期开奖号叠加保护分，不被冷区回落剔除
    结构校验：前区尽量覆盖 ≥2 个分区，避免码全挤一区。

    records 若传入全量历史，则用全历史遗漏值（更准）；否则退化为窗口内遗漏。
    """
    scored = compute_recommendation_scores(window, profile=profile, records=records)
    front_scores = dict(scored["front_scores"])
    back_scores = dict(scored["back_scores"])
    local = scored["local"]
    empty = scored["empty"]
    adjusted = scored["adjusted"]
    last_front = scored["last_front"]
    last_back = scored["last_back"]

    def _ensure_pool(scores: dict[int, float], lo: int, hi: int, need: int) -> None:
        if len(scores) >= need:
            return
        for n in range(lo, hi + 1):
            if n not in scores:
                scores[n] = 0.1
            if len(scores) >= need + 5:
                break

    _ensure_pool(front_scores, 1, 35, front_count)
    _ensure_pool(back_scores, 1, 12, back_count)

    front_final = select_front_pool(front_scores, front_count)
    back_final = select_back_pool(back_scores, back_count)

    # 结构指标
    zone_dist = [0, 0, 0]
    for n in front_final:
        zone_dist[_zone_of(n)] += 1
    odd = sum(1 for n in front_final if n % 2)
    small = sum(1 for n in front_final if n <= 17)

    return {
        "front": front_final,
        "back": back_final,
        "front_count": front_count,
        "back_count": back_count,
        "structure": {
            "zone_dist": {EMPTY_ZONE_NAMES[i]: zone_dist[i] for i in range(3)},
            "odd_even": f"{odd}:{front_count - odd}",
            "size_small_large": f"{small}:{front_count - small}",
            "sum": sum(front_final),
        },
        "signals": {
            "deviation_band": adjusted["recommended_band"] if adjusted else None,
            "hot_zone": empty["prediction"]["hottest_zone"],
            "cold_zone": empty["prediction"]["predicted_empty_zone"],
            "trend_chains_front": len(local["front"]["chains"]),
            "repeat_protected": {
                "front": sorted(n for n in last_front if n in front_final),
                "back": sorted(n for n in last_back if n in back_final),
            },
        },
        "note": (
            f"{front_count}+{back_count} 为加权候选池（非投注建议）；纯趋势精确率约 20%，"
            "已叠加偏差带 + 空区弱权重 + 重号保护（上期号保底进池）。"
        ),
    }
