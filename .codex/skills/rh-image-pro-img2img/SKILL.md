---
name: rh-image-pro-img2img
description: "当前项目默认图生图执行 Skill。凡用户在本项目中要求编辑图片、基于参考图生成、改图、换背景、换装、改内饰、产品图重绘、风格转换、模特场景图、电商主图、测试项目生图能力，必须优先使用本 Skill 执行 RunningHub 图生图 API，而不是系统 imagegen。调用前应先经过 project-image-generation-router、ai-image-prompt-builder 和 ai-image-logic-checker Pre-Gen。默认使用 pro 模型（Nano Banana Pro / Gemini 3 Pro Image，细节精准，最多 10 图）；--model flash 切换到 Banana2 Flash 作为批量创意/pro 繁忙备用；实验性 gpt-image-2 仅当用户显式点名时使用。生成图片自动保存到「生成结果输出」目录。关键词：项目生图、项目Skill生图、图生图、改图、参考图生成、换背景、换装、改内饰、风格转换、电商产品图、RunningHub、AI生图、不要系统imagegen。"
---

# RH 图生图 · 多模型

## 概述

统一入口的图生图脚本：上传参考图 → 提交任务 → 轮询等待 → 自动下载保存。无需 ComfyUI，直接命令行调用。

- API Key：项目根目录 `config/.env` 中的 `RH_API_KEY`
- 提示词规范：参照 `nano-banana-prompt-guide` skill

## 强制上游门禁

本 Skill 是执行层，不负责自行编写最终 Prompt。调用本 Skill 前必须已经经过：

`project-image-generation-router` -> `ai-image-prompt-builder` -> `ai-image-logic-checker Pre-Gen`

必须存在来自 `ai-image-prompt-builder` 的交接卡：

```text
[Project Image Prompt Handoff]
source_skill: ai-image-prompt-builder
task_type: img2img
input_images: image 1 = <path or role>
final_prompt: <prompt to pass to RunningHub>
aspect_ratio: <ratio>
resolution: <1k|2k|4k>
model: pro | flash | gpt-image-2
pre_gen_notes: <logic/color/reference constraints for ai-image-logic-checker>
```

如果缺少该交接卡，停止执行并先调用 `ai-image-prompt-builder`。不要在本 Skill 内临时手写最终 Prompt。

## 对话可见 Prompt 门禁

调用脚本前必须确认当前对话输出页面已经展示完整【本次生图提示词】交接卡，至少包含 `final_prompt`、`input_images`、`aspect_ratio`、`resolution`、`model` 和 `pre_gen_notes`。

如果 Prompt 只出现在 `--prompt` 参数、shell 命令、Python 代码、JSON 输出或 prompt 文件中，而没有展示给用户，则停止执行，先把交接卡输出到当前对话页面，再继续调用脚本。

执行完成后，反馈结果时也要保留本次使用的 Prompt 摘要或完整 Prompt，方便用户复盘。

## 图生图保留锚点门禁

调用脚本前必须确认 `final_prompt` 已使用引用式保留锚点，而不是只重新描述参考图内容。

合格格式示例：

```text
除蓝色光效外，保持 image 1 中所有内容完全一致：整体构图、拍摄角度、透视、比例、主体结构、材质、光影、背景和未指定元素均保持原样。仅移除蓝色发光、蓝色能量线和蓝色反射。
```

如果 `final_prompt` 只列举“保持手机、支架、背景……”但没有“除变更对象外保持 image 1 中所有内容完全一致”的总保留锚点，停止执行并退回 `ai-image-prompt-builder` 修正。

## ⚡ 提示词语言默认中文

`--prompt` 参数的内容**默认使用中文**，以便用户能直接审核 Prompt。以下技术锚点必须保留原样（禁止翻译）：

- 参考图编号：`image 1` / `image 2` / `image N`
- HEX 色号：`#bf192e`
- API 参数：`--images` / `--aspect-ratio` / `--resolution` / `--label`
- 文件路径、品牌名、Logo 文字
- 色彩硬约束词：`BACKGROUND ONLY` / `PRODUCT ONLY` / `DECORATIVE ELEMENTS ONLY` / `TEXT ONLY`
- 标准化英文视觉术语可用"中文 + 英文括注"形式保留，如 `低角度仰拍 (low-angle shot)`

完整规范详见 `ai-designer-assistant.mdc`「默认输出语言规范」与 `nano-banana-prompt-guide` skill「语言规范」章节。

## 可用模型对照

