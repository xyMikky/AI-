#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体渲染脚本 — 将指定字体文件 + 文字内容渲染为高清 PNG 图片。

用途：
    生成的文字图片作为 image N 传入 rh-image-pro-img2img，
    让 AI 生图模型参考精确字体样式，而非自行猜测。

用法：
    python render_font_text.py \
        --font "参考库/C_排版字体/字体文件/Futura-Bold.otf" \
        --text "Tummy Control Shapewear" \
        --size 120 \
        --color "#1A1A1A" \
        --bg "transparent" \
        --letter-spacing 5 \
        --align "left" \
        --max-width 1200 \
        --output "生成结果输出/font_renders/text_01.png"

输出：JSON 格式，包含 saved_path / width / height / error
"""

import argparse
import json
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR   = Path(__file__).resolve().parent          # .cursor/skills/.../scripts/
SKILL_DIR    = SCRIPT_DIR.parent                        # .cursor/skills/.../
CURSOR_DIR   = SKILL_DIR.parent.parent                  # .cursor/
PROJECT_ROOT = CURSOR_DIR.parent                        # 项目根目录

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "生成结果输出" / "font_renders"


def hex_to_rgba(hex_color: str) -> tuple:
    """#RRGGBB or #RRGGBBAA -> (R, G, B, A)"""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    elif len(h) == 8:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4, 6))
    raise ValueError(f"Invalid hex color: {hex_color}")


def measure_text_with_spacing(draw, text, font, letter_spacing):
    """Measure total width of text with custom letter-spacing."""
    if letter_spacing == 0:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    total_w = 0
    max_h = 0
    for i, ch in enumerate(text):
        bbox = draw.textbbox((0, 0), ch, font=font)
        ch_w = bbox[2] - bbox[0]
        ch_h = bbox[3] - bbox[1]
        total_w += ch_w
        if i < len(text) - 1:
            total_w += letter_spacing
        max_h = max(max_h, ch_h)
    return total_w, max_h


def wrap_text(draw, text, font, letter_spacing, max_width):
    """Split text into lines that fit within max_width."""
    if max_width <= 0:
        return [text]

    lines = []
    for raw_line in text.split("\n"):
        words = raw_line.split(" ")
        current_line = ""
        for word in words:
            test = (current_line + " " + word).strip()
            w, _ = measure_text_with_spacing(draw, test, font, letter_spacing)
            if w <= max_width or not current_line:
                current_line = test
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
    return lines if lines else [""]


def draw_text_with_spacing(draw, x, y, text, font, fill, letter_spacing):
    """Draw text character by character with custom letter-spacing."""
    if letter_spacing == 0:
        draw.text((x, y), text, font=font, fill=fill)
        return

    cursor_x = x
    for ch in text:
        draw.text((cursor_x, y), ch, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), ch, font=font)
        cursor_x += (bbox[2] - bbox[0]) + letter_spacing


def render(font_path, text, size, color, bg, letter_spacing, align, max_width, output_path):
    font_path = Path(font_path)
    if not font_path.is_absolute():
        font_path = PROJECT_ROOT / font_path

    if not font_path.exists():
        return {"success": False, "error": f"字体文件不存在: {font_path}"}

    try:
        font = ImageFont.truetype(str(font_path), size)
    except Exception as e:
        return {"success": False, "error": f"无法加载字体: {e}"}

    fg_color = hex_to_rgba(color)

    if bg.lower() == "transparent":
        bg_color = (0, 0, 0, 0)
    else:
        bg_color = hex_to_rgba(bg)

    dummy = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy)

    if max_width > 0:
        lines = wrap_text(dummy_draw, text, font, letter_spacing, max_width)
    else:
        lines = text.split("\n") if "\n" in text else [text]

    line_metrics = []
    total_height = 0
    max_line_width = 0
    line_gap = int(size * 0.35)

    for line in lines:
        w, h = measure_text_with_spacing(dummy_draw, line, font, letter_spacing)
        ascent, descent = font.getmetrics()
        line_h = ascent + descent
        line_metrics.append((w, line_h))
        max_line_width = max(max_line_width, w)
        total_height += line_h

    total_height += line_gap * (len(lines) - 1) if len(lines) > 1 else 0

    padding_x = int(size * 0.4)
    padding_y = int(size * 0.4)
    canvas_w = max_line_width + padding_x * 2
    canvas_h = total_height + padding_y * 2

    img = Image.new("RGBA", (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(img)

    y_cursor = padding_y
    for i, line in enumerate(lines):
        lw, lh = line_metrics[i]

        if align == "center":
            x = (canvas_w - lw) // 2
        elif align == "right":
            x = canvas_w - padding_x - lw
        else:
            x = padding_x

        draw_text_with_spacing(draw, x, y_cursor, line, font, fg_color, letter_spacing)
        y_cursor += lh + (line_gap if i < len(lines) - 1 else 0)

    output_path = Path(output_path)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img.save(str(output_path), "PNG")

    return {
        "success": True,
        "saved_path": str(output_path),
        "width": canvas_w,
        "height": canvas_h,
        "lines": len(lines),
    }


def main():
    parser = argparse.ArgumentParser(description="字体渲染脚本 — 将字体文件+文字渲染为 PNG 图片")

    parser.add_argument("--font", required=True,
                        help="字体文件路径 (.ttf/.otf)，支持绝对路径或相对于项目根的路径")
    parser.add_argument("--text", required=True,
                        help="要渲染的文字内容（支持 \\n 换行）")
    parser.add_argument("--size", type=int, default=120,
                        help="字号大小（像素），默认 120")
    parser.add_argument("--color", default="#1A1A1A",
                        help="文字颜色，HEX 格式，默认 #1A1A1A")
    parser.add_argument("--bg", default="transparent",
                        help="背景色，'transparent' 或 HEX 格式，默认 transparent")
    parser.add_argument("--letter-spacing", type=int, default=0,
                        help="字间距（像素），默认 0")
    parser.add_argument("--align", choices=["left", "center", "right"], default="left",
                        help="对齐方式，默认 left")
    parser.add_argument("--max-width", type=int, default=0,
                        help="最大宽度（像素），超出自动换行，0=不限")
    parser.add_argument("--output", default="",
                        help="输出路径，默认自动生成")

    args = parser.parse_args()

    text = args.text.replace("\\n", "\n")

    if not args.output:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in text[:20])
        args.output = str(DEFAULT_OUTPUT_DIR / f"font_{ts}_{safe_name}.png")

    result = render(
        font_path=args.font,
        text=text,
        size=args.size,
        color=args.color,
        bg=args.bg,
        letter_spacing=args.letter_spacing,
        align=args.align,
        max_width=args.max_width,
        output_path=args.output,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
