#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Color Palette Generator — Minimal Edition
颜色占据画布主体，文字仅标注色号和占比，减少干扰，让 AI 模型专注感知颜色。

用法示例：
    python ".codex/skills/color-palette-generator/scripts/generate_color_palette.py" \
        --colors "#f5f2ee:Warm Cream Background:60,#3d1f0a:Dark Brown Product:30,#f5c800:Accent Yellow:10" \
        --title "NEBILITY-ShaperShort-Cream" \
        --output "生成结果输出/color_palettes/NEBILITY-cream-palette.png"

--colors 格式：#hex:名称:占比,...  （占比为整数，总和约100；可省略，省略时均分剩余）
所有路径均相对于项目根目录。
"""

import argparse
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# ──────────────────────── 布局常量 ────────────────────────

CANVAS_W     = 1800          # 画布宽度
COLOR_H      = 480           # 颜色色块高度（占主体）
LABEL_H      = 72            # 底部标签条高度
TOTAL_H      = COLOR_H + LABEL_H
GAP          = 4             # 色块之间的间隙（px）

BG_COLOR     = (250, 250, 250, 255)
LABEL_BG     = (245, 245, 245, 255)
DARK_TEXT    = (30,  30,  30,  255)
LIGHT_TEXT   = (255, 255, 255, 255)
MUTED_TEXT   = (110, 110, 110, 255)


# ──────────────────────── 工具函数 ────────────────────────

def get_project_root() -> Path:
    try:
        root = Path(__file__).resolve()
        for _ in range(5):
            root = root.parent
        if (root / "主控中心.txt").exists():
            return root
    except Exception:
        pass
    return Path.cwd()


def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.strip().lstrip("#")
    if len(h) == 6:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    raise ValueError(f"Invalid hex color: {hex_color!r}")


def is_dark(rgb: tuple) -> bool:
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b < 155


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    candidates += [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def text_w(draw: ImageDraw.Draw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


# ──────────────────────── 解析颜色 ────────────────────────

def parse_colors(colors_str: str) -> list:
    entries = []
    total_given = 0
    for part in colors_str.split(","):
        part = part.strip()
        if not part:
            continue
        segs = [s.strip() for s in part.split(":")]
        hex_code   = segs[0] if segs[0].startswith("#") else "#" + segs[0]
        name       = segs[1] if len(segs) > 1 else hex_code
        proportion = int(segs[2]) if len(segs) > 2 and segs[2].isdigit() else None
        entries.append({"hex": hex_code, "name": name, "proportion": proportion})
        if proportion is not None:
            total_given += proportion

    # 均分剩余给未指定的颜色
    unspecified = [e for e in entries if e["proportion"] is None]
    if unspecified:
        remaining = max(0, 100 - total_given)
        share     = remaining // len(unspecified)
        leftover  = remaining - share * len(unspecified)
        for i, e in enumerate(unspecified):
            e["proportion"] = share + (1 if i < leftover else 0)

    # 归一化
    total = sum(e["proportion"] for e in entries)
    if total != 100 and total > 0:
        new_total = 0
        for e in entries[:-1]:
            e["proportion"] = max(1, round(e["proportion"] * 100 / total))
            new_total += e["proportion"]
        entries[-1]["proportion"] = max(1, 100 - new_total)

    return entries


# ──────────────────────── 生成色卡图 ──────────────────────

def generate_palette(colors: list, title: str, output_path: Path) -> dict:
    n = len(colors)

    # 按比例计算每列宽度（含间隙）
    total_gap   = GAP * (n - 1)
    usable_w    = CANVAS_W - total_gap
    raw_widths  = [max(40, round(usable_w * c["proportion"] / 100)) for c in colors]
    diff        = usable_w - sum(raw_widths)
    raw_widths[-1] += diff

    # 字体
    f_hex   = load_font(36, bold=True)   # 色块内色号
    f_pct   = load_font(28)              # 色块内占比
    f_name  = load_font(22)              # 底部标签：颜色角色名

    img  = Image.new("RGBA", (CANVAS_W, TOTAL_H), LABEL_BG)
    draw = ImageDraw.Draw(img)

    x = 0
    for i, (c, sw) in enumerate(zip(colors, raw_widths)):
        rgb  = hex_to_rgb(c["hex"])
        dark = is_dark(rgb)
        on_block = LIGHT_TEXT if dark else DARK_TEXT

        # ── 色块主体 ──
        block_x2 = x + sw
        draw.rectangle([x, 0, block_x2, COLOR_H], fill=rgb + (255,))

        # 色号：左下角，距底部 52px
        hex_txt = c["hex"].upper()
        draw.text((x + 16, COLOR_H - 54), hex_txt, font=f_hex, fill=on_block)

        # 占比：色号右侧，同行
        pct_txt = f"{c['proportion']}%"
        hw = text_w(draw, hex_txt, f_hex)
        draw.text((x + 16 + hw + 14, COLOR_H - 50), pct_txt, font=f_pct, fill=on_block)

        # ── 底部标签条 ──
        label_y = COLOR_H + (LABEL_H - 26) // 2
        draw.text((x + 12, label_y), c["name"], font=f_name, fill=MUTED_TEXT)

        x = block_x2 + GAP

    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(str(output_path), quality=95)

    # prompt_snippet（供 Prompt 引用，不放在图里）
    snippet = ["Color palette reference (image N — replace N with actual index):"]
    for c in colors:
        snippet.append(
            f"  - {c['name']}: use exactly {c['hex'].upper()} "
            f"({c['proportion']}% of image area)"
        )
    snippet.append(
        'Prompt format: "use exactly #HEX ([role name]) from image N — NOT [wrong color], specifically [#HEX]"'
    )

    return {
        "success": True,
        "saved_path": str(output_path),
        "width": CANVAS_W,
        "height": TOTAL_H,
        "colors": colors,
        "prompt_snippet": "\n".join(snippet)
    }


# ──────────────────────── 主入口 ──────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--colors",       required=True,
                    help="#hex:name:proportion,...  proportion 可省略（均分）")
    ap.add_argument("--title",        default="Color Palette")
    ap.add_argument("--output",       default=None,
                    help="输出路径（相对项目根目录）")
    ap.add_argument("--project-root", default=None)
    args = ap.parse_args()

    root   = Path(args.project_root).resolve() if args.project_root else get_project_root()
    colors = parse_colors(args.colors)

    safe   = args.title.replace(" ", "-").replace("/", "-")
    out    = root / (args.output or f"生成结果输出/color_palettes/{safe}-palette.png")

    result = generate_palette(colors, args.title, out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