| key (--model) | 状态 | 端点（endpoint） | 底层模型 / 定位 | 最多图数 | aspectRatio | resolution | base_url |
|---------------|------|------------------|-----------------|---------|-------------|-----------|----------|
| `pro` (默认) | **稳定** | `rhart-image-n-pro/edit` | **Nano Banana Pro / Gemini 3 Pro Image**，细节还原精准，产品精修/最终出图首选 | 10 | 10 档枚举，payload 字段 | 1k/2k/4k | www.runninghub.cn |
| `flash` | 稳定 | `rhart-image-n-g31-flash/image-to-image` | **Banana2 Flash**，价格更低、特征保留强，批量创意或 pro 繁忙备用 | 10 | 10 档枚举，payload 字段 | 1k/2k/4k | www.runninghub.cn |
| `gpt-image-2` | ⚠ **实验性** | `rhart-image-g-2/image-to-image` | **GPT-image 2（ChatGPT 系）**，文字渲染/真实感倾向更强，但 API 功能不完善、稳定性待验证 | **2** | **不发 payload**，写进 prompt 文字 | ✗（传入忽略） | **rhtv.runninghub.cn** |

### 选型指南（何时用哪个模型）

**默认策略：永远用 `pro`（无需加 `--model`）。** 除非命中下方显式例外，否则 AI 不得主动切换模型。

| 触发条件 | 使用模型 |
|---------|---------|
| 默认所有图生图任务 | `pro` |
| 用户明确说"用 flash / 批量快出草图 / pro 繁忙报 1011 需备用" | `flash` |
| **用户明确点名要求使用 `gpt-image-2` / GPT / ChatGPT 图生图 / 实验性模型**，或明确说"Nano Banana 文字跑崩了换 GPT 试试" | `gpt-image-2` |

> **重要：`gpt-image-2` 是实验性模型，AI 不要基于"场景适合文字/真实感"等推断来主动替换。**
> 即使遇到产品说明书、带文字电商图、写实人像这类看似对口的任务，也**继续用 `pro`**；只有用户口头或文字中显式指定 gpt-image-2 / GPT / ChatGPT 模型时才切换。

### gpt-image-2 的比例写法

官方 `aspectRatio` 枚举仅 `2:3 / 1:1 / 3:2`，本脚本不把该字段写入 payload；改由 prompt 文字传达比例，实测模型对 `21:9` / `9:16` 等非枚举比例也能响应。在 prompt 里直接写 `aspect ratio 21:9` 或 `比例 21:9`，或后缀 `, 21:9 horizontal banner` / `, 9:16 vertical poster` 即可。

---

## 使用场景

### 背景操作
- **换白底 / 纯色背景**：上传原图，生成标准电商白底产品图
- **室内换室外**：咖啡馆/工作室背景 → 公园/街道/海边等室外场景
- **任意场景替换**：替换背景为任何指定场景，保持主体不变

### 风格转换
- **3D 卡通化**：真实照片 → Pixar/迪士尼卡通风格
- **油画 / 水彩 / 插画**：转换为各种艺术风格
- **日式动漫风**：转换为 Manga/Anime 风格
- **商业摄影风**：提升为专业摄影棚质感

### 人物 / 模特
- **换装**：保持模特外貌，更换服装
- **场景替换**：同一模特置于不同背景环境
- **系列图人物一致性**：生成多张姿势/角度不同但外貌一致的系列图

### 产品 / 电商
- **白底产品图**：纯白背景、专业布光
- **生活场景图**：产品置于真实生活场景
- **产品细节特写**：纹理/材质极近距离展示
- **多角度展示图**：同款产品不同拍摄角度

### 物体操作
- **添加元素**：向图片中添加道具、装饰等
- **移除元素**：去除不需要的背景物体并自然填充
- **替换元素**：替换场景中的特定物体

### 光线与氛围
- **时间氛围切换**：正午 / 黄金时段 / 蓝调时刻
- **光线方向调整**：侧光 / 逆光 / 顶光
- **添加戏剧性光效**：棚拍灯光效果

### 文字图片
- **营销 Banner**：图片内嵌品牌文字、促销信息
- **多语言素材**：中英双语文字图片

---

## 使用参考库图片作为参考

参考库 `原始素材/` 目录中保存了经过 M10 分析标注的高质量参考图。在生图时**应主动检索并引用**这些图片作为视觉参考输入，让生成结果更贴合项目的既定审美方向，而非仅依赖文字描述。

### 检索逻辑（推荐流程）

