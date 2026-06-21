#!/usr/bin/env python3
"""L2 + L1 融合定号：以 L2 看图预测为锚，L1 算法评分辅助修正."""

from __future__ import annotations

from typing import Any

from dlt_data import select_back_pool, select_front_pool


def _normalize_scores(scores: dict[int, float]) -> dict[int, float]:
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    if hi <= lo:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _l1_top_set(scores: dict[int, float], count: int) -> set[int]:
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    return {n for n, _ in ranked[:count]}


def _swap_correct(
    current: list[int],
    combined: dict[int, float],
    *,
    lo: int,
    hi: int,
    max_replace: int,
    min_margin: float = 0.03,
) -> list[int]:
    """按合分从低到高替换 L2 号，最多 max_replace 次."""
    pool = sorted(set(int(x) for x in current))
    for _ in range(max_replace):
        if not pool:
            break
        worst = min(pool, key=lambda n: combined.get(n, 0.0))
        outside = [n for n in range(lo, hi + 1) if n not in pool]
        if not outside:
            break
        best = max(outside, key=lambda n: combined.get(n, 0.0))
        if combined.get(best, 0.0) > combined.get(worst, 0.0) + min_margin:
            pool.remove(worst)
            pool.append(best)
        else:
            break
    return sorted(pool)


def fuse_l2_with_l1(
    visual_front: list[int],
    visual_back: list[int],
    l1_front_scores: dict[int, float],
    l1_back_scores: dict[int, float],
    front_count: int,
    back_count: int,
    *,
    visual_weight: float = 0.5,
    l1_weight: float = 1.0,
    consensus_bonus: float = 0.4,
    max_replace_ratio: float = 0.35,
) -> dict[str, Any]:
    """
    L2-primary 融合：
      1. 合分 = L1 归一化×l1_weight + L2 锚定×visual_weight + 共识加成
      2. 对 L2 原号做有限次替换（7+3 最多 2 个，15+5 最多 5 个）
      3. 用 L1 结构选号（前区三分区 ≥2）产出最终池
    """
    vf = [int(x) for x in visual_front]
    vb = [int(x) for x in visual_back]
    norm_f = _normalize_scores(l1_front_scores)
    norm_b = _normalize_scores(l1_back_scores)

    l1_front_top = _l1_top_set(l1_front_scores, min(front_count * 2, 20))
    l1_back_top = _l1_top_set(l1_back_scores, min(back_count * 2, 8))
    consensus_f = set(vf) & l1_front_top
    consensus_b = set(vb) & l1_back_top

    def _combined(n: int, *, visual: list[int], consensus: set[int], norm: dict[int, float]) -> float:
        score = l1_weight * norm.get(n, 0.0)
        if n in visual:
            score += visual_weight
        if n in consensus:
            score += consensus_bonus
        return score

    combined_f = {n: _combined(n, visual=vf, consensus=consensus_f, norm=norm_f) for n in range(1, 36)}
    combined_b = {n: _combined(n, visual=vb, consensus=consensus_b, norm=norm_b) for n in range(1, 13)}

    max_f_replace = max(1, int(round(front_count * max_replace_ratio)))
    max_b_replace = max(1, int(round(back_count * max_replace_ratio)))

    swapped_f = _swap_correct(vf, combined_f, lo=1, hi=35, max_replace=max_f_replace)
    swapped_b = _swap_correct(vb, combined_b, lo=1, hi=12, max_replace=max_b_replace)

    # 共识号强制保留：若被换出则换回合分最低的非常识号
    for n in consensus_f:
        if n not in swapped_f and len(swapped_f) >= front_count:
            worst_non = min(
                (x for x in swapped_f if x not in consensus_f),
                key=lambda x: combined_f[x],
                default=None,
            )
            if worst_non is not None and combined_f[n] >= combined_f[worst_non]:
                swapped_f.remove(worst_non)
                swapped_f.append(n)
                swapped_f = sorted(swapped_f)

    for n in consensus_b:
        if n not in swapped_b and len(swapped_b) >= back_count:
            worst_non = min(
                (x for x in swapped_b if x not in consensus_b),
                key=lambda x: combined_b[x],
                default=None,
            )
            if worst_non is not None and combined_b[n] >= combined_b[worst_non]:
                swapped_b.remove(worst_non)
                swapped_b.append(n)
                swapped_b = sorted(swapped_b)

    # 在合分空间做最终定号（允许从 swapped 候选向邻域扩展）
    expand_f = set(swapped_f)
    for n, _ in sorted(combined_f.items(), key=lambda x: (-x[1], x[0]))[: front_count + 5]:
        expand_f.add(n)
    expand_b = set(swapped_b)
    for n, _ in sorted(combined_b.items(), key=lambda x: (-x[1], x[0]))[: back_count + 3]:
        expand_b.add(n)

    front_final = select_front_pool({n: combined_f[n] for n in expand_f}, front_count)
    back_final = select_back_pool({n: combined_b[n] for n in expand_b}, back_count)

    l1_front_pick = select_front_pool(l1_front_scores, front_count)
    l1_back_pick = select_back_pool(l1_back_scores, back_count)

    return {
        "front": front_final,
        "back": back_final,
        "method": "l2_l1_fusion",
        "fusion_meta": {
            "visual_weight": visual_weight,
            "l1_weight": l1_weight,
            "consensus_bonus": consensus_bonus,
            "max_replace_ratio": max_replace_ratio,
            "visual_front": sorted(vf),
            "visual_back": sorted(vb),
            "swapped_front": swapped_f,
            "swapped_back": swapped_b,
            "l1_front": l1_front_pick,
            "l1_back": l1_back_pick,
            "consensus_front": sorted(consensus_f),
            "consensus_back": sorted(consensus_b),
            "replaced_front": sorted(set(vf) - set(front_final)),
            "added_front": sorted(set(front_final) - set(vf)),
            "replaced_back": sorted(set(vb) - set(back_final)),
            "added_back": sorted(set(back_final) - set(vb)),
        },
    }


def fuse_prediction_block(
    visual_block: dict[str, Any],
    l1_front_scores: dict[int, float],
    l1_back_scores: dict[int, float],
    front_count: int,
    back_count: int,
    **kwargs: Any,
) -> dict[str, Any]:
    fused = fuse_l2_with_l1(
        visual_block["front"],
        visual_block["back"],
        l1_front_scores,
        l1_back_scores,
        front_count,
        back_count,
        **kwargs,
    )
    reasoning = visual_block.get("reasoning", "")
    meta = fused["fusion_meta"]
    parts = []
    if meta["replaced_front"] or meta["added_front"]:
        parts.append(
            f"前区 L1 修正: 替换 {meta['replaced_front']} → 加入 {meta['added_front']}"
        )
    if meta["replaced_back"] or meta["added_back"]:
        parts.append(
            f"后区 L1 修正: 替换 {meta['replaced_back']} → 加入 {meta['added_back']}"
        )
    if meta["consensus_front"] or meta["consensus_back"]:
        parts.append(
            f"共识号 前{meta['consensus_front']} 后{meta['consensus_back']}"
        )
    fused["reasoning"] = (
        (reasoning + " | L1融合: " + "；".join(parts)) if parts else reasoning + " | L1融合: 无替换"
    )
    return fused
