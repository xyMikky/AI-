---

name: brand-asset-sheet
description: "生成品牌视觉资产合成图（Brand Asset Sheet），将 Logo、色卡、品牌字体渲染文字合成为单张参考图，节省 AI 生图的 --images 上传编号槽位，同时为 Nano Banana / Gemini 图片编辑模型提供完整的品牌视觉约束信息。适用于在调用 rh-image-pro-img2img 或 rh-image-pro-txt2img 之前，先准备好品牌参考图。关键词：品牌资产图、Logo合成、色卡、字体渲染、brand asset sheet、品牌参考图、视觉约束、AI生图前置准备。"

# Brand Asset Sheet 生成器

## 概述

将品牌的 Logo、色板、字体排版渲染为 **单张 PNG 参考图**，作为 `image N` 传入 `rh-image-pro-img2img` 等生图 skill，让 AI 模型一次性感知完整品牌视觉约束，而不需要占用多个 `--images` 槽位。

- 入口脚本：`.codex/skills/brand-asset-sheet/scripts/generate_brand_asset_sheet.py`
- 输出默认目录：`生成结果输出/brand_asset_sheets/`

---

## 使用时机

在调用 `rh-image-pro-img2img` / `rh-image-pro-txt2img` **之前**，当以下任一条件成立时先生成品牌资产图：

- 需要 AI 精准还原品牌 Logo 样式
- 需要 AI 遵守品牌色系（主色 / 辅助色 / 背景色）
- 需要 AI 使用品牌字体渲染文案（如 Slogan、促销标签）
- 参考图 `--images` 槽位紧张，需要把多个品牌元素合并到 1 张图

---

## 调用方式（标准方式，推荐）

**直接用 `python` 调用脚本**，在项目根目录下运行，所有路径使用**相对于项目根目录的相对路径**。脚本会自动从自身 `__file__` 位置向上推算项目根目录，无需传入绝对路径，换盘符换电脑都不受影响：

```powershell
python ".codex/skills/brand-asset-sheet/scripts/generate_brand_asset_sheet.py" `
  --brand "NEBILITY" `
  --logo "品牌规范/NEBILITY/原始素材/NEBILITY-LG-005-Logo-512w-BlackText-RedShape-20260331.png" `
  --colors "#bf192e:Brand Red,#1a1a1a:Brand Black,#ffffff:White,#f5f5f5:Light Gray" `
  --texts-file "生成结果输出/brand_asset_sheets/NEBILITY-texts.json" `
  --output "生成结果输出/brand_asset_sheets/NEBILITY-promo-assets.png"
```

> Shell 工具的 `working_directory` 必须设为项目根目录，**不要硬编码盘符**（如 `f:\` 或 `g:\`），项目插入不同电脑时盘符可能变化。

---

## 参数说明


| 参数               | 必填  | 说明                                                                                                                                                              |
| ---------------- | --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--project-root` | 否   | 项目根目录绝对路径。**通常不需要传**，脚本默认从自身 `__file__` 向上推5层自动推算（`scripts/` → `brand-asset-sheet/` → `skills/` → `.codex/` → 项目根）。仅在通过 `exec()` 等特殊方式调用导致 `__file__` 失效时才手动指定 |
| `--brand`        | 是   | 品牌名称，显示在合成图标题区                                                                                                                                                  |
| `--logo`         | 否   | Logo 图片路径（PNG/JPG，支持透明背景）。相对路径以项目根目录为基准                                                                                                                         |
| `--colors`       | 否   | 色卡，格式：`#HEX:名称,#HEX:名称,...`                                                                                                                                     |
| `--texts`        | 否   | 字体渲染列表，内联 JSON 数组（与 `--texts-file` 二选一）                                                                                                                         |
| `--texts-file`   | 否   | 字体渲染列表 JSON 文件路径，相对路径以项目根目录为基准（推荐，避免 shell 转义问题）                                                                                                                |
| `--logo-bg`      | 否   | Logo 区背景色，HEX 格式。反白 Logo 时传深色背景，默认 `#ffffff`                                                                                                                    |
| `--output`       | 否   | 输出路径，相对路径以项目根目录为基准。默认 `生成结果输出/brand_asset_sheets/[品牌名]-assets.png`                                                                                              |


---

## --texts-file JSON 格式

`--texts-file` 接受一个 JSON 文件，内容为数组，每项描述一段渲染文字：