**方式一：从参考记录的来源字段提取（精准，推荐）**

M8 在 Step 2.5 中从选中的参考记录的「来源」字段提取归档文件名，拼接为完整路径：

```
来源字段示例：
  来源：M10自主学习 · E-004-促销Banner-生活场景产品浮层-US-EC-20260323.jpeg（Popilush · BOGO）
                       ↓ 提取文件名
  归档文件名：E-004-促销Banner-生活场景产品浮层-US-EC-20260323.jpeg
                       ↓ 拼接路径
  完整路径：参考库/E_平面与海报/原始素材/E-004-促销Banner-生活场景产品浮层-US-EC-20260323.jpeg
```

路径拼接规则：

| 文件名前缀 | 原始素材目录 |
|-----------|-------------|
| `E-` | `参考库/E_平面与海报/原始素材/` |
| `F-` | `参考库/F_摄影风格/原始素材/` |
| `G-` | `参考库/G_插画与图形/原始素材/` |
| `C-` | `参考库/C_排版字体/原始素材/` |
| `H-` | `参考库/H_3D与渲染/原始素材/` |
| `D-` | `参考库/D_UI界面/原始素材/` |
| `J-` | `参考库/J_空间与产品/原始素材/` |

**方式二：按借鉴维度目录检索（浏览式）**

当没有明确的参考记录时，根据借鉴维度在对应域的原始素材目录中浏览：

| 需要借鉴的维度 | 优先检索目录 |
|---------------|-------------|
| 构图 / 版式 / 信息层级 | `参考库/E_平面与海报/原始素材/` |
| 色彩搭配 / 色调 | `参考库/B_配色系统/原始素材/` |
| 摄影光线 / 氛围 | `参考库/F_摄影风格/原始素材/` |
| 插画 / 图形风格 | `参考库/G_插画与图形/原始素材/` |
| 3D 质感 / 渲染 | `参考库/H_3D与渲染/原始素材/` |
| UI 界面风格 | `参考库/D_UI界面/原始素材/` |
| 品牌 / Logo 风格 | `参考库/A_品牌与Logo/原始素材/` |
| 产品 / 工业设计 | `参考库/J_空间与产品/原始素材/` |

### 多参考图传参方式

```bash
python "G:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\generate_image.py" \
  --images "主素材图路径" "参考库参考图路径1" "参考库参考图路径2" \
  --prompt "（含 image 1/2/3 差异化引用的提示词，见 nano-banana-prompt-guide 场景八）" \
  --aspect-ratio "9:16" --resolution "1k" --label "任务标签"
```

> 图片按 `--images` 传入顺序编号：`image 1`（第一张）、`image 2`（第二张）……Prompt 中**必须**通过编号指定从哪张图借鉴什么，不指定会导致模型随机混合多图特征。

### 快速示例：借鉴参考库图片的色调

```bash
python "G:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\generate_image.py" \
  --images "产品原图.jpg" "参考库/F_摄影风格/原始素材/F-005-低饱和柔光人像-胶片色调背景-20260323.jpg" \
  --prompt "产品与 image 1 中完全一致，外观保持原样。借鉴 image 2 的色调和光线氛围——使用同样的低饱和胶片色调和柔和自然光质感。干净白色背景，专业商业摄影风格。" \
  --aspect-ratio "1:1" --resolution "1k" --label "胶片风产品图"
```

### 快速示例：借鉴参考库图片的构图版式

```bash
python "G:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\generate_image.py" \
  --images "产品图.jpg" "参考库/E_平面与海报/原始素材/E-004-促销Banner-生活场景产品浮层-US-EC-20260323.jpeg" "参考库/F_摄影风格/原始素材/F-009-Popilush-低饱和柔光人像-US-DTC-20260323.jpg" \
  --prompt "使用高细节推理确保准确性：产品与 image 1 中完全一致，外观保持原样。借鉴 image 2 的构图版式——具体参考生活场景背景作为氛围层、产品浮层及胶囊标签标注风格。借鉴 image 3 的色调——使用同样的柔和低饱和色调和漫射自然光。专业商业摄影风格。" \
  --aspect-ratio "9:16" --resolution "1k" --label "参考版式产品图"
```

---

## 工作流程

### 步骤 1：构造提示词

按照 `nano-banana-prompt-guide` skill 中的模板构造提示词。**图片编辑基本公式**：

```
【编辑动作】+ 【目标效果】+ 【保留内容（引用参考图，不重新描述）】
```

