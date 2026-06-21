#!/usr/bin/env python3
"""大乐透基本走势图生成器 — 指定期号往前 N 期."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from dlt_data import (
    BACK_RANGE,
    FRONT_GROUPS,
    FRONT_RANGE,
    build_chart_rows,
    data_summary,
    load_records,
    pick_window,
    resolve_data_path,
)

DEFAULT_OUTPUT_DIR = Path.home() / "Desktop" / "lotto-charts"
DEFAULT_PNG_SCALE = 2.0

COLOR_FRONT_HIT = "#e53935"
COLOR_BACK_HIT = "#1e88e5"
COLOR_OMIT = "#bbbbbb"
COLOR_GRID = "#d8d8d8"
COLOR_GRID_STRONG = "#888888"
COLOR_GRID_GROUP = "#bbbbbb"


@dataclass(frozen=True)
class ChartLayout:
    """按 scale 缩放全部绘图尺寸，默认 2x 提升 PNG 清晰度."""

    scale: float = DEFAULT_PNG_SCALE

    def __post_init__(self) -> None:
        if self.scale < 0.5 or self.scale > 6:
            raise ValueError("scale 须在 0.5–6 之间")

    def px(self, base: float) -> int:
        return max(1, round(base * self.scale))

    @property
    def issue_w(self) -> int:
        return self.px(56)

    @property
    def tail_w(self) -> int:
        return self.px(28)

    @property
    def cell_w(self) -> int:
        return self.px(24)

    @property
    def cell_h(self) -> int:
        return self.px(22)

    @property
    def margin(self) -> int:
        return self.px(16)

    @property
    def title_h(self) -> int:
        return self.px(32)

    @property
    def subtitle_h(self) -> int:
        return self.px(20)

    @property
    def ball_r(self) -> int:
        return self.px(9)

    @property
    def sep_strong(self) -> int:
        return max(1, self.px(3))

    @property
    def sep_group(self) -> int:
        return max(1, self.px(2))

    @property
    def border_w(self) -> int:
        return max(1, self.px(1))

    @property
    def bottom_pad(self) -> int:
        return self.px(8)

    def font_title(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return load_font(self.px(14))

    def font_sub(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return load_font(self.px(10))

    def font_header(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return load_font(self.px(9))

    def font_issue(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return load_font(self.px(10))

    def font_ball(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return load_font(self.px(8))

    def font_omit(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return load_font(self.px(8))

    def table_width(self) -> int:
        return self.issue_w + self.tail_w + len(FRONT_RANGE) * self.cell_w + len(BACK_RANGE) * self.cell_w

    def front_x(self, x0: int, num: int) -> int:
        return x0 + self.issue_w + self.tail_w + (num - 1) * self.cell_w

    def back_x(self, x0: int, num: int) -> int:
        return x0 + self.issue_w + self.tail_w + len(FRONT_RANGE) * self.cell_w + (num - 1) * self.cell_w


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc"):
        path = Path("C:/Windows/Fonts") / name
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _text_center(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
) -> None:
    x0, y0, x1, y1 = box
    try:
        draw.text(((x0 + x1) / 2, (y0 + y1) / 2), text, fill=fill, font=font, anchor="mm")
    except TypeError:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - th) / 2), text, fill=fill, font=font)


def _draw_vertical_separators(
    draw: ImageDraw.ImageDraw,
    layout: ChartLayout,
    x0: int,
    y0: int,
    height: int,
) -> None:
    xs = [
        (x0 + layout.issue_w + layout.tail_w, COLOR_GRID_STRONG, layout.sep_strong),
        (x0 + layout.issue_w + layout.tail_w + 12 * layout.cell_w, COLOR_GRID_GROUP, layout.sep_group),
        (x0 + layout.issue_w + layout.tail_w + 24 * layout.cell_w, COLOR_GRID_GROUP, layout.sep_group),
        (layout.back_x(x0, 1), COLOR_GRID_STRONG, layout.sep_strong),
    ]
    for x, color, w in xs:
        draw.line([(x, y0), (x, y0 + height)], fill=color, width=w)


def render_png(
    rows: list[dict[str, Any]],
    target_issue: str,
    count: int,
    data_path: Path,
    out_path: Path,
    scale: float = DEFAULT_PNG_SCALE,
) -> None:
    layout = ChartLayout(scale=scale)
    first_issue = rows[0]["issue"]
    last_issue = rows[-1]["issue"]
    title = f"大乐透基本走势图 {first_issue}—{last_issue}（共{len(rows)}期）"
    subtitle = (
        f"基准期 {target_issue} · 往前 {count} 期 · 数据源 {data_path.name} · {scale}x"
    )

    font_title = layout.font_title()
    font_sub = layout.font_sub()
    font_header = layout.font_header()
    font_issue = layout.font_issue()
    font_ball = layout.font_ball()
    font_omit = layout.font_omit()

    header_h = layout.cell_h * 2
    table_w = layout.table_width()
    table_h = header_h + len(rows) * layout.cell_h
    margin = layout.margin
    img_w = margin * 2 + table_w
    img_h = margin * 2 + layout.title_h + layout.subtitle_h + table_h + layout.bottom_pad

    img = Image.new("RGB", (img_w, img_h), "#f5f5f5")
    draw = ImageDraw.Draw(img)

    _text_center(
        draw,
        (margin, margin, img_w - margin, margin + layout.title_h),
        title,
        font_title,
        "#333333",
    )
    _text_center(
        draw,
        (
            margin,
            margin + layout.title_h,
            img_w - margin,
            margin + layout.title_h + layout.subtitle_h,
        ),
        subtitle,
        font_sub,
        "#666666",
    )

    x0 = margin
    y0 = margin + layout.title_h + layout.subtitle_h

    # 表头：期号、和尾（跨两行）
    draw.rectangle(
        [x0, y0, x0 + layout.issue_w, y0 + header_h],
        fill="#fafafa",
        outline=COLOR_GRID,
    )
    _text_center(
        draw, (x0, y0, x0 + layout.issue_w, y0 + header_h), "期号", font_header, "#555555"
    )

    tx = x0 + layout.issue_w
    draw.rectangle(
        [tx, y0, tx + layout.tail_w, y0 + header_h],
        fill="#fafafa",
        outline=COLOR_GRID,
    )
    _text_center(
        draw, (tx, y0, tx + layout.tail_w, y0 + header_h), "和尾", font_header, "#555555"
    )

    # 分组表头（第一行）
    y_group = y0
    for g in FRONT_GROUPS:
        gx = layout.front_x(x0, g.start)
        gw = len(g) * layout.cell_w
        fill = "#fff5f5"
        draw.rectangle(
            [gx, y_group, gx + gw, y_group + layout.cell_h],
            fill=fill,
            outline=COLOR_GRID,
        )
        label = f"{g.start:02d}-{g.stop - 1:02d}"
        _text_center(
            draw,
            (gx, y_group, gx + gw, y_group + layout.cell_h),
            label,
            font_header,
            "#c62828",
        )

    bx = layout.back_x(x0, 1)
    bw = len(BACK_RANGE) * layout.cell_w
    draw.rectangle(
        [bx, y_group, bx + bw, y_group + layout.cell_h],
        fill="#f0f7ff",
        outline=COLOR_GRID,
    )
    _text_center(
        draw,
        (bx, y_group, bx + bw, y_group + layout.cell_h),
        "后区01-12",
        font_header,
        "#1565c0",
    )

    # 号码表头（第二行）
    y_nums = y0 + layout.cell_h
    for n in FRONT_RANGE:
        fx = layout.front_x(x0, n)
        draw.rectangle(
            [fx, y_nums, fx + layout.cell_w, y_nums + layout.cell_h],
            fill="#fff5f5",
            outline=COLOR_GRID,
        )
        _text_center(
            draw,
            (fx, y_nums, fx + layout.cell_w, y_nums + layout.cell_h),
            f"{n:02d}",
            font_header,
            "#c62828",
        )

    for n in BACK_RANGE:
        bx2 = layout.back_x(x0, n)
        draw.rectangle(
            [bx2, y_nums, bx2 + layout.cell_w, y_nums + layout.cell_h],
            fill="#f0f7ff",
            outline=COLOR_GRID,
        )
        _text_center(
            draw,
            (bx2, y_nums, bx2 + layout.cell_w, y_nums + layout.cell_h),
            f"{n:02d}",
            font_header,
            "#1565c0",
        )

    _draw_vertical_separators(draw, layout, x0, y0, header_h)

    ball_r = layout.ball_r

    # 数据行
    for ri, row in enumerate(rows):
        y = y0 + header_h + ri * layout.cell_h
        row_bg = "#fdf8f8" if ri % 2 else "#ffffff"
        meta_bg = "#f5f0f0" if ri % 2 else "#fafafa"

        draw.rectangle(
            [x0, y, x0 + layout.issue_w, y + layout.cell_h],
            fill=meta_bg,
            outline=COLOR_GRID,
        )
        _text_center(
            draw,
            (x0, y, x0 + layout.issue_w, y + layout.cell_h),
            row["issue"],
            font_issue,
            "#333333",
        )

        draw.rectangle(
            [
                x0 + layout.issue_w,
                y,
                x0 + layout.issue_w + layout.tail_w,
                y + layout.cell_h,
            ],
            fill=meta_bg,
            outline=COLOR_GRID,
        )
        _text_center(
            draw,
            (
                x0 + layout.issue_w,
                y,
                x0 + layout.issue_w + layout.tail_w,
                y + layout.cell_h,
            ),
            str(row["sum_tail"]),
            font_omit,
            "#888888",
        )

        for n in FRONT_RANGE:
            fx = layout.front_x(x0, n)
            cell = row["front"][n]
            draw.rectangle(
                [fx, y, fx + layout.cell_w, y + layout.cell_h],
                fill=row_bg,
                outline=COLOR_GRID,
            )
            cx, cy = fx + layout.cell_w / 2, y + layout.cell_h / 2
            if cell[0] == "hit":
                draw.ellipse(
                    [cx - ball_r, cy - ball_r, cx + ball_r, cy + ball_r],
                    fill=COLOR_FRONT_HIT,
                )
                _text_center(
                    draw,
                    (fx, y, fx + layout.cell_w, y + layout.cell_h),
                    f"{cell[1]:02d}",
                    font_ball,
                    "#ffffff",
                )
            else:
                _text_center(
                    draw,
                    (fx, y, fx + layout.cell_w, y + layout.cell_h),
                    str(cell[1]),
                    font_omit,
                    COLOR_OMIT,
                )

        for n in BACK_RANGE:
            bx2 = layout.back_x(x0, n)
            cell = row["back"][n]
            draw.rectangle(
                [bx2, y, bx2 + layout.cell_w, y + layout.cell_h],
                fill=row_bg,
                outline=COLOR_GRID,
            )
            cx, cy = bx2 + layout.cell_w / 2, y + layout.cell_h / 2
            if cell[0] == "hit":
                draw.ellipse(
                    [cx - ball_r, cy - ball_r, cx + ball_r, cy + ball_r],
                    fill=COLOR_BACK_HIT,
                )
                _text_center(
                    draw,
                    (bx2, y, bx2 + layout.cell_w, y + layout.cell_h),
                    f"{cell[1]:02d}",
                    font_ball,
                    "#ffffff",
                )
            else:
                _text_center(
                    draw,
                    (bx2, y, bx2 + layout.cell_w, y + layout.cell_h),
                    str(cell[1]),
                    font_omit,
                    COLOR_OMIT,
                )

        _draw_vertical_separators(draw, layout, x0, y, layout.cell_h)

    draw.rectangle(
        [x0, y0, x0 + table_w, y0 + table_h],
        outline="#cccccc",
        width=layout.border_w,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", compress_level=3)


def cell_html(
    cell: tuple[str, int], zone: str, extra_class: str = ""
) -> str:
    kind, value = cell
    cls = f"cell {extra_class}".strip()
    if kind == "hit":
        color = "#e53935" if zone == "front" else "#1e88e5"
        return (
            f'<td class="{cls} hit {zone}">'
            f'<span class="ball" style="background:{color}">{value:02d}</span></td>'
        )
    return f'<td class="{cls} miss"><span class="omit">{value}</span></td>'


def render_html(
    rows: list[dict[str, Any]],
    target_issue: str,
    count: int,
    data_path: Path,
) -> str:
    def header_nums(nums: range, cls: str, first_extra: str = "") -> str:
        parts = []
        for i, n in enumerate(nums):
            extra = first_extra if i == 0 else ""
            parts.append(f'<th class="num {cls} {extra}">{n:02d}</th>')
        return "".join(parts)

    group_headers = []
    for gi, g in enumerate(FRONT_GROUPS):
        sep = "sep-front" if gi == 0 else "sep-group"
        group_headers.append(
            f'<th colspan="{len(g)}" class="group-head front-group {sep}">'
            f'{g.start:02d}-{g.stop - 1:02d}</th>'
        )
    group_header_html = "".join(group_headers)

    front_header_parts = []
    for gi, g in enumerate(FRONT_GROUPS):
        sep = "sep-front" if gi == 0 else "sep-group"
        front_header_parts.append(header_nums(g, "front", sep))
    front_nums = "".join(front_header_parts)
    back_nums = header_nums(BACK_RANGE, "back", "sep-back")

    body_rows = []
    for i, row in enumerate(rows):
        alt = "alt" if i % 2 else ""
        front_parts = []
        for gi, g in enumerate(FRONT_GROUPS):
            sep = "sep-front" if gi == 0 else "sep-group"
            for i, n in enumerate(g):
                cell_sep = sep if i == 0 else ""
                front_parts.append(cell_html(row["front"][n], "front", cell_sep))
        front_tds = "".join(front_parts)
        back_tds = "".join(
            cell_html(row["back"][n], "back", "sep-back" if i == 0 else "")
            for i, n in enumerate(BACK_RANGE)
        )
        body_rows.append(
            f'<tr class="data-row {alt}">'
            f'<td class="issue">{row["issue"]}</td>'
            f'<td class="sum-tail">{row["sum_tail"]}</td>'
            f"{front_tds}{back_tds}</tr>"
        )

    first_issue = rows[0]["issue"]
    last_issue = rows[-1]["issue"]
    title = f"大乐透基本走势图 {first_issue}—{last_issue}（共{len(rows)}期）"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    margin: 16px;
    background: #f5f5f5;
    color: #333;
  }}
  h1 {{
    font-size: 18px;
    margin: 0 0 8px;
    text-align: center;
  }}
  .meta {{
    text-align: center;
    font-size: 12px;
    color: #666;
    margin-bottom: 12px;
  }}
  .wrap {{
    overflow-x: auto;
    background: #fff;
    border: 1px solid #ccc;
    padding: 4px;
  }}
  table {{
    border-collapse: collapse;
    font-size: 11px;
    margin: 0 auto;
  }}
  th, td {{
    border: 1px solid #d8d8d8;
    text-align: center;
    vertical-align: middle;
    padding: 0;
  }}
  th {{
    background: #fafafa;
    font-weight: normal;
    color: #555;
  }}
  .issue, .sum-tail {{
    width: 52px;
    min-width: 52px;
    font-size: 11px;
    background: #fafafa;
    font-weight: 600;
  }}
  .sum-tail {{ width: 28px; min-width: 28px; color: #888; }}
  .group-head {{
    font-size: 10px;
    background: #f0f0f0;
    border-bottom: 2px solid #bbb;
  }}
  .front-group {{ background: #fff5f5; }}
  .back-group {{ background: #f0f7ff; }}
  th.num.front {{ background: #fff5f5; color: #c62828; }}
  th.num.back {{ background: #f0f7ff; color: #1565c0; }}
  .sep-front {{ border-left: 3px solid #bbb !important; }}
  .sep-group {{ border-left: 2px solid #ccc !important; }}
  .sep-back {{ border-left: 3px solid #888 !important; }}
  .cell {{
    width: 22px;
    min-width: 22px;
    height: 22px;
    line-height: 22px;
  }}
  .data-row.alt td {{ background: #fdf8f8; }}
  .data-row.alt td.issue, .data-row.alt td.sum-tail {{ background: #f5f0f0; }}
  .ball {{
    display: inline-block;
    width: 20px;
    height: 20px;
    line-height: 20px;
    border-radius: 50%;
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    vertical-align: middle;
  }}
  .omit {{
    color: #bbb;
    font-size: 10px;
  }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">基准期 {target_issue} · 往前 {count} 期 · 数据源 {data_path.name}</p>
<div class="wrap">
<table>
  <thead>
    <tr>
      <th rowspan="2">期号</th>
      <th rowspan="2">和尾</th>
      {group_header_html}
      <th colspan="12" class="group-head back-group sep-back">后区 01-12</th>
    </tr>
    <tr>
      {front_nums}
      {back_nums}
    </tr>
  </thead>
  <tbody>
    {"".join(body_rows)}
  </tbody>
</table>
</div>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="生成大乐透基本走势图（PNG / HTML）")
    parser.add_argument(
        "-i", "--issue",
        help="基准期号（默认最新一期）",
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=50,
        help="往前期数（默认 50）",
    )
    parser.add_argument(
        "-d", "--data",
        type=Path,
        help="JSON 数据路径（默认 skill/assets/lotto_history.json）",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="仅输出数据文件摘要（期数、首尾期号）",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="输出文件路径（扩展名决定格式；未指定时按 --format 命名）",
    )
    parser.add_argument(
        "-f", "--format",
        choices=("png", "html", "both"),
        default="png",
        help="输出格式（默认 png）",
    )
    parser.add_argument(
        "-s", "--scale",
        type=float,
        default=DEFAULT_PNG_SCALE,
        help=f"PNG 清晰度倍率（默认 {DEFAULT_PNG_SCALE}，建议 2–3）",
    )
    args = parser.parse_args()

    if args.count < 1:
        print("错误: count 必须 >= 1", file=sys.stderr)
        return 1

    if args.scale < 0.5 or args.scale > 6:
        print("错误: scale 须在 0.5–6 之间", file=sys.stderr)
        return 1

    data_path = resolve_data_path(args.data)
    if not data_path.is_file():
        print(f"错误: 数据文件不存在 {data_path}", file=sys.stderr)
        return 1

    records = load_records(data_path)
    if args.info:
        summary = data_summary(records)
        print(
            json.dumps(
                {"ok": True, "data_path": str(data_path.resolve()), **summary},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    window, target_issue = pick_window(records, args.issue, args.count)
    rows = build_chart_rows(records, window)
    n = len(rows)
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base_name = f"trend-{target_issue}-n{n}"

    outputs: list[str] = []

    if args.output:
        out = args.output
        suffix = out.suffix.lower()
        if suffix == ".html":
            fmt = "html"
        elif suffix in (".png", ".jpg", ".jpeg"):
            fmt = "png"
        else:
            fmt = args.format if args.format != "both" else "png"
        targets = {fmt: out}
        if args.format == "both" and suffix not in (".html", ".png"):
            targets = {
                "png": DEFAULT_OUTPUT_DIR / f"{base_name}.png",
                "html": DEFAULT_OUTPUT_DIR / f"{base_name}.html",
            }
    else:
        if args.format == "both":
            targets = {
                "png": DEFAULT_OUTPUT_DIR / f"{base_name}.png",
                "html": DEFAULT_OUTPUT_DIR / f"{base_name}.html",
            }
        elif args.format == "html":
            targets = {"html": DEFAULT_OUTPUT_DIR / f"{base_name}.html"}
        else:
            targets = {"png": DEFAULT_OUTPUT_DIR / f"{base_name}.png"}

    for fmt, path in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "html":
            html = render_html(rows, target_issue, args.count, data_path)
            path.write_text(html, encoding="utf-8")
        else:
            png_path = path.with_suffix(".png")
            render_png(
                rows, target_issue, args.count, data_path, png_path, scale=args.scale
            )
            path = png_path
        outputs.append(str(path.resolve()))

    result = {
        "ok": True,
        "target_issue": target_issue,
        "periods": n,
        "range": [window[0]["issue"], window[-1]["issue"]],
        "format": args.format,
        "scale": args.scale if args.format in ("png", "both") else None,
        "data_path": str(data_path.resolve()),
        "outputs": outputs,
        "output": outputs[0],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
