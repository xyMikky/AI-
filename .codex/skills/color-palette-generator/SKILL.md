---

name: color-palette-generator
description: "生成配色参考色卡图（Color Palette Reference），将每个颜色按画面占比比例可视化，每个色块下方标注精确色号（#hex）、颜色角色名称和面积占比。输出 PNG 色卡图作为 image N 传入 rh-image-pro-img2img，同时生成配套 Prompt 片段，实现「image N 中的 #hex 色号」精准颜色引用，解决 AI 生图颜色偏差问题。与 M2（配色系统设计）配合使用：M2 决策配色方案，本 skill 生成视觉色卡锚定颜色执行。关键词：色卡、配色参考图、颜色比例、色号标注、颜色准确性、color palette、hex color reference、AI生图颜色控制。"

# Color Palette Generator

## 概述

将设计配色方案生成为 **单张 PNG 色卡参考图**，作为 `image N` 传入 `rh-image-pro-img2img`，让 AI 模型能精确感知每个颜色的色号和画面占比，大幅减少颜色偏差。

- 入口脚本：`.codex/skills/color-palette-generator/scripts/generate_color_palette.py`
- 输出默认目录：`生成结果输出/color_palettes/`

### 与 brand-asset-sheet 的关系

| 工具 | 用途 | 典型场景 |
|---|---|---|
| `brand-asset-sheet` | 品牌识别资产（Logo + 品牌色 + 字体渲染） | 品牌宣传图、含 Logo 的产品图 |
| `color-palette-generator` | 单次生图的精确配色锚定（比例 + 色号） | 任何需要精确控制背景/主体/点缀颜色的生图 |

**同时使用**：brand-asset-sheet 传品牌色约束，color-palette-generator 传当次画面配色比例。

---

## 使用时机

在调用 `rh-image-pro-img2img` / `rh-image-pro-txt2img` **之前**，当以下任一条件成立时先生成色卡：

- 画面颜色有精确要求（背景色值、产品色、点缀色）
- 上一轮生图颜色偏差（偏灰、偏冷、偏暖）需要修正
- M2 配色系统已输出具体色值，需要将色值传入生图
- 多区域画面（如左/中/右三栏），每个区域配色不同
- 任何需要「告诉 AI 哪个区域用什么颜色」的场景

---

## 调用方式

从项目根目录运行（`working_directory` 设为项目根目录）：

```powershell
python ".codex/skills/color-palette-generator/scripts/generate_color_palette.py" `
  --colors "#f5f2ee:暖米色背景:60,#3d1f0a:深棕色产品:30,#f5c800:强调黄色:10" `
  --title "NEBILITY-ShaperShort-Cream" `
  --output "生成结果输出/color_palettes/NEBILITY-cream-palette.png"
```

---

## 参数说明

| 参数 | 必填 | 说明 |
|---|---|---|
| `--colors` | 是 | 颜色列表，格式见下方 |
| `--title` | 否 | 色卡标题，显示在图片顶部，默认 `Color Palette` |
| `--output` | 否 | 输出路径（相对项目根目录），默认 `生成结果输出/color_palettes/<title>-palette.png` |
| `--project-root` | 否 | 项目根目录绝对路径，通常不需要传 |

### `--colors` 格式

```
#hex:颜色角色名称:画面占比, #hex:颜色角色名称:画面占比, ...
```

- **hex**：标准6位色号，带或不带 `#` 均可
- **颜色角色名称**：该颜色在画面中扮演的角色（如 `Background`、`Product Fabric`、`Accent Arrow`）
- **画面占比**：整数，所有颜色之和应约为100。可省略，省略时将剩余比例均分

```bash
# 示例：三色方案
--colors "#f5f2ee:暖米色背景:60,#3d1f0a:深棕色产品:30,#f5c800:强调黄色:10"

# 比例省略示例（两色均分）
--colors "#ffffff:白色背景,#1a1a1a:深色文字"

# 五色方案
--colors "#f0ece6:米白背景:50,#bf192e:品牌红:20,#1a1a1a:近黑色:15,#ffffff:白色:10,#f5c800:金色点缀:5"
```

---

## 输出说明

脚本成功时输出 JSON：

```json
{
  "success": true,
  "saved_path": "F:\\AI设计师助手\\生成结果输出\\color_palettes\\NEBILITY-cream-palette.png",
  "width": 1800,
  "height": 620,
  "colors": [
    {"hex": "#f5f2ee", "name": "Warm Cream Background", "proportion": 60},
    {"hex": "#3d1f0a", "name": "Dark Brown Product",    "proportion": 30},
    {"hex": "#f5c800", "name": "Accent Yellow",         "proportion": 10}
  ],
  "prompt_snippet": "Color palette reference (image N — replace N with actual --images index):\nApply each color exactly as specified by its hex code:\n  - Warm Cream Background: use exactly #f5f2ee ..."
}
```

