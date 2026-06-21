#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体预览图自动生成器 — 为 00_待学习/ 中没有配套预览图的字体文件自动生成预览。

用途：
    M10 学习流程的前置步骤。扫描 00_待学习/ 中的字体文件，
    如果没有同名预览图，则自动渲染一张包含完整字体特征信息的预览图。

用法：
    python generate_font_preview.py
    python generate_font_preview.py --dir "参考库/00_待学习"
    python generate_font_preview.py --font "某字体.ttf"  # 只处理单个文件

输出：JSON 格式，包含 generated / skipped / errors
"""

import argparse
import json
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR   = Path(__file__).resolve().parent
SKILL_DIR    = SCRIPT_DIR.parent
CURSOR_DIR   = SKILL_DIR.parent.parent
PROJECT_ROOT = CURSOR_DIR.parent

DEFAULT_LEARN_DIR = PROJECT_ROOT / "参考库" / "00_待学习"

FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

CANVAS_WIDTH = 1800
BG_COLOR = (255, 255, 255, 255)
TEXT_COLOR = (26, 26, 26, 255)       # #1A1A1A
LIGHT_TEXT = (120, 120, 120, 255)    # #787878
ACCENT_COLOR = (0, 102, 204, 255)   # #0066CC
DIVIDER_COLOR = (220, 220, 220, 255)
PADDING = 60


def try_load_font(font_path: Path, size: int):
    try:
        return ImageFont.truetype(str(font_path), size)
    except Exception:
        return None


def has_glyph(font, char):
    """Check if font has a glyph for the given character."""
    try:
        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        bbox = d.textbbox((0, 0), char, font=font)
        tofu_bbox = d.textbbox((0, 0), "\uffff", font=font)
        return (bbox[2] - bbox[0]) > 0 and bbox != tofu_bbox
    except Exception:
        return False


def detect_font_capabilities(font_path: Path):
    """Detect what character sets the font supports."""
    font = try_load_font(font_path, 40)
    if not font:
        return {"latin": False, "cjk": False, "cyrillic": False}

    latin = has_glyph(font, "A") and has_glyph(font, "a")
    cjk = has_glyph(font, "中") and has_glyph(font, "文")
    cyrillic = has_glyph(font, "Б")

    return {"latin": latin, "cjk": cjk, "cyrillic": cyrillic}


def draw_divider(draw, y, width):
    draw.line([(PADDING, y), (width - PADDING, y)], fill=DIVIDER_COLOR, width=1)
    return y + 20


def get_font_name(font_path: Path):
    """Try to extract font family name from the file."""
    try:
        font = try_load_font(font_path, 20)
        if font and hasattr(font, "getname"):
            family, style = font.getname()
            if family:
                return family, style or ""
    except Exception:
        pass
    stem = font_path.stem
    parts = stem.rsplit("-", 1)
    family = parts[0].replace("-", " ")
    style = parts[1] if len(parts) > 1 else ""
    return family, style


def generate_preview(font_path: Path, output_path: Path) -> dict:
    """Generate a comprehensive font preview image."""

    font_path = Path(font_path)
    if not font_path.exists():
        return {"success": False, "error": f"字体文件不存在: {font_path}"}

    caps = detect_font_capabilities(font_path)
    family_name, style_name = get_font_name(font_path)
    full_name = f"{family_name} {style_name}".strip()

    # Load fonts at different sizes
    sizes = {
        "title": 72,
        "section": 20,
        "large": 56,
        "medium": 40,
        "body": 28,
        "small": 20,
        "tiny": 16,
    }
    fonts = {}
    for key, sz in sizes.items():
        f = try_load_font(font_path, sz)
        if not f:
            return {"success": False, "error": f"无法加载字体: {font_path}"}
        fonts[key] = f

    # Use a system font for labels
    label_font = None
    for fallback in ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        label_font = try_load_font(Path(fallback), 18)
        if label_font:
            break
    if not label_font:
        label_font = ImageFont.load_default()

    label_font_big = None
    for fallback in ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]:
        label_font_big = try_load_font(Path(fallback), 14)
        if label_font_big:
            break
    if not label_font_big:
        label_font_big = label_font

    # --- Build the preview in a tall canvas, then crop ---
    canvas_h = 2400
    img = Image.new("RGBA", (CANVAS_WIDTH, canvas_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = PADDING

    # ── Section 1: Font Name (rendered in its own typeface) ──
    draw.text((PADDING, y), full_name, font=fonts["title"], fill=TEXT_COLOR)
    bbox = draw.textbbox((PADDING, y), full_name, font=fonts["title"])
    y = bbox[3] + 8

    # File info line
    info_text = f"{font_path.suffix.upper().lstrip('.')}  ·  {font_path.name}"
    draw.text((PADDING, y), info_text, font=label_font, fill=LIGHT_TEXT)
    y += 30

    y = draw_divider(draw, y, CANVAS_WIDTH)

    # ── Section 2: Alphabet ──
    if caps["latin"]:
        draw.text((PADDING, y), "ALPHABET", font=label_font, fill=ACCENT_COLOR)
        y += 28

        upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        draw.text((PADDING, y), upper, font=fonts["medium"], fill=TEXT_COLOR)
        bbox = draw.textbbox((PADDING, y), upper, font=fonts["medium"])
        y = bbox[3] + 12

        lower = "abcdefghijklmnopqrstuvwxyz"
        draw.text((PADDING, y), lower, font=fonts["medium"], fill=TEXT_COLOR)
        bbox = draw.textbbox((PADDING, y), lower, font=fonts["medium"])
        y = bbox[3] + 12

        nums = "0123456789  !@#$%&*()  .,;:?!-—'\"…"
        draw.text((PADDING, y), nums, font=fonts["body"], fill=TEXT_COLOR)
        bbox = draw.textbbox((PADDING, y), nums, font=fonts["body"])
        y = bbox[3] + 20

        y = draw_divider(draw, y, CANVAS_WIDTH)

    # ── Section 3: CJK Characters (if supported) ──
    if caps["cjk"]:
        draw.text((PADDING, y), "中文字符", font=label_font, fill=ACCENT_COLOR)
        y += 28

        cjk_sample = "永远不要放弃梦想 设计改变世界"
        draw.text((PADDING, y), cjk_sample, font=fonts["medium"], fill=TEXT_COLOR)
        bbox = draw.textbbox((PADDING, y), cjk_sample, font=fonts["medium"])
        y = bbox[3] + 12

        cjk_chars = "天地玄黄 宇宙洪荒 日月盈昃 辰宿列张"
        draw.text((PADDING, y), cjk_chars, font=fonts["body"], fill=TEXT_COLOR)
        bbox = draw.textbbox((PADDING, y), cjk_chars, font=fonts["body"])
        y = bbox[3] + 20

        y = draw_divider(draw, y, CANVAS_WIDTH)

    # ── Section 4: Size Comparison ──
    draw.text((PADDING, y), "SIZE COMPARISON", font=label_font, fill=ACCENT_COLOR)
    y += 28

    sample_text = "Shapewear Bodysuit" if caps["latin"] else "塑身连体衣"

    for label, font_key in [("56px", "large"), ("40px", "medium"), ("28px", "body"), ("20px", "small"), ("16px", "tiny")]:
        draw.text((PADDING, y), label, font=label_font_big, fill=LIGHT_TEXT)
        draw.text((PADDING + 60, y), sample_text, font=fonts[font_key], fill=TEXT_COLOR)
        bbox = draw.textbbox((PADDING + 60, y), sample_text, font=fonts[font_key])
        y = max(bbox[3] + 8, y + fonts[font_key].size + 8)

    y += 12
    y = draw_divider(draw, y, CANVAS_WIDTH)

    # ── Section 5: Paragraph / Context ──
    draw.text((PADDING, y), "PARAGRAPH SAMPLE", font=label_font, fill=ACCENT_COLOR)
    y += 28

    if caps["latin"]:
        paragraphs = [
            "The quick brown fox jumps over the lazy dog.",
            "Designed for all women with the ultimate balance between",
            "compression, comfort, and inclusivity. Premium quality",
            "shapewear that moves with you throughout the day.",
        ]
        for line in paragraphs:
            draw.text((PADDING, y), line, font=fonts["body"], fill=TEXT_COLOR)
            bbox = draw.textbbox((PADDING, y), line, font=fonts["body"])
            y = bbox[3] + 6

    if caps["cjk"]:
        y += 8
        cn_paragraphs = [
            "为所有女性设计，在压缩、舒适与包容之间",
            "实现终极平衡。高品质塑身衣，全天候随你而动。",
        ]
        for line in cn_paragraphs:
            draw.text((PADDING, y), line, font=fonts["body"], fill=TEXT_COLOR)
            bbox = draw.textbbox((PADDING, y), line, font=fonts["body"])
            y = bbox[3] + 6

    y += 20
    y = draw_divider(draw, y, CANVAS_WIDTH)

    # ── Section 6: Headline Styles (typical use cases) ──
    draw.text((PADDING, y), "HEADLINE STYLES", font=label_font, fill=ACCENT_COLOR)
    y += 28

    headlines = []
    if caps["latin"]:
        headlines += [
            ("ALL CAPS TRACKING", "TUMMY CONTROL SHAPEWEAR", fonts["large"], 4),
            ("Title Case", "Buttery Soft Everyday Comfort", fonts["medium"], 0),
            ("lowercase minimal", "designed for confidence", fonts["body"], 0),
        ]
    if caps["cjk"]:
        headlines += [
            ("中文标题", "轻塑·自在呼吸", fonts["large"], 0),
            ("中文正文", "收腹塑形 防晒防护 速干面料", fonts["body"], 0),
        ]

    for label, text, font, spacing in headlines:
        draw.text((PADDING, y), label, font=label_font_big, fill=LIGHT_TEXT)
        y += 22
        if spacing > 0:
            cursor_x = PADDING
            for ch in text:
                draw.text((cursor_x, y), ch, font=font, fill=TEXT_COLOR)
                bbox = draw.textbbox((0, 0), ch, font=font)
                cursor_x += (bbox[2] - bbox[0]) + spacing
            bbox = draw.textbbox((PADDING, y), text, font=font)
            y += font.size + 16
        else:
            draw.text((PADDING, y), text, font=font, fill=TEXT_COLOR)
            bbox = draw.textbbox((PADDING, y), text, font=font)
            y = bbox[3] + 16

    y += 10
    y = draw_divider(draw, y, CANVAS_WIDTH)

    # ── Section 7: Contrast / Weight feel ──
    draw.text((PADDING, y), "WEIGHT & CONTRAST", font=label_font, fill=ACCENT_COLOR)
    y += 28

    contrast_pairs = [
        ("iiillll111", "MMWWOO000"),
        ("aeiou", "bdpqg"),
    ] if caps["latin"] else [
        ("一二三十", "國鬱靈體"),
    ]

    for left, right in contrast_pairs:
        combined = f"{left}     {right}"
        draw.text((PADDING, y), combined, font=fonts["large"], fill=TEXT_COLOR)
        bbox = draw.textbbox((PADDING, y), combined, font=fonts["large"])
        y = bbox[3] + 12

    y += 20

    # ── Crop canvas to actual content ──
    final_h = min(y + PADDING, canvas_h)
    img = img.crop((0, 0, CANVAS_WIDTH, final_h))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")

    return {
        "success": True,
        "saved_path": str(output_path),
        "font_name": full_name,
        "width": CANVAS_WIDTH,
        "height": final_h,
        "supports_latin": caps["latin"],
        "supports_cjk": caps["cjk"],
    }


def find_unpaired_fonts(directory: Path):
    """Find font files that don't have a matching preview image."""
    directory = Path(directory)
    if not directory.exists():
        return []

    all_files = []
    try:
        for f in directory.iterdir():
            all_files.append(f)
    except Exception:
        return []

    font_files = [f for f in all_files if f.suffix.lower() in FONT_EXTENSIONS]
    image_stems = {f.stem.lower() for f in all_files if f.suffix.lower() in IMAGE_EXTENSIONS}

    unpaired = []
    for ff in font_files:
        stem_lower = ff.stem.lower()
        has_preview = any(
            stem_lower in img_stem or img_stem in stem_lower
            for img_stem in image_stems
        )
        if not has_preview:
            unpaired.append(ff)

    return unpaired


