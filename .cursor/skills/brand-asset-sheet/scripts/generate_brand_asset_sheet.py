#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brand Asset Sheet 入口脚本
将品牌 Logo、色卡、字体渲染文字合成为单张 PNG 参考图。

用法示例（从项目根目录运行，无需 --project-root）：
    python ".cursor/skills/brand-asset-sheet/scripts/generate_brand_asset_sheet.py" \
        --brand "NEBILITY" \
        --logo "品牌规范/NEBILITY/原始素材/NEBILITY-LG-005-Logo-512w-BlackText-RedShape-20260331.png" \
        --colors "#bf192e:Brand Red,#1a1a1a:Brand Black,#ffffff:White,#f5f5f5:Light Gray" \
        --texts-file "生成结果输出/brand_asset_sheets/NEBILITY-texts.json" \
        --output "生成结果输出/brand_asset_sheets/NEBILITY-promo-assets.png"

所有路径（--logo / --texts-file / --output / texts JSON 中的 font）均使用
相对于项目根目录的相对路径，脚本内部自动拼接为绝对路径。

项目根目录推算规则（优先级从高到低）：
  1. 命令行传入 --project-root（适用于 exec() 调用等特殊场景）
  2. 从 __file__ 向上推算5层：scripts/ → brand-asset-sheet/ → skills/ → .cursor/ → 项目根
  3. 当前工作目录（cwd）兜底