色卡图包含三个区域：
1. **PROPORTION MAP**：按比例宽度的横向色条，直观呈现各色面积关系
2. **COLOR SWATCHES**：等高独立色块，每块内显示色号，下方标注色号 + 角色名 + 占比
3. **PROMPT COLOR REFERENCE**：底部灰色区，列出每个颜色的 Prompt 引用写法

---

## 完整操作流程

### Step 1：由 M2 或需求分析确定配色方案

确认画面中每个区域的颜色和大致占比：

```
背景（左/中/右面板）：#f5f2ee  约 60%
产品颜色（参考色）：#3d1f0a  约 30%
标注箭头/点缀：#f5c800  约 10%
```

### Step 2：生成色卡图

```powershell
python ".codex/skills/color-palette-generator/scripts/generate_color_palette.py" `
  --colors "#f5f2ee:暖米色背景:60,#3d1f0a:深棕色产品:30,#f5c800:强调黄色:10" `
  --title "NEBILITY-ShaperShort-Cream" `
  --output "生成结果输出/color_palettes/NEBILITY-cream-palette.png"
```

### Step 3：读取色卡图确认效果

用 Read 工具目视确认色卡图正确渲染，同时记录 `prompt_snippet` 字段供 Step 4 使用。

### Step 4：将色卡图加入 `--images`，并在 Prompt 中精准引用

```powershell
python ".codex/skills/rh-image-pro-img2img/scripts/generate_image.py" `
  --images "产品图.jpg" "人物图.jpg" "布局模板.jpg" "生成结果输出/color_palettes/NEBILITY-cream-palette.png" `
  --prompt "... [COLOR PALETTE — from image 4] ... (见下方 Prompt 写法)" `
  --aspect-ratio "21:9" --resolution "2k"
```

---

## Prompt 写法规范（核心）

### ❌ 旧写法（模糊，颜色容易偏差）

```
使用 image 4 中的颜色。匹配 image 4 的暖色调。
```

### ✅ 新写法（精确到色号 + 画面角色）

```
[色卡参考 — 来自 image 4]
image 4 是色卡参考图，精确使用以下颜色：
- 所有背景面板（三个区域）：精确使用 #f5f2ee（暖米色背景，image 4 中面积最大的色块，占画面约 60%）。不是灰色、不是白色——精确是 #f5f2ee。
- 产品/面料颜色参考：#3d1f0a（image 4 中的深棕色产品色）是产品色调的参考——在塑形短裤上完整保留这个颜色。
- 标注箭头及点缀图形：所有方向箭头和高亮元素精确使用 #f5c800（image 4 中的强调黄色）。
画面中不得引入 image 4 以外的其他背景颜色。
```

### 写法要点

1. **明确说明 image N 是色卡参考图**（防止模型误解图片用途）
2. **每个颜色写「精确使用 #hex（角色名，在 image N 中的位置描述）」**
3. **对关键颜色加强：「不是灰色、不是白色——精确是 #f5f2ee」**
4. **结尾加：「画面中不得引入 image N 以外的其他颜色」**

---

## 与 M2 配色系统的协作流程

```
M2 配色系统设计
  → 输出色彩策略（主色/辅色/背景色/点缀色 + 色值）
  ↓
color-palette-generator
  → 根据 M2 输出的色值 + 画面区域占比生成色卡图
  → 输出 prompt_snippet
  ↓
rh-image-pro-img2img
  → 色卡图作为 image N 传入
  → Prompt 使用 "exactly #hex (角色名) from image N" 精准引用
```

---

## 与 design-must-use-main-control 的关系

色卡生成在 **⑥ 构造提示词之前** 执行（与品牌资产生成并列）：

```
⑥.4 色卡生成（凡有精确颜色要求时触发）
  → 由 M2 或需求分析确定色值和占比
  → 调用 color-palette-generator 生成色卡图
  → 色卡图加入 --images，Prompt 中用 "image N + #hex + 角色名" 引用
  → 输出【色卡参考摘要】
```

---

## 常见问题

| 问题 | 原因 | 解决方法 |
|---|---|---|
| 生成图背景色仍然偏灰 | Prompt 中只写了 `from image N` 没有写具体色号 | 改写为 `use exactly #f5f2ee from image N` |
| 色卡图路径含中文导致报错 | 用了 `Get-ChildItem` 等 PowerShell 原生命令 | 确认 `working_directory` 为项目根目录即可，脚本内部用 pathlib 处理 |
| 比例之和不等于100 | 输入时计算失误 | 脚本会自动归一化，或最后一项补足差值 |
| AI 模型颜色仍偏差 | Prompt 描述力度不够 | 在颜色描述后加 `NOT [错误颜色描述] — specifically [正确色号]` |

---

## 注意事项

- **不要硬编码盘符**：路径一律用相对路径（相对项目根目录）
- **色卡图不替代品牌资产图**：两者并用时各占一个 image 编号
- **比例是参考而非绝对**：`60%` 告诉 AI 这个颜色是主导色，不要求像素级精确
- **颜色角色名称要有意义**：`Background`、`Product Fabric`、`Accent Arrow` 比 `Color1` 更能帮助 AI 理解颜色的用途