> 核心原则：想保留的元素用“除变更对象外，保持 image N 中所有内容完全一致”或 `keep ... exactly as shown in the reference image` 引用，**不要重新用文字描述**。

### 步骤 2：确认参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--images` | 是 | 参考图路径（pro/flash: 1-10 张；**gpt-image-2: 1-2 张，每张 ≤10MB**；JPG/PNG） |
| `--prompt` | 二选一 | 直接传入提示词字符串（5-800 字符）。⚠️ PowerShell 中 `$` 会被展开为变量，含 `$` 时请改用 `--prompt-file` |
| `--prompt-file` | 二选一 | **推荐**：从 UTF-8 文本文件读取提示词，彻底避免特殊字符转义问题（见下方防坑指南） |
| `--model` | 否 | 默认 `pro`；可选：`pro` / `flash` / `gpt-image-2`（选型指南见上方对照表） |
| `--aspect-ratio` | 否 | 默认 `3:4`；可选：`1:1` `9:16` `16:9` `4:3` `3:4` `3:2` `2:3` `5:4` `4:5` `21:9`。**gpt-image-2 不接受该字段，传入会被忽略**，请改在 prompt 里用文字写明比例 |
| `--resolution` | 否 | 默认 `2k`；可选：`1k` `2k` `4k`（**gpt-image-2 不支持，传入会被忽略**） |
| `--label` | 否 | 输出文件名前缀 |

**比例速查**：`9:16` 竖版电商/小红书 · `1:1` 方形展示 · `16:9` Banner · `3:4` 传统产品图


---

## ⚠️ PowerShell 特殊字符防坑指南

### 问题根源

PowerShell 在双引号字符串 `"..."` 中会将 `$变量名` 展开为变量值。变量不存在时展开为**空字符串**，导致提示词内容被悄悄删除：

```
# 错误示例：$22 被展开为空字符串，"$22.99" 变成 ".99"
--prompt "AS LOW AS $22.99"

# 错误示例：$bf192e 被展开为空，颜色信息丢失
--prompt "use exactly $bf192e (Brand Red)"
```

常见受影响字符：

| 字符 | PowerShell 行为 | 典型受害场景 |
|------|----------------|-------------|
| `$` 后跟字母/数字 | 展开为同名变量（不存在则变空字符串） | 价格 `$22.99`、颜色 `$accent` |
| `` ` `` | 被识别为转义符前缀 | Prompt 内含反引号 |

### 解决方案一：`--prompt-file`（强烈推荐，彻底解决）

将 Prompt 写入文件，用文件路径代替字符串传参。**AI 调用此 skill 时，凡 Prompt 含 `$`、`%`、`@` 等特殊字符，必须使用此方案。**

```powershell
# Step 1：AI 用 Write 工具将 Prompt 写入文件（内容无需任何转义）
# 文件内容可直接写 $22.99、#bf192e 等，完全不受 Shell 影响

# Step 2：传文件路径（支持相对于项目根目录的路径）
python ".codex/skills/rh-image-pro-img2img/scripts/generate_image.py" `
  --images "产品图.jpg" "参考图.jpg" `
  --prompt-file "生成结果输出/prompts/NEBILITY-promo-prompt.txt" `
  --aspect-ratio "4:5" --resolution "2k" --label "任务名"
```

**优势**：价格/颜色/百分号/换行/引号等所有特殊字符完全无需处理；Prompt 可随时用 Read 工具检查；不受命令行长度限制。

### 解决方案二：PowerShell 转义（Prompt 极短且 `$` 很少时可用）

```powershell
# 方法 A：反引号转义 $（双引号字符串，支持反引号续行）
--prompt "AS LOW AS ``$22.99"

# 方法 B：单引号字符串（不展开变量，但不支持反引号续行）
--prompt 'AS LOW AS $22.99, use #bf192e'
```

> 单引号字符串不支持 PowerShell 反引号行续，长 Prompt 须写成一行。**含 `$` 的长 Prompt 请用 `--prompt-file`。**

### AI 调用规范（强制）

```
凡 Prompt 含 $ % 等特殊字符：
  1. Write 工具 -> 创建 Prompt 文件（生成结果输出/prompts/<任务名>.txt）
  2. Shell 工具 -> --prompt-file 传文件路径（不用 --prompt）
凡 Prompt 纯英文无特殊字符：
  -> 可直接 --prompt '...'（优先单引号以防万一）
```


### 步骤 3：调用脚本

