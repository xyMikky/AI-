#!/usr/bin/env python3
"""大乐透 harness 公共计分与格式定义（L1 algo / L2 visual 共用）."""

from __future__ import annotations

import random
from typing import Any

FRONT_TOTAL = 35
BACK_TOTAL = 12
DRAW_FRONT = 5
DRAW_BACK = 2

FORMATS: dict[str, tuple[int, int]] = {
    "7+3": (7, 3),
    "15+5": (15, 5),
}

_PRIZE = {
    (5, 2): 1, (5, 1): 2, (5, 0): 3, (4, 2): 4, (4, 1): 5,
    (3, 2): 6, (4, 0): 7, (3, 1): 8, (2, 2): 8, (3, 0): 9,
    (1, 2): 9, (2, 1): 9, (0, 2): 9,
}


def parse_formats(arg: str) -> dict[str, tuple[int, int]]:
    if arg == "both":
        return dict(FORMATS)
    if arg not in FORMATS:
        raise SystemExit(f"未知格式 {arg}，可选 {list(FORMATS)} 或 both")
    return {arg: FORMATS[arg]}


def prize_tier(front_hits: int, back_hits: int) -> int:
    f = min(front_hits, DRAW_FRONT)
    b = min(back_hits, DRAW_BACK)
    return _PRIZE.get((f, b), 0)


def score_pool(
    front_pool: list[int],
    back_pool: list[int],
    actual_front: set[int],
    actual_back: set[int],
) -> dict[str, Any]:
    fhit = len(set(front_pool) & actual_front)
    bhit = len(set(back_pool) & actual_back)
    return {
        "front_hits": fhit,
        "back_hits": bhit,
        "tier": prize_tier(fhit, bhit),
    }


def validate_prediction_numbers(
    front: list[int],
    back: list[int],
    fcount: int,
    bcount: int,
) -> None:
    if len(front) != fcount or len(set(front)) != fcount:
        raise ValueError(f"前区需 {fcount} 个不重复号码，实际 {front}")
    if len(back) != bcount or len(set(back)) != bcount:
        raise ValueError(f"后区需 {bcount} 个不重复号码，实际 {back}")
    for n in front:
        if not 1 <= n <= FRONT_TOTAL:
            raise ValueError(f"前区号码越界: {n}")
    for n in back:
        if not 1 <= n <= BACK_TOTAL:
            raise ValueError(f"后区号码越界: {n}")


def random_pool_baseline(
    actual_front: set[int],
    actual_back: set[int],
    fcount: int,
    bcount: int,
    trials: int,
    rng: random.Random,
) -> dict[str, float]:
    fh = bh = prize = 0
    for _ in range(trials):
        fp = set(rng.sample(range(1, FRONT_TOTAL + 1), fcount))
        bp = set(rng.sample(range(1, BACK_TOTAL + 1), bcount))
        f = len(fp & actual_front)
        b = len(bp & actual_back)
        fh += f
        bh += b
        if prize_tier(f, b):
            prize += 1
    return {
        "front_hits": fh / trials,
        "back_hits": bh / trials,
        "prize_rate": prize / trials,
    }


def aggregate_scores(rows: list[dict[str, Any]], fmt_name: str) -> dict[str, Any]:
    if not rows:
        return {}
    n = len(rows)
    fh = sum(r["front_hits"] for r in rows)
    bh = sum(r["back_hits"] for r in rows)
    pc = sum(1 for r in rows if r.get("tier"))
    tiers: dict[int, int] = {}
    for r in rows:
        t = r.get("tier") or 0
        if t:
            tiers[t] = tiers.get(t, 0) + 1
    bf = sum(r.get("baseline_front_hits", 0) for r in rows)
    bb = sum(r.get("baseline_back_hits", 0) for r in rows)
    bp = sum(r.get("baseline_prize_rate", 0) for r in rows)
    fc, bc = FORMATS[fmt_name]
    return {
        "pool": f"{fc}+{bc}",
        "periods": n,
        "avg_front_hits": round(fh / n, 4),
        "avg_back_hits": round(bh / n, 4),
        "prize_rate": round(pc / n, 4),
        "prize_tiers": dict(sorted(tiers.items())),
        "random_baseline": {
            "avg_front_hits": round(bf / n, 4),
            "avg_back_hits": round(bb / n, 4),
            "prize_rate": round(bp / n, 4),
        },
        "edge": {
            "front_hits": round((fh / n) - (bf / n), 4),
            "back_hits": round((bh / n) - (bb / n), 4),
            "prize_rate": round((pc / n) - (bp / n), 4),
        },
    }
