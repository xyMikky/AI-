#!/usr/bin/env python3
"""大乐透空区分析 — 三分区空区周期 + 下期空区预测，绿色横条标注 PNG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from dlt_data import (
    BACK_RANGE,
    EMPTY_ZONE_NAMES,
    FRONT_RANGE,
    analyze_empty_zones,
    build_chart_rows,
    load_records,
    pick_window,
    resolve_data_path,
    run_empty_zone_backtest,
)
from trend_chart import (
    COLOR_BACK_HIT,
    COLOR_FRONT_HIT,
    COLOR_GRID,
    COLOR_OMIT,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PNG_SCALE,
    FRONT_GROUPS,
    ChartLayout,
    _draw_vertical_separators,
    _text_center,
)

DEFAULT_ZONE_COUNT = 30
COLOR_EMPTY_BOX = "#27ae60"
COLOR_PRED_BOX = "#f39c12"


def render_empty_zone_png(
    rows: list[dict[str, Any]],
    analysis: dict[str, Any],
    target_issue: str,
    count: int,
    data_path: Path,
    out_path: Path,
    scale: float = DEFAULT_PNG_SCALE,
) -> None:
    layout = ChartLayout(scale=scale)
    first_issue = rows[0]["issue"]
    last_issue = rows[-1]["issue"]
    pred = analysis["prediction"]
    title = f"大乐透空区分析 {first_issue}—{last_issue}（近{len(rows)}期）"
    subtitle = (
        f"基准期 {target_issue} · 绿框=空区(连续≥{analysis['min_run']}号未开) · "
        f"预测下期空区 {pred['predicted_empty_zone']} · {data_path.name}"
    )

    font_title = layout.font_title()
    font_sub = layout.font_sub()
    font_header = layout.font_header()
    font_issue = layout.font_issue()
    font_ball = layout.font_ball()
    font_omit = layout.font_omit()

    header_h = layout.cell_h * 2
    extra_row = layout.cell_h
    table_w = layout.table_width()
    table_h = header_h + len(rows) * layout.cell_h + extra_row
    margin = layout.margin
    img_w = margin * 2 + table_w
    img_h = margin * 2 + layout.title_h + layout.subtitle_h + table_h + layout.bottom_pad

    img = Image.new("RGB", (img_w, img_h), "#f5f5f5")
    draw = ImageDraw.Draw(img)

    _text_center(draw, (margin, margin, img_w - margin, margin + layout.title_h), title, font_title, "#333333")
    _text_center(
        draw,
        (margin, margin + layout.title_h, img_w - margin, margin + layout.title_h + layout.subtitle_h),
        subtitle,
        font_sub,
        "#666666",
    )

    x0 = margin
    y0 = margin + layout.title_h + layout.subtitle_h

    draw.rectangle([x0, y0, x0 + layout.issue_w, y0 + header_h], fill="#fafafa", outline=COLOR_GRID)
    _text_center(draw, (x0, y0, x0 + layout.issue_w, y0 + header_h), "期号", font_header, "#555555")
    tx = x0 + layout.issue_w
    draw.rectangle([tx, y0, tx + layout.tail_w, y0 + header_h], fill="#fafafa", outline=COLOR_GRID)
    _text_center(draw, (tx, y0, tx + layout.tail_w, y0 + header_h), "和尾", font_header, "#555555")

    y_group = y0
    for g in FRONT_GROUPS:
        gx = layout.front_x(x0, g.start)
        gw = len(g) * layout.cell_w
        draw.rectangle([gx, y_group, gx + gw, y_group + layout.cell_h], fill="#fff5f5", outline=COLOR_GRID)
        _text_center(draw, (gx, y_group, gx + gw, y_group + layout.cell_h), f"{g.start:02d}-{g.stop - 1:02d}", font_header, "#c62828")

    bx = layout.back_x(x0, 1)
    bw = len(BACK_RANGE) * layout.cell_w
    draw.rectangle([bx, y_group, bx + bw, y_group + layout.cell_h], fill="#f0f7ff", outline=COLOR_GRID)
    _text_center(draw, (bx, y_group, bx + bw, y_group + layout.cell_h), "后区01-12", font_header, "#1565c0")

    y_nums = y0 + layout.cell_h
    for n in FRONT_RANGE:
        fx = layout.front_x(x0, n)
        draw.rectangle([fx, y_nums, fx + layout.cell_w, y_nums + layout.cell_h], fill="#fff5f5", outline=COLOR_GRID)
        _text_center(draw, (fx, y_nums, fx + layout.cell_w, y_nums + layout.cell_h), f"{n:02d}", font_header, "#c62828")
    for n in BACK_RANGE:
        bx2 = layout.back_x(x0, n)
        draw.rectangle([bx2, y_nums, bx2 + layout.cell_w, y_nums + layout.cell_h], fill="#f0f7ff", outline=COLOR_GRID)
        _text_center(draw, (bx2, y_nums, bx2 + layout.cell_w, y_nums + layout.cell_h), f"{n:02d}", font_header, "#1565c0")

    _draw_vertical_separators(draw, layout, x0, y0, header_h)
    ball_r = layout.ball_r

    for ri, row in enumerate(rows):
        y = y0 + header_h + ri * layout.cell_h
        row_bg = "#fdf8f8" if ri % 2 else "#ffffff"
        meta_bg = "#f5f0f0" if ri % 2 else "#fafafa"

        draw.rectangle([x0, y, x0 + layout.issue_w, y + layout.cell_h], fill=meta_bg, outline=COLOR_GRID)
        _text_center(draw, (x0, y, x0 + layout.issue_w, y + layout.cell_h), row["issue"], font_issue, "#333333")
        draw.rectangle(
            [x0 + layout.issue_w, y, x0 + layout.issue_w + layout.tail_w, y + layout.cell_h],
            fill=meta_bg,
            outline=COLOR_GRID,
        )
        _text_center(
            draw,
            (x0 + layout.issue_w, y, x0 + layout.issue_w + layout.tail_w, y + layout.cell_h),
            str(row["sum_tail"]),
            font_omit,
            "#888888",
        )

        for n in FRONT_RANGE:
            fx = layout.front_x(x0, n)
            cell = row["front"][n]
            draw.rectangle([fx, y, fx + layout.cell_w, y + layout.cell_h], fill=row_bg, outline=COLOR_GRID)
            cx, cy = fx + layout.cell_w / 2, y + layout.cell_h / 2
            if cell[0] == "hit":
                draw.ellipse([cx - ball_r, cy - ball_r, cx + ball_r, cy + ball_r], fill=COLOR_FRONT_HIT)
                _text_center(draw, (fx, y, fx + layout.cell_w, y + layout.cell_h), f"{cell[1]:02d}", font_ball, "#ffffff")
            else:
                _text_center(draw, (fx, y, fx + layout.cell_w, y + layout.cell_h), str(cell[1]), font_omit, COLOR_OMIT)

        for n in BACK_RANGE:
            bx2 = layout.back_x(x0, n)
            cell = row["back"][n]
            draw.rectangle([bx2, y, bx2 + layout.cell_w, y + layout.cell_h], fill=row_bg, outline=COLOR_GRID)
            cx, cy = bx2 + layout.cell_w / 2, y + layout.cell_h / 2
            if cell[0] == "hit":
                draw.ellipse([cx - ball_r, cy - ball_r, cx + ball_r, cy + ball_r], fill=COLOR_BACK_HIT)
                _text_center(draw, (bx2, y, bx2 + layout.cell_w, y + layout.cell_h), f"{cell[1]:02d}", font_ball, "#ffffff")
            else:
                _text_center(draw, (bx2, y, bx2 + layout.cell_w, y + layout.cell_h), str(cell[1]), font_omit, COLOR_OMIT)

        _draw_vertical_separators(draw, layout, x0, y, layout.cell_h)

    # 绿色空区横条（每期最宽空号段）
    box_w = max(2, layout.px(2))
    for ri, period in enumerate(analysis["per_period_runs"]):
        widest = period["widest"]
        if not widest:
            continue
        y = y0 + header_h + ri * layout.cell_h
        sx = layout.front_x(x0, widest["start"])
        ex = layout.front_x(x0, widest["end"]) + layout.cell_w
        pad = max(1, layout.px(1))
        draw.rectangle([sx + pad, y + pad, ex - pad, y + layout.cell_h - pad], outline=COLOR_EMPTY_BOX, width=box_w)

    # 预测行：高亮预测空区(橙) + 活跃区(浅绿底)
    pred_y = y0 + header_h + len(rows) * layout.cell_h
    draw.rectangle([x0, pred_y, x0 + layout.issue_w, pred_y + layout.cell_h], fill="#fff7e6", outline=COLOR_GRID)
    _text_center(draw, (x0, pred_y, x0 + layout.issue_w, pred_y + layout.cell_h), "预测", font_issue, "#b9770e")
    draw.rectangle(
        [x0 + layout.issue_w, pred_y, x0 + layout.issue_w + layout.tail_w, pred_y + layout.cell_h],
        fill="#fff7e6",
        outline=COLOR_GRID,
    )
    excl = analysis["prediction"]["excluded_range"]
    for n in FRONT_RANGE:
        fx = layout.front_x(x0, n)
        in_excluded = excl[0] <= n <= excl[1]
        bg = "#fde3c0" if in_excluded else "#eafaf0"
        draw.rectangle([fx, pred_y, fx + layout.cell_w, pred_y + layout.cell_h], fill=bg, outline=COLOR_GRID)
    sx = layout.front_x(x0, excl[0])
    ex = layout.front_x(x0, excl[1]) + layout.cell_w
    draw.rectangle([sx + 1, pred_y + 1, ex - 1, pred_y + layout.cell_h - 1], outline=COLOR_PRED_BOX, width=box_w)
    for n in BACK_RANGE:
        bx2 = layout.back_x(x0, n)
        draw.rectangle([bx2, pred_y, bx2 + layout.cell_w, pred_y + layout.cell_h], fill="#fafafa", outline=COLOR_GRID)
    _draw_vertical_separators(draw, layout, x0, pred_y, layout.cell_h)

    draw.rectangle([x0, y0, x0 + table_w, y0 + table_h], outline="#cccccc", width=layout.border_w)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", compress_level=3)


def format_report(analysis: dict[str, Any], target_issue: str) -> str:
    pred = analysis["prediction"]
    lines = [
        f"大乐透空区分析 · 基准期 {target_issue} · 近 {analysis['periods']} 期",
        f"期号范围 {analysis['range'][0]}—{analysis['range'][1]} · 空区阈值 连续≥{analysis['min_run']} 号未开",
        "",
        "■ 三分区空区周期",
    ]
    for z in analysis["zones"]:
        gap = f"平均每{z['mean_gap']}期空1次" if z["mean_gap"] else "窗口内规律不足"
        dr = f"{z['due_ratio']}" if z["due_ratio"] is not None else "—"
        lines.append(
            f"  {z['zone']}：空 {z['empty_count']}/{analysis['periods']} 期 "
            f"({z['empty_rate'] * 100:.0f}%) · {gap} · 距上次空 {z['since_last_empty']} 期 · due={dr}"
        )

    er = pred.get("empty_rate_ref")
    lines.extend(
        [
            "",
            "■ 下期空区预测（结构性偏冷区 · 已弃用失效的 due 回归法）",
            f"  首选空区：{pred['predicted_empty_zone']} "
            f"（窗口空区率 {er * 100:.0f}%）  →  弱排除 {pred['excluded_range'][0]:02d}-{pred['excluded_range'][1]:02d}",
            f"  两个最冷候选区：{' / '.join(pred['two_coldest_zones'])}（覆盖更宽，回测命中≈26%）",
            f"  最热活跃区（重点选号）：{pred['hottest_zone']}",
            "",
            "■ 应用建议",
            "  · 前区 5 码重点落在最热活跃区 + 次热区；",
            f"  · 对最冷的 {pred['predicted_empty_zone']} 区降低权重（但勿全清，单区严格全空仅 ~10-16%）。",
            "",
            "[实测提醒] 800 期回测：严格三等分区空区是 ~10-16%/区 的弱事件，",
            "动态预测难显著超随机基线；本模块主要价值是「描述空区分布 + 结构性偏冷提示」，",
            "而非高确定性排除。彩票随机，仅供娱乐参考。",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="大乐透空区分析（默认近 30 期）")
    parser.add_argument("-i", "--issue", help="基准期号（默认最新一期）")
    parser.add_argument("-n", "--count", type=int, default=DEFAULT_ZONE_COUNT, help="窗口期数（默认 30）")
    parser.add_argument("-d", "--data", type=Path, help="JSON 数据路径")
    parser.add_argument("-o", "--output", type=Path, help="PNG 输出路径")
    parser.add_argument("-s", "--scale", type=float, default=DEFAULT_PNG_SCALE, help="PNG 倍率")
    parser.add_argument("--min-run", type=int, default=6, help="空区最小连续空号数（默认 6）")
    parser.add_argument("--no-chart", action="store_true", help="仅文字/JSON，不生成 PNG")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON")
    parser.add_argument("--backtest", action="store_true", help="回测空区预测命中率")
    parser.add_argument("-t", "--test-issues", type=int, default=500, help="回测期数（默认 500）")
    args = parser.parse_args()

    data_path = resolve_data_path(args.data)
    if not data_path.is_file():
        print(f"错误: 数据文件不存在 {data_path}", file=sys.stderr)
        return 1

    records = load_records(data_path)

    if args.backtest:
        bt = run_empty_zone_backtest(
            records, window=args.count, test_issues=args.test_issues, min_run=args.min_run
        )
        if args.json:
            print(json.dumps(bt, ensure_ascii=False, indent=2))
        else:
            r = bt["results"]
            print("大乐透空区预测回测")
            print(f"窗口 {bt['params']['window']} 期 · 回测 {bt['sample']['test_count']} 期 · "
                  f"{bt['sample']['issue_range'][0]}—{bt['sample']['issue_range'][1]}")
            print()
            print(f"  首选预测命中率: {r['predict_hit_rate'] * 100:.1f}%")
            print(f"  押2最冷区命中率: {r['two_coldest_hit_rate'] * 100:.1f}%")
            print(f"  正确随机基线(边际均值): {r['baseline_marginal_mean'] * 100:.1f}%")
            print(f"  最优固定押基线: {r['baseline_best_fixed'] * 100:.1f}%")
            print(f"  实际确有空区频率: {r['actual_has_empty_rate'] * 100:.1f}%")
            print(f"  实际 ≥2 区同时空: {r['multi_empty_rate'] * 100:.1f}%")
            print()
            print("  各分区边际空区频率:")
            for name, rate in r["zone_marginal_empty_rate"].items():
                print(f"    {name}: {rate * 100:.1f}%")
            print()
            print(f"  [结论] {bt['verdict']}")
            print()
            print(json.dumps(bt, ensure_ascii=False, indent=2))
        return 0

    window, target_issue = pick_window(records, args.issue, args.count)
    rows = build_chart_rows(records, window)
    analysis = analyze_empty_zones(window, min_run=args.min_run)
    analysis["target_issue"] = target_issue

    output_path: Path | None = None
    if not args.no_chart:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = args.output or DEFAULT_OUTPUT_DIR / f"empty-zone-{target_issue}-n{len(rows)}.png"
        render_empty_zone_png(rows, analysis, target_issue, args.count, data_path, output_path, scale=args.scale)

    result = {
        "ok": True,
        "target_issue": target_issue,
        "periods": len(rows),
        "range": analysis["range"],
        "analysis": analysis,
        "output": str(output_path.resolve()) if output_path else None,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(analysis, target_issue))
        print()
        if output_path:
            print(f"空区分析图: {output_path.resolve()}")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