**单张参考图（Prompt 无特殊字符）：**

```powershell
python ".codex/skills/rh-image-pro-img2img/scripts/generate_image.py" `
  --images "图片路径" `
  --prompt '提示词' `
  --aspect-ratio "9:16" --resolution "1k" --label "任务标签"
```

**含 `$` 等特殊字符的 Prompt（用 --prompt-file，推荐）：**

```powershell
# Step 1：Write 工具将 Prompt 写入文件（可含 $22.99 等任意字符，无需转义）
# Step 2：传文件路径
python ".codex/skills/rh-image-pro-img2img/scripts/generate_image.py" `
  --images "产品图.jpg" "参考图.jpg" `
  --prompt-file "生成结果输出/prompts/my-prompt.txt" `
  --aspect-ratio "4:5" --resolution "2k" --label "任务名"
```

**多张参考图（最多 10 张）：**

```powershell
python ".codex/skills/rh-image-pro-img2img/scripts/generate_image.py" `
  --images "路径1" "路径2" `
  --prompt '提示词' `
  --aspect-ratio "1:1" --resolution "2k"
```

### 步骤 4：解读输出

脚本向 stdout 输出 JSON，向 stderr 输出实时进度。

**成功：**
```json
{
  "success": true,
  "task_id": "xxx",
  "saved_paths": ["G:\\AI设计师助手\\生成结果输出\\20260323\\标签_时间戳_1.jpg"],
  "result_urls": ["https://..."],
  "save_dir": "G:\\AI设计师助手\\生成结果输出\\20260323"
}
```

**失败：**
```json
{ "success": false, "error": "未配置 RH_API_KEY！请编辑 config/.env" }
```

### 步骤 5：反馈结果

- 告知用户 `saved_paths` 中的本地路径
- 如需在 Codex 中预览：`![预览](文件路径)`

---

## 典型示例

### 示例 1：室内换室外背景

```bash
python "G:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\generate_image.py" --images "参考图.jpg" --prompt "主体与 image 1 中完全一致，外观保持原样。仅替换背景为户外公园场景，柔和自然阳光、绿树、黄金时段光线。边缘融合自然，光线方向前后一致。" --aspect-ratio "9:16" --resolution "1k" --label "室外背景"
```

### 示例 2：电商白底图

```bash
python "G:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\generate_image.py" --images "产品图.jpg" --prompt "专业产品照片，纯白色背景，柔和均匀的棚拍光线，底部有轻微落地阴影。产品与 image 1 中完全一致，外观保持原样。无文字叠加，无水印。" --aspect-ratio "1:1" --resolution "2k" --label "白底图"
```

### 示例 3：模特换装

```bash
python "G:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\generate_image.py" --images "模特图.jpg" --prompt "女性模特穿着优雅黑色深V晚礼裙，奢华时尚摄影风格，棚拍光线。保持与 image 1 中相同的面部特征、发色及身体比例。白色背景。" --aspect-ratio "9:16" --resolution "2k" --label "黑色礼裙"
```

### 示例 4：3D 卡通化风格转换

```bash
python "G:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\generate_image.py" --images "原图.jpg" --prompt "将这张图片转换为 3D 卡通动画风格，色彩鲜艳，表面平滑，构图和主体位置与原图保持一致。皮克斯动画美学，高质量渲染。" --aspect-ratio "1:1" --resolution "1k" --label "3D卡通"
```

### 示例 5：系列图人物一致性

```bash
python "G:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\generate_image.py" --images "人物参考图.jpg" --prompt "使用高细节推理确保准确性：[姿势描述]，面部特征、发色及身体比例与 image 1 保持一致，服装与 image 1 完全相同、保持不变。[背景描述]，专业摄影光线。无文字叠加。" --aspect-ratio "9:16" --resolution "2k" --label "系列图姿势1"
```

### 示例 6：GPT-image 2 加 Logo + 生成产品说明书（⚠ 实验性，仅用户显式要求时使用）

> **AI 注意**：仅当用户**明确点名** `gpt-image-2` / GPT / ChatGPT 模型时才走这条分支。常规图生图任务（包括带文字/写实感类）一律默认用 `pro`。

**关键点**：
- 最多 2 张参考图；
- **不传** `--aspect-ratio` / `--resolution`（当前版本都不生效）；
- **比例在 prompt 里用文字说明**（`比例为 21:9` / `aspect ratio 21:9` / `21:9 horizontal banner` 都可以）。

```powershell
python ".codex/skills/rh-image-pro-img2img/scripts/generate_image.py" `
  --model "gpt-image-2" `
  --images "产品原图.jpg" `
  --prompt "在马克杯的正中央，添加一个精致的几何风格狐狸 Logo，Logo 下方清晰地印着文字 ""Wild Fox""。请保持原图的光影结构和陶瓷质感完全不变。然后生成一张产品介绍说明书，比例为 21:9（横版 banner 版式）。" `
  --label "WildFox产品说明书"
