#!/usr/bin/env python3
"""大乐透局部趋势图 — 默认最近 15 期，识别斜向/纵向/汇聚趋势并标注 PNG."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from dlt_data import (
    BACK_RANGE,
    FRONT_RANGE,
    analyze_local_trends,
    apply_deviation_band,
    build_chart_rows,
    build_final_recommendation,
    load_deviation_profile,
    load_records,
    pick_window,
    resolve_data_path,
)
from trend_chart import (
    COLOR_BACK_HIT,
    COLOR_FRONT_HIT,
    COLOR_GRID,
    COLOR_GRID_GROUP,
    COLOR_GRID_STRONG,
    COLOR_OMIT,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PNG_SCALE,
    FRONT_GROUPS,
    ChartLayout,
    _draw_vertical_separators,
    _text_center,
    load_font,
)

DEFAULT_LOCAL_COUNT = 15
COLOR_TREND = "#2ecc71"
COLOR_TREND_EXT = "#27ae60"
COLOR_TREND_HUB = "#f39c12"


def _cell_center(
    layout: ChartLayout, x0: int, y0: int, header_h: int, row_idx: int, num: int, zone: str
) -> tuple[float, float]:
    y = y0 + header_h + row_idx * layout.cell_h + layout.cell_h / 2
    if zone == "front":
        x = layout.front_x(x0, num) + layout.cell_w / 2
    else:
        x = layout.back_x(x0, num) + layout.cell_w / 2
    return x, y


def _draw_arrow(
    draw: ImageDraw.ImageDraw,
    p1: tuple[float, float],
    p2: tuple[float, float],
    color: str,
    width: int,
    dashed: bool = False,
) -> None:
    if dashed:
        # 简单虚线：分段绘制
        import math

        x1, y1 = p1
        x2, y2 = p2
        dist = math.hypot(x2 - x1, y2 - y1)
        if dist < 1:
            return
        dash, gap = 6, 4
        n = int(dist / (dash + gap))
        for i in range(n + 1):
            t0 = i * (dash + gap) / dist
            t1 = min(1.0, (i * (dash + gap) + dash) / dist)
            if t0 >= 1:
                break
            draw.line(
                [(x1 + (x2 - x1) * t0, y1 + (y2 - y1) * t0), (x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1)],
                fill=color,
                width=width,
            )
    else:
        draw.line([p1, p2], fill=color, width=width)
    # 箭头三角（简化）
    import math

    x1, y1 = p1
    x2, y2 = p2
    angle = math.atan2(y2 - y1, x2 - x1)
    al = 8
    aa = 0.45
    p_a = (x2 - al * math.cos(angle - aa), y2 - al * math.sin(angle - aa))
    p_b = (x2 - al * math.cos(angle + aa), y2 - al * math.sin(angle + aa))
    draw.polygon([p2, p_a, p_b], fill=color)


def render_local_trend_png(
    rows: list[dict[str, Any]],
    window: list[dict[str, Any]],
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
    title = f"大乐透局部趋势图 {first_issue}—{last_issue}（近{len(rows)}期）"
    subtitle = (
        f"基准期 {target_issue} · 局部窗口 {count} 期 · 绿线=趋势线 · 虚线=延长落点 · {data_path.name}"
    )

    font_title = layout.font_title()
    font_sub = layout.font_sub()
    font_header = layout.font_header()
    font_issue = layout.font_issue()
    font_ball = layout.font_ball()
    font_omit = layout.font_omit()

    header_h = layout.cell_h * 2
    extra_row = layout.cell_h  # 虚拟预测行
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

    # 表头（同 trend_chart）
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

    # 数据行
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

    # 虚拟预测行
    pred_y = y0 + header_h + len(rows) * layout.cell_h
    draw.rectangle([x0, pred_y, x0 + layout.issue_w, pred_y + layout.cell_h], fill="#eef9ee", outline=COLOR_GRID)
    _text_center(draw, (x0, pred_y, x0 + layout.issue_w, pred_y + layout.cell_h), "预测", font_issue, "#2e7d32")
    draw.rectangle(
        [x0 + layout.issue_w, pred_y, x0 + layout.issue_w + layout.tail_w, pred_y + layout.cell_h],
        fill="#eef9ee",
        outline=COLOR_GRID,
    )
    for n in FRONT_RANGE:
        fx = layout.front_x(x0, n)
        draw.rectangle([fx, pred_y, fx + layout.cell_w, pred_y + layout.cell_h], fill="#f6fff6", outline=COLOR_GRID)
    for n in BACK_RANGE:
        bx2 = layout.back_x(x0, n)
        draw.rectangle([bx2, pred_y, bx2 + layout.cell_w, pred_y + layout.cell_h], fill="#f6fff6", outline=COLOR_GRID)
    _draw_vertical_separators(draw, layout, x0, pred_y, layout.cell_h)

    line_w = max(2, layout.px(2))

    # 绘制趋势线
    for zone_key, zone_label in (("front", "front"), ("back", "back")):
        for chain in analysis[zone_key]["chains"]:
            pts = chain["points"]
            centers = [_cell_center(layout, x0, y0, header_h, r, n, zone_label) for r, n in pts]
            for i in range(len(centers) - 1):
                _draw_arrow(draw, centers[i], centers[i + 1], COLOR_TREND, line_w)
            # 延长虚线到预测行
            last_r, last_n = pts[-1]
            pred_n = chain["predict_num"]
            p_from = _cell_center(layout, x0, y0, header_h, last_r, last_n, zone_label)
            p_to = _cell_center(layout, x0, y0, header_h, len(rows), pred_n, zone_label)
            _draw_arrow(draw, p_from, p_to, COLOR_TREND_EXT, line_w, dashed=True)
            # 预测落点标记
            px, py = p_to
            hub = any(h["num"] == pred_n for h in analysis[zone_key]["convergence_hubs"])
            color = COLOR_TREND_HUB if hub else COLOR_TREND_EXT
            pr = layout.px(7)
            draw.ellipse([px - pr, py - pr, px + pr, py + pr], outline=color, width=line_w)

    draw.rectangle([x0, y0, x0 + table_w, y0 + table_h], outline="#cccccc", width=layout.border_w)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", compress_level=3)


def format_report(
    analysis: dict[str, Any],
    target_issue: str,
    adjusted: dict[str, Any] | None = None,
    final: dict[str, Any] | None = None,
) -> str:
    lines = [
        f"大乐透局部趋势分析 · 基准期 {target_issue} · 近 {analysis['periods']} 期",
        f"期号范围 {analysis['range'][0]}—{analysis['range'][1]}",
        "",
        "■ 前区趋势线（≥3 期连线）",
    ]
    if analysis["front"]["chains"]:
        for i, c in enumerate(analysis["front"]["chains"][:6], 1):
            dir_map = {
                "diagonal_down_right": "↘ 右下斜",
                "diagonal_down_left": "↙ 左下斜",
                "vertical": "↓ 纵向",
                "flat": "→ 平移",
            }
            d = dir_map.get(c["type"], c["type"])
            nums = "→".join(f"{n:02d}" for n in c["path_nums"])
            lines.append(
                f"  线{i}：{d} · {c['start_issue']}—{c['end_issue']} · {nums} · "
                f"步长≈{c['avg_step']:+.1f} · 延长落点 ≈ {c['predict_num']:02d}"
            )
    else:
        lines.append("  （未识别显著趋势线）")

    lines.append("")
    lines.append("■ 前区纵向热柱（同号反复）")
    if analysis["front"]["vertical_repeats"]:
        for v in analysis["front"]["vertical_repeats"][:4]:
            lines.append(f"  {v['num']:02d} · 出现 {v['count']} 次")
    else:
        lines.append("  （无）")

    lines.append("")
    lines.append("■ 前区汇聚枢纽（多线指向同一落点）")
    if analysis["front"]["convergence_hubs"]:
        for h in analysis["front"]["convergence_hubs"]:
            lines.append(f"  {h['num']:02d} · {h['convergence']} 条线汇聚")
    else:
        lines.append("  （无显著汇聚）")

    lines.append("")
    lines.append("■ 前区下一期候选（链落点加权）")
    for c in analysis["front"]["next_candidates"][:6]:
        lines.append(f"  {c['num']:02d} · 得分 {c['score']}")

    lines.append("")
    lines.append("■ 后区趋势线")
    if analysis["back"]["chains"]:
        for i, c in enumerate(analysis["back"]["chains"][:4], 1):
            nums = "→".join(f"{n:02d}" for n in c["path_nums"])
            lines.append(
                f"  线{i}：{c['start_issue']}—{c['end_issue']} · {nums} · 落点 ≈ {c['predict_num']:02d}"
            )
    else:
        lines.append("  （未识别显著趋势线）")

    lines.append("")
    lines.append("■ 后区下一期候选")
    for c in analysis["back"]["next_candidates"][:4]:
        lines.append(f"  {c['num']:02d} · 得分 {c['score']}")

    if adjusted:
        fb = adjusted["recommended_band"]["front"]
        bb = adjusted["recommended_band"]["back"]
        fe = adjusted["exact_hit_rate_ref"]["front"]
        lines.extend(
            [
                "",
                "■ 偏差带扩展（程序四 · 勿只押纯落点）",
                f"  档案纯落点精确率参考: 前区 {fe * 100:.1f}%  →  推荐带 前±{fb} / 后±{bb}",
                "  前区扩展候选: "
                + " ".join(f"{x['num']:02d}" for x in adjusted["front_adjusted"][:10]),
                "  后区扩展候选: "
                + " ".join(f"{x['num']:02d}" for x in adjusted["back_adjusted"][:5]),
            ]
        )
    else:
        lines.extend(
            [
                "",
                "■ 偏差带扩展",
                "  （未找到 deviation_profile.json，请先运行 deviation_backtest.py）",
            ]
        )

    if final:
        st = final["structure"]
        sg = final["signals"]
        zd = " / ".join(f"{k}:{v}" for k, v in st["zone_dist"].items())
        lines.extend(
            [
                "",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"★ 本期推荐定号 {final['front_count']}+{final['back_count']}（综合趋势+偏差带+空区权重）",
                "  前区 7 码: " + "  ".join(f"{n:02d}" for n in final["front"]),
                "  后区 3 码: " + "  ".join(f"{n:02d}" for n in final["back"]),
                f"  结构: 分区 {zd} · 奇偶 {st['odd_even']} · 大小 {st['size_small_large']} · 和值 {st['sum']}",
                f"  信号: 热区 {sg['hot_zone']} / 冷区 {sg['cold_zone']} / 前区趋势线 {sg['trend_chains_front']} 条",
                "  重号保护(上期号入选): 前 "
                + (" ".join(f"{n:02d}" for n in sg["repeat_protected"]["front"]) or "无")
                + " / 后 "
                + (" ".join(f"{n:02d}" for n in sg["repeat_protected"]["back"]) or "无"),
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ]
        )

    lines.append("")
    lines.append("[声明] 局部趋势基于近窗连线外推，彩票随机，仅供娱乐参考。")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="大乐透局部趋势图（默认近 15 期）")
    parser.add_argument("-i", "--issue", help="基准期号（默认最新一期）")
    parser.add_argument("-n", "--count", type=int, default=DEFAULT_LOCAL_COUNT, help="局部窗口期数（默认 15）")
    parser.add_argument("-d", "--data", type=Path, help="JSON 数据路径")
    parser.add_argument("-o", "--output", type=Path, help="PNG 输出路径")
    parser.add_argument("-s", "--scale", type=float, default=DEFAULT_PNG_SCALE, help="PNG 倍率")
    parser.add_argument("--no-chart", action="store_true", help="仅输出文字/JSON 分析，不生成 PNG")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON")
    args = parser.parse_args()

    if args.count < 3:
        print("错误: 局部趋势至少需要 3 期", file=sys.stderr)
        return 1

    data_path = resolve_data_path(args.data)
    if not data_path.is_file():
        print(f"错误: 数据文件不存在 {data_path}", file=sys.stderr)
        return 1

    records = load_records(data_path)
    window, target_issue = pick_window(records, args.issue, args.count)
    rows = build_chart_rows(records, window)
    analysis = analyze_local_trends(window)
    analysis["target_issue"] = target_issue
    profile = load_deviation_profile()
    adjusted = apply_deviation_band(analysis, profile) if profile else None
    final = build_final_recommendation(window, profile=profile, records=records)

    output_path: Path | None = None
    if not args.no_chart:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = args.output or DEFAULT_OUTPUT_DIR / f"local-trend-{target_issue}-n{len(rows)}.png"
        render_local_trend_png(
            rows, window, analysis, target_issue, args.count, data_path, output_path, scale=args.scale
        )

    result = {
        "ok": True,
        "target_issue": target_issue,
        "periods": len(rows),
        "range": analysis["range"],
        "analysis": analysis,
        "deviation_adjusted": adjusted,
        "final_recommendation": final,
        "output": str(output_path.resolve()) if output_path else None,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(analysis, target_issue, adjusted, final))
        print()
        if output_path:
            print(f"局部趋势图: {output_path.resolve()}")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