```json
[
  {
    "font": "品牌规范/NEBILITY/原始素材/figtree-bold.ttf",
    "text": "Shape Your Style",
    "size": 100,
    "color": "#1a1a1a",
    "label": "Slogan",
    "letter_spacing": 3
  },
  {
    "font": "品牌规范/NEBILITY/原始素材/figtree-bold.ttf",
    "text": "NEW ARRIVAL",
    "size": 90,
    "color": "#bf192e",
    "label": "Promo Label",
    "letter_spacing": 5
  }
]
```

字体路径使用**相对于项目根目录的相对路径**，脚本会自动拼接为绝对路径。

---

## 完整操作流程

### Step 1：准备 texts JSON 文件

将字体渲染配置写入 JSON 文件，放在项目内任意位置（推荐 `生成结果输出/brand_asset_sheets/`）。

用 Write 工具创建，例如 `生成结果输出/brand_asset_sheets/NEBILITY-texts.json`，内容参考上方格式。

### Step 2：运行脚本

```powershell
python ".codex/skills/brand-asset-sheet/scripts/generate_brand_asset_sheet.py" `
  --brand "NEBILITY" `
  --logo "品牌规范/NEBILITY/原始素材/NEBILITY-LG-005-Logo-512w-BlackText-RedShape-20260331.png" `
  --colors "#bf192e:Brand Red,#1a1a1a:Brand Black,#ffffff:White,#f5f5f5:Light Gray" `
  --texts-file "生成结果输出/brand_asset_sheets/NEBILITY-texts.json" `
  --output "生成结果输出/brand_asset_sheets/NEBILITY-promo-assets.png"
```

Shell 工具的 `working_directory` 设为项目根目录（不要写死盘符，用工作区路径变量）。

### Step 3：确认输出

脚本输出 JSON，`saved_path` 为实际保存路径（绝对路径，随当前盘符自动变化）：

```json
{
  "success": true,
  "saved_path": "<当前盘符>:\\AI设计师助手\\生成结果输出\\brand_asset_sheets\\NEBILITY-promo-assets.png",
  "width": 1800,
  "height": 1404,
  "sections": ["logo", "colors", "typography"]
}
```

用 Read 工具读取 `saved_path` 中的 PNG 文件，目视确认 Logo、色卡、字体均已正确渲染。

### Step 4：传入生图 skill

将输出的 PNG 作为 `--images` 参数之一传入 `rh-image-pro-img2img`：

```powershell
python ".codex/skills/rh-image-pro-img2img/scripts/generate_image.py" `
  --images "用户参考图.jpg" "生成结果输出/brand_asset_sheets/NEBILITY-promo-assets.png" `
  --prompt "... 使用 image 2 中的品牌 Logo、色彩方案和字体排版风格 ..." `
  --aspect-ratio "1:1" --resolution "2k" --label "NEBILITY-Front"
```

---

## 常见错误与排查


| 错误信息                                                   | 原因                | 解决方法                                              |
| ------------------------------------------------------ | ----------------- | ------------------------------------------------- |
| `[Logo load error: ... No such file or directory ...]` | 项目根目录推算失败，或相对路径写错 | 确认 `working_directory` 设为项目根目录；路径用 `Test-Path` 验证 |
| `[Font not found: ...]`                                | 同上，字体相对路径解析失败     | 同上                                                |
| Logo/字体路径正确但找不到文件                                      | 相对路径写法有误          | 确认路径相对于项目根目录，斜线方向用 `/` 或 `\\` 均可                  |
| `--texts` JSON 解析失败                                    | shell 转义问题        | 改用 `--texts-file`，将 JSON 写入文件再传路径                 |


---

## 注意事项

- **不要硬编码盘符**：项目插入不同电脑时盘符（`f:\`/`g:\` 等）可能变化，任何路径都不要写死盘符
- **优先用 `--texts-file`**：直接在 shell 里写 JSON 字符串极易被转义破坏，写入文件再传路径更稳定
- **所有相对路径以项目根目录为基准**：Logo、字体、output、texts 内的 font 路径均如此
- `**working_directory` 必须是项目根目录**：Shell 工具调用时务必设置，脚本通过 `__file__` 推算根目录依赖此前提
- `**--project-root` 仅特殊场景使用**：通过 `exec()` 导致 `__file__` 失效时才需要手动传入