```

### 示例 7：GPT-image 2 写实人像换装（⚠ 实验性，仅用户显式要求时使用）

比例同样写进 prompt-file 的文本里（例如结尾加一句 `Render as a 9:16 vertical portrait poster.`）：

```powershell
python ".codex/skills/rh-image-pro-img2img/scripts/generate_image.py" `
  --model "gpt-image-2" `
  --images "模特原图.jpg" "服装参考.jpg" `
  --prompt-file "生成结果输出/prompts/realistic-portrait-prompt.txt" `
  --label "写实人像"
```

---

## 使用字体渲染图作为参考（精确字体控制）

当用户在 C 域收藏了字体文件时，可通过同目录下的 `render_font_text.py` 先将文字渲染为图片，再作为 image N 传入本脚本，让 AI 参考精确的字体样式。

### 渲染字体文字图

```bash
python "f:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\render_font_text.py" \
  --font "参考库/C_排版字体/字体文件/Futura-Bold.otf" \
  --text "Tummy Control Shapewear" \
  --size 120 --color "#1A1A1A" --bg "transparent" \
  --letter-spacing 5 --align center \
  --output "生成结果输出/font_renders/headline.png"
```

### 模式 A：首次生图时注入字体

```bash
python "f:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\generate_image.py" \
  --images "产品图.jpg" "生成结果输出/font_renders/headline.png" \
  --prompt "产品与 image 1 中完全一致，外观保持原样。文字样式与 image 2 完全相同——精确复制字体风格、字母形状、字重和字间距。将文字置于顶部居中位置，使用 image 2 中的字体，不得替换为其他字体。" \
  --aspect-ratio "3:4" --resolution "1k" --label "字体注入测试"
```

### 模式 B：二次替换文字

```bash
python "f:\AI设计师助手\.codex\skills\rh-image-pro-img2img\scripts\generate_image.py" \
  --images "第一轮生成结果.jpg" "生成结果输出/font_renders/headline.png" \
  --prompt "image 1 中的所有内容保持完全不变。仅将文字区域替换为 image 2 中所示的文字样式。文字位置与 image 1 保持一致，字体样式与 image 2 完全相同，自然融合进画面。" \
  --aspect-ratio "3:4" --resolution "1k" --label "字体替换"
```

### --images 编号约定（含字体渲染图时）

| 编号 | 角色 | 说明 |
|------|------|------|
| image 1 | 用户主素材/产品图 | 保留主体 |
| image 2 | 字体渲染文字图 | 精确字体样式来源 |
| image 3 | 参考库风格参考图（如有） | 借鉴色调/构图/氛围 |

不需要字体注入时，保持现有编号规则不变。

> 详细 Prompt 模板见 `nano-banana-prompt-guide` 场景十一。

---

## 注意事项

- **API Key**：编辑 `G:\AI设计师助手\config\.env`，设置 `RH_API_KEY=你的密钥`
- **图片路径**：支持绝对路径；相对路径以 `G:\AI设计师助手` 为基准
- **保留元素**：不要重新用文字描述想保留的内容。图生图必须先写「除变更对象外，保持 image N 中所有内容完全一致」的总保留锚点；细节枚举只能作为补充
- **九宫格陷阱**：单张图的 prompt 中不能出现九宫格、拼图、网格、系列数量等描述，会导致单张图变成拼贴图；解决方法是彻底不写这类描述，而不是加禁止语
- **运行时间**：通常 30-120 秒，最长 600 秒
- **提示词语言**：默认使用中文（技术锚点保留英文原样：`image N`、HEX 色号、`--aspect-ratio` 等）

---

## 相关资源

- **提示词规范**：`nano-banana-prompt-guide` skill（同目录）
- **API Key 配置**：`G:\AI设计师助手\config\.env`
- **图片输出目录**：`G:\AI设计师助手\生成结果输出\`
- **模型文档**：`g:\1.20\111\AAA-Gemini图片编辑模型使用说明（Nano Banana）.md`
- **RunningHub 官网**：https://www.runninghub.cn