"""

import argparse
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────── 布局常量 ───────────────────────────

CANVAS_W     = 1800
PADDING      = 72
SWATCH_W     = 180
SWATCH_H     = 120
SWATCH_GAP   = 20
SECTION_GAP  = 48
DIVIDER_COLOR  = (220, 220, 220, 255)
BG_COLOR       = (255, 255, 255, 255)
LABEL_COLOR    = (120, 120, 120, 255)
DARK_COLOR     = (26, 26, 26, 255)
SECTION_ACCENT = (80, 80, 80, 255)


# ─────────────────────────── 工具函数 ───────────────────────────

def hex_to_rgba(hex_color: str) -> tuple:
    h = hex_color.strip().lstrip("#")
    if len(h) == 6:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    if len(h) == 8:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4, 6))
    raise ValueError(f"Invalid hex color: {hex_color}")


def load_label_font(size: int = 22):
    for path in [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_divider(draw, y, accent_label="", label_font=None):
    if accent_label and label_font:
        draw.text((PADDING, y), accent_label.upper(), font=label_font, fill=SECTION_ACCENT)
        bbox = draw.textbbox((PADDING, y), accent_label.upper(), font=label_font)
        y = bbox[3] + 10
    draw.line([(PADDING, y), (CANVAS_W - PADDING, y)], fill=DIVIDER_COLOR, width=1)
    return y + 20


def measure_text_with_spacing(draw, text, font, spacing):
    if spacing == 0:
        bb = draw.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0], bb[3] - bb[1]
    total_w, max_h = 0, 0
    for i, ch in enumerate(text):
        bb = draw.textbbox((0, 0), ch, font=font)
        total_w += (bb[2] - bb[0]) + (spacing if i < len(text) - 1 else 0)
        max_h = max(max_h, bb[3] - bb[1])
    return total_w, max_h


def draw_text_with_spacing(draw, x, y, text, font, fill, spacing):
    if spacing == 0:
        draw.text((x, y), text, font=font, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        bb = draw.textbbox((0, 0), ch, font=font)
        x += (bb[2] - bb[0]) + spacing


# ─────────────────────────── 区块渲染 ───────────────────────────

def section_header(draw, y, brand_name, font_lg, font_sm):
    draw.text((PADDING, y), f"BRAND VISUAL ASSETS  ·  {brand_name.upper()}", font=font_lg, fill=DARK_COLOR)
    bb = draw.textbbox((PADDING, y), f"BRAND VISUAL ASSETS  ·  {brand_name.upper()}", font=font_lg)
    return bb[3] + SECTION_GAP // 2


def section_logo(img, draw, y, logo_path: Path, label_font, logo_bg=(255, 255, 255, 255)):
    y = draw_divider(draw, y, "Logo", label_font)
    try:
        logo = Image.open(str(logo_path)).convert("RGBA")
    except Exception as e:
        draw.text((PADDING, y), f"[Logo load error: {e}]", font=label_font, fill=(200, 60, 60, 255))
        return y + 60

    max_w, max_h = CANVAS_W - PADDING * 2, 300
    ratio = min(max_w / logo.width, max_h / logo.height, 1.0)
    logo = logo.resize((int(logo.width * ratio), int(logo.height * ratio)), Image.LANCZOS)

    panel_h = logo.height + PADDING
    panel = Image.new("RGBA", (CANVAS_W - PADDING * 2, panel_h), logo_bg)
    panel.paste(logo, ((panel.width - logo.width) // 2, PADDING // 2), logo)
    img.paste(panel, (PADDING, y))
    return y + panel_h + SECTION_GAP


def section_colors(draw, y, color_list, label_font):
    y = draw_divider(draw, y, "Color Palette", label_font)
    x = PADDING
    for hex_val, name in color_list:
        rgba = hex_to_rgba(hex_val)
        draw.rectangle([x, y, x + SWATCH_W, y + SWATCH_H], fill=rgba)
        luma = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
        if luma > 230:
            draw.rectangle([x, y, x + SWATCH_W, y + SWATCH_H], outline=(180, 180, 180, 255), width=1)
        hex_upper = hex_val.upper() if hex_val.startswith("#") else f"#{hex_val.upper()}"
        draw.text((x, y + SWATCH_H + 6), hex_upper, font=label_font, fill=DARK_COLOR)
        if name:
            bb = draw.textbbox((x, y + SWATCH_H + 6), hex_upper, font=label_font)
            draw.text((x, bb[3] + 2), name, font=label_font, fill=LABEL_COLOR)
        x += SWATCH_W + SWATCH_GAP
        if x + SWATCH_W > CANVAS_W - PADDING:
            x = PADDING
            y += SWATCH_H + 58
    return y + SWATCH_H + 60


def section_texts(img, draw, y, texts, label_font, project_root: Path):
    y = draw_divider(draw, y, "Typography / Text Renders", label_font)
    for entry in texts:
        font_path_raw = entry.get("font", "")
        text_content  = entry.get("text", "")
        size          = int(entry.get("size", 100))
        color_hex     = entry.get("color", "#1a1a1a")
        label         = entry.get("label", "")
        spacing       = int(entry.get("letter_spacing", 0))

        if not text_content:
            continue

        info = f"{label}  ·  {Path(font_path_raw).name if font_path_raw else 'unknown font'}  ·  {size}px"
        draw.text((PADDING, y), info, font=label_font, fill=LABEL_COLOR)
        bb = draw.textbbox((PADDING, y), info, font=label_font)
        y = bb[3] + 8

        font_path = Path(font_path_raw)
        if not font_path.is_absolute():
            font_path = project_root / font_path

        if not font_path.exists():
            draw.text((PADDING, y), f"[Font not found: {font_path}]", font=label_font, fill=(200, 60, 60, 255))
            y += 40
            continue

        try:
            brand_font = ImageFont.truetype(str(font_path), size)
        except Exception as e:
            draw.text((PADDING, y), f"[Font load error: {e}]", font=label_font, fill=(200, 60, 60, 255))
            y += 40
            continue

        fill_color = hex_to_rgba(color_hex)
        bg_hex = entry.get("bg", "").strip()
        panel_bg = hex_to_rgba(bg_hex) if bg_hex else None

        text_w, text_h = measure_text_with_spacing(draw, text_content, brand_font, spacing)
        panel_w = CANVAS_W - PADDING * 2
        panel_h = size + PADDING

        if panel_bg:
            panel = Image.new("RGBA", (panel_w, panel_h), panel_bg)
            panel_draw = ImageDraw.Draw(panel)
            draw_text_with_spacing(panel_draw, PADDING // 2, PADDING // 4, text_content, brand_font, fill_color, spacing)
            img.paste(panel, (PADDING, y))
        else:
            text_layer = Image.new("RGBA", (min(text_w + PADDING * 2, CANVAS_W), panel_h), (0, 0, 0, 0))
            text_draw = ImageDraw.Draw(text_layer)
            draw_text_with_spacing(text_draw, PADDING // 2, PADDING // 4, text_content, brand_font, fill_color, spacing)
            img.paste(text_layer, (0, y), text_layer)

        y += panel_h + SECTION_GAP // 2

    return y + SECTION_GAP // 2


# ─────────────────────────── 主构建函数 ───────────────────────────

def build_sheet(brand, logo_path, color_list, texts, output_path: Path,
                logo_bg_hex="#ffffff", project_root: Path = Path(".")):
    font_sm = load_label_font(22)
    font_lg = load_label_font(36)

    est_h = 120
    if logo_path:
        est_h += 300 + SECTION_GAP + 80
    if color_list:
        rows = max(1, (len(color_list) * (SWATCH_W + SWATCH_GAP)) // (CANVAS_W - PADDING * 2) + 1)
        est_h += rows * (SWATCH_H + 58) + 80 + SECTION_GAP
    for entry in texts:
        est_h += int(entry.get("size", 100)) + SECTION_GAP + 60
    est_h += PADDING * 2

    canvas = Image.new("RGBA", (CANVAS_W, max(est_h, 400)), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    y = PADDING
    y = section_header(draw, y, brand, font_lg, font_sm)
    y += 10

    sections_rendered = []

    if logo_path:
        lp = Path(logo_path)
        if not lp.is_absolute():
            lp = project_root / lp
        logo_bg = hex_to_rgba(logo_bg_hex)
        y = section_logo(canvas, draw, y, lp, font_sm, logo_bg)
        sections_rendered.append("logo")

    if color_list:
        y = section_colors(draw, y, color_list, font_sm)
        sections_rendered.append("colors")

    if texts:
        y = section_texts(canvas, draw, y, texts, font_sm, project_root)
        sections_rendered.append("typography")

    final_h = min(y + PADDING, canvas.size[1])
    canvas = canvas.crop((0, 0, CANVAS_W, final_h))
    final = Image.new("RGB", canvas.size, (255, 255, 255))
    final.paste(canvas, mask=canvas.split()[3])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(str(output_path), "PNG")

    return {
        "success": True,
        "saved_path": str(output_path),
        "width": CANVAS_W,
        "height": final_h,
        "sections": sections_rendered,
    }


# ─────────────────────────── CLI ───────────────────────────

def parse_colors(raw: str) -> list:
    pairs = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            parts = item.split(":", 1)
            pairs.append((parts[0].strip(), parts[1].strip()))
        else:
            pairs.append((item, ""))
    return pairs


def main():
    parser = argparse.ArgumentParser(description="Brand Asset Sheet 生成器")
    parser.add_argument("--project-root", default="",
                        help="项目根目录绝对路径（可选）。不传时自动从脚本位置向上推算，"
                             "推算失败则退回到当前工作目录")
    parser.add_argument("--brand", required=True,
                        help="品牌名称，显示在合成图标题")
    parser.add_argument("--logo", default="",
                        help="Logo 图片路径（PNG/JPG），相对于 --project-root")
    parser.add_argument("--colors", default="",
                        help='色卡，格式：#HEX:名称,#HEX:名称,...')
    parser.add_argument("--texts", default="[]",
                        help='字体渲染列表，内联 JSON 数组（与 --texts-file 二选一）')
    parser.add_argument("--texts-file", default="",
                        help='字体渲染列表 JSON 文件路径，相对于 --project-root（优先于 --texts）')
    parser.add_argument("--logo-bg", default="#ffffff",
                        help="Logo 区背景色 HEX，反白 Logo 时传深色，默认 #ffffff")
    parser.add_argument("--output", default="",
                        help="输出路径，相对于 --project-root，默认 生成结果输出/brand_asset_sheets/[品牌名]-assets.png")
    args = parser.parse_args()

    # 项目根目录推算（优先级：命令行 > __file__ 向上推算 > cwd）
    if args.project_root.strip():
        project_root = Path(args.project_root).resolve()
    else:
        try:
            # 脚本位置：<project_root>/.cursor/skills/brand-asset-sheet/scripts/此文件
            # 向上5层：scripts → brand-asset-sheet → skills → .cursor → 项目根
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        except Exception:
            project_root = Path.cwd()

    # 输出路径
    if args.output.strip():
        out = Path(args.output)
        if not out.is_absolute():
            out = project_root / out
    else:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.brand)
        out = project_root / "生成结果输出" / "brand_asset_sheets" / f"{safe}-assets.png"

    # 色卡
    color_list = parse_colors(args.colors) if args.colors.strip() else []

    # 字体渲染列表
    texts_raw = args.texts
    if args.texts_file.strip():
        tf = Path(args.texts_file)
        if not tf.is_absolute():
            tf = project_root / tf
        try:
            texts_raw = tf.read_text(encoding="utf-8-sig")
        except Exception as e:
            print(json.dumps({"success": False, "error": f"无法读取 --texts-file: {e}"}, ensure_ascii=False))
            sys.exit(1)

    try:
        texts = json.loads(texts_raw)
        if not isinstance(texts, list):
            texts = []
    except Exception:
        texts = []

    result = build_sheet(
        brand=args.brand,
        logo_path=args.logo if args.logo.strip() else None,
        color_list=color_list,
        texts=texts,
        output_path=out,
        logo_bg_hex=args.logo_bg,
        project_root=project_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