def main():
    parser = argparse.ArgumentParser(
        description="字体预览图自动生成器 — 为无配套预览图的字体文件生成预览")
    parser.add_argument("--dir", default="",
                        help="扫描目录，默认 参考库/00_待学习/")
    parser.add_argument("--font", default="",
                        help="仅处理单个字体文件")

    args = parser.parse_args()

    results = {"generated": [], "skipped": [], "errors": []}

    if args.font:
        font_path = Path(args.font)
        if not font_path.is_absolute():
            font_path = PROJECT_ROOT / font_path
        if not font_path.exists():
            results["errors"].append({"font": str(font_path), "error": "文件不存在"})
        else:
            out_name = font_path.stem + "_preview.png"
            default_out_dir = PROJECT_ROOT / "生成结果输出" / "font_renders"
            out_path = default_out_dir / out_name
            r = generate_preview(font_path, out_path)
            if r["success"]:
                results["generated"].append({
                    "font": font_path.name,
                    "preview": str(out_path),
                    "font_name": r.get("font_name", ""),
                })
            else:
                results["errors"].append({"font": font_path.name, "error": r["error"]})
    else:
        scan_dir = Path(args.dir) if args.dir else DEFAULT_LEARN_DIR
        if not scan_dir.is_absolute():
            scan_dir = PROJECT_ROOT / scan_dir

        if not scan_dir.exists():
            print(json.dumps({"success": False, "error": f"目录不存在: {scan_dir}"},
                             ensure_ascii=False, indent=2))
            sys.exit(1)

        unpaired = find_unpaired_fonts(scan_dir)

        if not unpaired:
            results["skipped"].append("所有字体文件均已有配套预览图，无需生成")
        else:
            for font_path in unpaired:
                out_name = font_path.stem + "_preview.png"
                out_path = font_path.parent / out_name
                r = generate_preview(font_path, out_path)
                if r["success"]:
                    results["generated"].append({
                        "font": font_path.name,
                        "preview": out_name,
                        "font_name": r.get("font_name", ""),
                    })
                else:
                    results["errors"].append({"font": font_path.name, "error": r["error"]})

    results["total_generated"] = len(results["generated"])
    results["total_errors"] = len(results["errors"])
    print(json.dumps(results, ensure_ascii=False, indent=2))
    sys.exit(0 if results["total_errors"] == 0 else 1)


if __name__ == "__main__":
    main()
