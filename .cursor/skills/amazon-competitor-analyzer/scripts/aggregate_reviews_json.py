"""外部完整评论聚合器（竞品分析 · review-sentiment 静态摘要数据源）。

V3 起改用 `review_core`，**数据驱动**关键词/主题，不再绑定任何品类：
- 关键词（好评/差评/词云）由词频自动抽取，替代旧版写死的英文信号词清单。
- 主题（theme）改为**可选**：通过 --themes themes.json 传入 {主题名:[关键词...]}；
  不传则跳过主题统计，由数据驱动 Top 关键词承担"痛点速览"。
- 输入兼容 .json 与 .xlsx（openpyxl 直读，无需先手动转 JSON）。

默认全量、不按 ASIN 剔除（文件内多 ASIN = 同系列不同款式/颜色）；
仅当用户明确只看某一款时，用 --asin 过滤。

输出字段与 render_report_html.py 的 review-sentiment 渲染器对齐，
可直接作为 AI 填写 visual.json 的数据依据。
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
from typing import Any

import review_core as rc


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="聚合评论（数据驱动 · 默认全量，不按 ASIN 剔除 · 支持 .json/.xlsx）"
    )
    p.add_argument("--input", required=True, help="评论文件路径（.json 或 .xlsx）")
    p.add_argument(
        "--meta",
        default="",
        help="metadata.json 路径；不传 --asin 时从中取目标 asin（只分析 URL 对应竞品）",
    )
    p.add_argument(
        "--asin",
        default="",
        help="显式指定目标 ASIN；默认取 --meta 的 asin 过滤",
    )
    p.add_argument(
        "--all-variants",
        action="store_true",
        help="逃生开关：分析文件内全部 ASIN（同系列所有款式/颜色），仅用户明确要求时使用",
    )
    p.add_argument(
        "--themes",
        default="",
        help="可选主题配置 JSON 路径，格式 {主题名:[关键词...]}；不传则跳过主题统计",
    )
    p.add_argument(
        "--output",
        default="",
        help="输出 JSON 路径；默认与输入同目录的 <stem>_aggregate.json",
    )
    p.add_argument(
        "--top-voice", type=int, default=3, help="每个星级桶择取的原话候选数量（默认 3）"
    )
    return p.parse_args()


def recent_vs_hist(records: list[dict[str, Any]], window_days: int = 90) -> dict[str, Any] | None:
    """近 window_days 天 vs 历史的均分/低星比对照（识别质量下滑）。"""
    dated = [(r["date"], r) for r in records if r["date"]]
    if len(dated) < 2:
        return None
    dates = [datetime.date.fromisoformat(d) for d, _ in dated]
    max_date = max(dates)
    cutoff = max_date - datetime.timedelta(days=window_days)
    recent = [r for d, r in dated if datetime.date.fromisoformat(d) > cutoff]
    hist = [r for d, r in dated if datetime.date.fromisoformat(d) <= cutoff]
    if not recent or not hist:
        return None
    rs = rc._bucket_stats(recent)
    hs = rc._bucket_stats(hist)
    delta_low = round(rs["low_star_pct"] - hs["low_star_pct"], 1)
    if delta_low >= 5:
        verdict = "近期低星比上升，质量/口碑有下滑信号"
    elif delta_low <= -5:
        verdict = "近期低星比下降，口碑趋于改善"
    else:
        verdict = "近期与历史基本持平"
    return {
        "window_days": window_days,
        "max_date": max_date.isoformat(),
        "recent_label": f"近 {window_days} 天",
        "recent_count": rs["count"],
        "recent_avg": rs["avg"],
        "recent_low_pct": rs["low_star_pct"],
        "hist_label": f"{window_days} 天前",
        "hist_count": hs["count"],
        "hist_avg": hs["avg"],
        "hist_low_pct": hs["low_star_pct"],
        "delta_low_pct": delta_low,
        "verdict": verdict,
    }


def main() -> int:
    args = parse_args()

    themes: dict[str, list[str]] = {}
    if args.themes:
        themes = json.loads(Path(args.themes).read_text(encoding="utf-8-sig"))

    meta_json: dict[str, Any] = {}
    if args.meta and Path(args.meta).exists():
        try:
            meta_json = json.loads(Path(args.meta).read_text(encoding="utf-8"))
        except Exception:
            meta_json = {}

    # 全局综合评分口径（页面 global ratings，覆盖全部评论；与抓取样本严格区分）
    global_rating = rc.global_rating_from_meta(meta_json)

    target_asin = rc.resolve_target_asin(args.asin, meta_json, args.all_variants)
    records, meta = rc.load_reviews(args.input, asin_filter=target_asin)
    total = len(records)
    if total == 0:
        avail = ", ".join(f"{k}({v})" for k, v in meta["distinct_asin"].items())
        raise ValueError(
            f"目标 ASIN '{target_asin}' 在评论文件内 0 条评论。"
            f"文件内可用 ASIN：{avail}。请确认 ASIN，或加 --all-variants 分析全系列。"
        )

    hist = rc.star_histogram(records)
    # 直方图对齐旧字段：[{star, percent}]
    histogram = [{"star": h["star"], "percent": h["percent"]} for h in hist["histogram"]]
    if target_asin:
        scoped_distinct_asin = {target_asin: total}
        scoped_distinct_asin_count = 1
    else:
        scoped_distinct_asin = meta["distinct_asin"]
        scoped_distinct_asin_count = meta["distinct_asin_count"]

    positive_keywords = rc.extract_keywords(
        [r for r in records if r["stars"] >= 4], top_n=20
    )
    critical_keywords = rc.extract_keywords(
        [r for r in records if 1 <= r["stars"] <= 2], top_n=20
    )

    result: dict[str, Any] = {
        "input": meta["source"],
        "scope": meta["scope"],
        "distinct_asin_count": scoped_distinct_asin_count,
        "distinct_asin": scoped_distinct_asin,
        "raw_distinct_asin_count": meta["distinct_asin_count"],
        "raw_distinct_asin": meta["distinct_asin"],
        # ───────────────────────────────────────────────────────────────
        # 口径一：全局综合评分（主口径）——覆盖全部评论，是产品真实口碑分。
        # ───────────────────────────────────────────────────────────────
        "global": global_rating,
        # ───────────────────────────────────────────────────────────────
        # 口径二：抓取样本（挖掘口径）——有限样本，受星级配额放大低星，
        # 仅用于挖抱怨主题/真实原话，**不可当作产品综合分**。
        # 以下 total/avg/histogram/low_star_* 全部属于"样本口径"。
        # ───────────────────────────────────────────────────────────────
        "sample": {
            "scope": meta["scope"],
            "total": total,
            "avg": hist["avg"],
            "low_star_ratio_percent": hist["low_star_ratio_percent"],
            "caveat": (
                "样本均分/低星比受抓取星级配额影响（每星级上限 100 条，常按正/负配额抓取），"
                "会系统性放大低星占比，可能显著低于全局综合评分，仅用于挖掘抱怨主题。"
            ),
        },
        "total": total,
        "avg": hist["avg"],
        "star_counts": hist["star_counts"],
        "histogram": histogram,
        "low_star_count": hist["star_counts"]["1"] + hist["star_counts"]["2"],
        "low_star_ratio_percent": hist["low_star_ratio_percent"],
        "theme_summary": rc.theme_summary(records, themes),
        "positive_keywords": positive_keywords,
        "critical_keywords": critical_keywords,
        "word_cloud": rc.keyword_cloud(records),
        "variant_breakdown": rc.group_breakdown(records, "asin"),
        "variation_breakdown": rc.group_breakdown(records, "variation"),
        "country_breakdown": rc.group_breakdown(records, "country"),
        "vp_breakdown": rc.vp_breakdown(records),
        "trend": recent_vs_hist(records),
        "real_voice_candidates": rc.real_voice(records, per_bucket=args.top_voice),
        "note": (
            "【双口径】global=全局综合评分（覆盖全部评论，产品真实口碑主口径）；"
            "顶层 total/avg/histogram/low_star_* 与 sample 块均为抓取样本口径。"
            "样本受星级配额抓取放大低星，样本均分**不等同于** Amazon 页面全局评分，"
            "撰写报告/评分时综合分一律取 global，样本仅用于挖抱怨主题与真实原话。"
            "scope=all_variants 时样本覆盖文件内全部 ASIN（同系列不同款式/颜色）；"
            "关键词/主题均为数据驱动，可泛化任意品类。"
        ),
    }

    in_path = Path(meta["source"])
    out_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else in_path.parent / f"{in_path.stem}_aggregate.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["output"] = str(out_path)

    # 口径偏差告警（提醒 agent：综合分取 global，勿用样本均分）
    import sys

    g_avg = global_rating.get("avg") if global_rating.get("available") else None
    s_avg = hist["avg"]
    if g_avg is not None:
        delta = round(abs(float(g_avg) - float(s_avg)), 2)
        tag = "⚠️ 偏差显著" if delta >= 1.0 else "口径对照"
        print(
            f"[{tag}] 全局综合评分 {g_avg}★（覆盖 {global_rating.get('rating_count')} 条全部评论） "
            f"vs 抓取样本均分 {s_avg}★（{total} 条样本，受配额放大低星）。"
            f"报告综合分一律取全局 {g_avg}★，样本仅用于挖抱怨主题。",
            file=sys.stderr,
        )
    else:
        print(
            "[提示] metadata.json 未提供全局综合评分（reviews.histogram / rating 缺失），"
            "无法分离全局口径；样本均分仅代表抓取样本，勿当作产品综合分。",
            file=sys.stderr,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
