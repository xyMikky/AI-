#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
品牌视觉资产合成图生成器 — 将色卡、Logo、渲染文字合成为单张参考图。

用途：
    替代多张独立 image 参考，节省 --images 上传编号，
    同时为 AI 生图模型提供完整品牌视觉约束信息。

用法：
    python brand_asset_sheet.py \
        --brand "NEBILITY" \
        --logo "品牌规范/NEBILITY/原始素材/NEBILITY-LG-005-Logo-512w-BlackText-RedShape-20260331.png" \
        --colors "#bf192e:Brand Red,#1a1a1a:Brand Black,#ffffff:White,#f5f5f5:Light Gray" \
        --texts '[{"font":"品牌规范/NEBILITY/原始素材/figtree-bold.ttf","text":"Shape Your Style","size":100,"color":"#1a1a1a","label":"Hero Title","letter_spacing":3},{"font":"品牌规范/NEBILITY/原始素材/Archivo-Bold.ttf","text":"TUMMY CONTROL","size":80,"color":"#1a1a1a","label":"Headline","letter_spacing":4}]' \
        --output "生成结果输出/brand_asset_sheets/NEBILITY-assets.png"

输出：JSON 格式，包含 saved_path / width / height / sections / error
"""

import argparse
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR   = Path(__file__).resolve().parent
SKILL_DIR    = SCRIPT_DIR.parent
CODEX_DIR   = SKILL_DIR.parent.parent
_INFERRED_ROOT = CODEX_DIR.parent

# PROJECT_ROOT 会在 main() 中根据 --project-root 参数最终确定，
# 模块级只做推断兜底，供直接 python 调用时使用。
PROJECT_ROOT = _INFERRED_ROOT

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "生成结果输出" / "brand_asset_sheets"

CANVAS_W   = 1800
PADDING    = 72
SWATCH_W   = 180
SWATCH_H   = 120
SWATCH_GAP = 20
SECTION_GAP = 48
DIVIDER_COLOR = (220, 220, 220, 255)
BG_COLOR      = (255, 255, 255, 255)
LABEL_COLOR   = (120, 120, 120, 255)
DARK_COLOR    = (26, 26, 26, 255)
SECTION_ACCENT = (80, 80, 80, 255)


# ─────────────────────────── helpers ───────────────────────────

def hex_to_rgba(hex_color: str) -> tuple:
    h = hex_color.strip().lstrip("#")
    if len(h) == 6:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    elif len(h) == 8:
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


def draw_divider(draw: ImageDraw.Draw, y: int, accent_label: str = "", label_font=None) -> int:
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
    total_w = 0
    max_h = 0
    for i, ch in enumerate(text):
        bb = draw.textbbox((0, 0), ch, font=font)
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        total_w += w + (spacing if i < len(text) - 1 else 0)
        max_h = max(max_h, h)
    return total_w, max_h


def draw_text_with_spacing(draw, x, y, text, font, fill, spacing):
    if spacing == 0:
        draw.text((x, y), text, font=font, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        bb = draw.textbbox((0, 0), ch, font=font)
        x += (bb[2] - bb[0]) + spacing


# ─────────────────────────── section renderers ───────────────────────────

def section_header(draw, y, brand_name, label_font_lg, label_font_sm):
    """Brand name header at the top."""
    draw.text((PADDING, y), f"BRAND VISUAL ASSETS  ·  {brand_name.upper()}", font=label_font_lg, fill=DARK_COLOR)
    bb = draw.textbbox((PADDING, y), f"BRAND VISUAL ASSETS  ·  {brand_name.upper()}", font=label_font_lg)
    y = bb[3] + SECTION_GAP // 2
    return y


def section_logo(img: Image.Image, draw: ImageDraw.Draw, y: int, logo_path: Path,
                 label_font_sm, logo_bg: tuple = (255, 255, 255, 255)) -> int:
    """Paste the logo image, scaled to fit within the canvas.

    logo_bg: background color tuple (R,G,B,A) for the logo panel.
             Use a dark color when the logo is a white/light variant.
    """
    y = draw_divider(draw, y, "Logo", label_font_sm)

    try:
        logo = Image.open(str(logo_path)).convert("RGBA")
    except Exception as e:
        draw.text((PADDING, y), f"[Logo load error: {e}]", font=label_font_sm, fill=(200, 60, 60, 255))
        return y + 60

    max_logo_w = CANVAS_W - PADDING * 2
    max_logo_h = 300
    ratio = min(max_logo_w / logo.width, max_logo_h / logo.height, 1.0)
    new_w = int(logo.width * ratio)
    new_h = int(logo.height * ratio)
    logo = logo.resize((new_w, new_h), Image.LANCZOS)

    # Full-width panel with chosen background
    panel_h = new_h + PADDING
    panel = Image.new("RGBA", (CANVAS_W - PADDING * 2, panel_h), logo_bg)
    # Center logo in panel
    offset_x = (panel.width - new_w) // 2
    offset_y = PADDING // 2
    panel.paste(logo, (offset_x, offset_y), logo)

    img.paste(panel, (PADDING, y))
    y += panel_h + SECTION_GAP
    return y


def section_colors(draw: ImageDraw.Draw, y: int, color_list: list, label_font_sm) -> int:
    """Draw color swatches with HEX values and names."""
    y = draw_divider(draw, y, "Color Palette", label_font_sm)

    x = PADDING
    for hex_val, name in color_list:
        rgba = hex_to_rgba(hex_val)

        # Swatch rectangle
        draw.rectangle([x, y, x + SWATCH_W, y + SWATCH_H], fill=rgba)

        # Border for very light colors (so they're visible on white background)
        luma = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
        if luma > 230:
            draw.rectangle([x, y, x + SWATCH_W, y + SWATCH_H], outline=(180, 180, 180, 255), width=1)

        # HEX label below swatch
        hex_upper = hex_val.upper() if hex_val.startswith("#") else f"#{hex_val.upper()}"
        draw.text((x, y + SWATCH_H + 6), hex_upper, font=label_font_sm, fill=DARK_COLOR)

        # Color name below HEX
        if name:
            bb = draw.textbbox((x, y + SWATCH_H + 6), hex_upper, font=label_font_sm)
            draw.text((x, bb[3] + 2), name, font=label_font_sm, fill=LABEL_COLOR)

        x += SWATCH_W + SWATCH_GAP

        # Wrap to next row if we'd overflow
        if x + SWATCH_W > CANVAS_W - PADDING:
            x = PADDING
            y += SWATCH_H + 58

    y += SWATCH_H + 60
    return y


def section_texts(img: Image.Image, draw: ImageDraw.Draw, y: int, texts: list, label_font_sm) -> int:
    """Render each text entry using its brand font."""
    y = draw_divider(draw, y, "Typography / Text Renders", label_font_sm)

    for entry in texts:
        font_path_raw = entry.get("font", "")
        text_content  = entry.get("text", "")
        size          = int(entry.get("size", 100))
        color_hex     = entry.get("color", "#1a1a1a")
        label         = entry.get("label", "")
        spacing       = int(entry.get("letter_spacing", 0))

        if not text_content:
            continue

        # Section label
        section_info = f"{label}  ·  {Path(font_path_raw).name if font_path_raw else 'unknown font'}  ·  {size}px"
        draw.text((PADDING, y), section_info, font=label_font_sm, fill=LABEL_COLOR)
        bb = draw.textbbox((PADDING, y), section_info, font=label_font_sm)
        y = bb[3] + 8

        font_path = Path(font_path_raw)
        if not font_path.is_absolute():
            font_path = PROJECT_ROOT / font_path

        if not font_path.exists():
            draw.text((PADDING, y), f"[Font not found: {font_path}]", font=label_font_sm, fill=(200, 60, 60, 255))
            y += 40
            continue

        try:
            brand_font = ImageFont.truetype(str(font_path), size)
        except Exception as e:
            draw.text((PADDING, y), f"[Font load error: {e}]", font=label_font_sm, fill=(200, 60, 60, 255))
            y += 40
            continue

        fill_color = hex_to_rgba(color_hex)

        # Optional per-entry background (e.g. dark panel for white text)
        bg_hex    = entry.get("bg", "").strip()
        panel_bg  = hex_to_rgba(bg_hex) if bg_hex else None

        text_w, text_h = measure_text_with_spacing(draw, text_content, brand_font, spacing)
        panel_w = CANVAS_W - PADDING * 2
        panel_h = size + PADDING

        if panel_bg:
            # Full-width colored panel
            panel = Image.new("RGBA", (panel_w, panel_h), panel_bg)
            panel_draw = ImageDraw.Draw(panel)
            draw_text_with_spacing(panel_draw, PADDING // 2, PADDING // 4,
                                   text_content, brand_font, fill_color, spacing)
            img.paste(panel, (PADDING, y))
        else:
            # Transparent layer on white canvas
            text_layer = Image.new("RGBA", (min(text_w + PADDING * 2, CANVAS_W), panel_h), (0, 0, 0, 0))
            text_draw  = ImageDraw.Draw(text_layer)
            draw_text_with_spacing(text_draw, PADDING // 2, PADDING // 4,
                                   text_content, brand_font, fill_color, spacing)
            img.paste(text_layer, (0, y), text_layer)

        y += panel_h + SECTION_GAP // 2

    return y + SECTION_GAP // 2


# ─────────────────────────── main build ───────────────────────────

def build_sheet(brand: str, logo_path, color_list, texts, output_path: Path,
                logo_bg_hex: str = "#ffffff") -> dict:
    label_font_sm = load_label_font(22)
    label_font_lg = load_label_font(36)

    # First pass: measure total height by dry-running the layout
    # Estimate conservatively (actual height <= estimate)
    est_h = 120                                      # header
    if logo_path:
        est_h += 300 + SECTION_GAP + 80             # logo + divider
    if color_list:
        rows = max(1, (len(color_list) * (SWATCH_W + SWATCH_GAP)) // (CANVAS_W - PADDING * 2) + 1)
        est_h += rows * (SWATCH_H + 58) + 80 + SECTION_GAP
    for entry in texts:
        est_h += int(entry.get("size", 100)) + SECTION_GAP + 60
    est_h += PADDING * 2

    canvas = Image.new("RGBA", (CANVAS_W, max(est_h, 400)), BG_COLOR)
    draw   = ImageDraw.Draw(canvas)

    y = PADDING
    y = section_header(draw, y, brand, label_font_lg, label_font_sm)
    y += 10

    sections_rendered = []

    if logo_path:
        logo_p = Path(logo_path)
        if not logo_p.is_absolute():
            logo_p = PROJECT_ROOT / logo_p
        logo_bg = hex_to_rgba(logo_bg_hex)
        y = section_logo(canvas, draw, y, logo_p, label_font_sm, logo_bg)
        sections_rendered.append("logo")

    if color_list:
        y = section_colors(draw, y, color_list, label_font_sm)
        sections_rendered.append("colors")

    if texts:
        y = section_texts(canvas, draw, y, texts, label_font_sm)
        sections_rendered.append("typography")

    # Crop to actual content
    final_h = min(y + PADDING, canvas.size[1])
    canvas = canvas.crop((0, 0, CANVAS_W, final_h))

    # Convert to RGB for final save (JPEG-compatible, but we save PNG)
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
    """Parse "#HEX:Label,#HEX:Label,..." into [(hex, label), ...]."""
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
    global PROJECT_ROOT, DEFAULT_OUTPUT_DIR

    parser = argparse.ArgumentParser(description="品牌视觉资产合成图生成器")
    parser.add_argument("--brand",  required=True,
                        help="品牌名称，用于标题标注")
    parser.add_argument("--logo",   default="",
                        help="Logo 图片文件路径（PNG/JPG），支持透明背景")
    parser.add_argument("--colors", default="",
                        help='色卡列表，格式：#HEX:名称,#HEX:名称,...  例：#bf192e:Brand Red,#1a1a1a:Black')
    parser.add_argument("--texts",  default="[]",
                        help='文字渲染列表，JSON 数组，每项含 font/text/size/color/label/letter_spacing')
    parser.add_argument("--texts-file", default="",
                        help='文字渲染列表的 JSON 文件路径（与 --texts 二选一，文件优先）')
    parser.add_argument("--logo-bg", default="#ffffff",
                        help="Logo 区背景色，HEX 格式，深色/反白Logo时传入深色背景，默认 #ffffff")
    parser.add_argument("--output", default="",
                        help="输出路径，默认 生成结果输出/brand_asset_sheets/[品牌名]-assets.png")
    parser.add_argument("--project-root", default="",
                        help="项目根目录绝对路径。通过 exec() 方式调用时必传，否则相对路径解析会错误")

    args = parser.parse_args()

    # 若传入 --project-root，覆盖模块级推断值（exec 方式调用时必须传此参数）
    if args.project_root.strip():
        PROJECT_ROOT = Path(args.project_root).resolve()
        DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "生成结果输出" / "brand_asset_sheets"

    # Output path
    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = PROJECT_ROOT / out_path
    else:
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.brand)
        out_path = DEFAULT_OUTPUT_DIR / f"{safe_name}-assets.png"

    # Parse colors
    color_list = parse_colors(args.colors) if args.colors.strip() else []

    # Parse texts (--texts-file takes priority over --texts)
    texts_raw = args.texts
    if hasattr(args, "texts_file") and args.texts_file.strip():
        tf = Path(args.texts_file)
        if not tf.is_absolute():
            tf = PROJECT_ROOT / tf
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
        output_path=out_path,
        logo_bg_hex=args.logo_bg,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
