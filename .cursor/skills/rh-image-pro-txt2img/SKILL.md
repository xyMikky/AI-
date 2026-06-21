---
name: rh-image-pro-txt2img
description: "调用 RunningHub GPT-image 2 官方文生图 API，纯文本描述生成图像，无需参考图片输入。当前文生图默认首选模型：内部评测综合评分比第二名高出 100+ 分，文字渲染准确，真实感强，适合商业摄影、海报、含文字画面、概念场景和高质感创意探索。支持指定画面比例（1:1/2:3/3:2/3:4/4:3/4:5/5:4/9:16/16:9/21:9）、分辨率（1k/2k/4k）和质量（low/medium/high，默认 medium）。生成图片自动保存到「生成结果输出」目录。关键词：文生图、纯文本生图、Text-to-Image、GPT-image 2、ChatGPT、文字渲染、真实感、商业摄影、RunningHub、AI生图。"
---

# RH GPT-image 2 官方 - 文生图

## 概述

使用 RunningHub `rhart-image-g-2-official/text-to-image` API（**GPT-image 2 官方文生图**），纯文本描述生成图像，**不需要任何参考图片输入**。这是当前文生图默认首选模型：内部评测综合评分比第二名高出 100+ 分，文字渲染准确，真实感强，尤其适合商业摄影、海报、含文字画面和高质感概念场景。直接调用脚本完成：提交任务 → 轮询等待 → 自动下载保存。

- API Key：项目根目录 `config/.env` 中的 `RH_API_KEY`

## ⚡ 提示词语言默认中文

`--prompt` 参数的内容**默认使用中文**，以便用户能直接审核 Prompt。技术锚点按规则保留原样。

需保留原样的技术锚点（禁止翻译）：
- HEX 色号：`#bf192e`
- API 参数：`--aspect-ratio` / `--resolution` / `--label`
- 文件路径、品牌名、Logo 文字
- 标准化英文视觉术语可用"中文 + 英文括注"形式保留，如 `低角度仰拍 (low-angle shot)` / `浅景深 (shallow depth of field)`

完整规范详见 `ai-designer-assistant.mdc`「默认输出语言规范」与 `nano-banana-prompt-guide` skill「语言规范」章节。

---

## 与图生图（img2img）的区别

| 维度 | 文生图（本 skill） | 图生图（rh-image-pro-img2img） |
|------|-------------------|-------------------------------|
| 输入 | 仅文字提示词 | 1-10 张参考图 + 文字提示词 |
| API 端点 | `rhart-image-g-2-official/text-to-image` | `rhart-image-n-pro/edit` |
| 适用场景 | 从零创建、无参考图、纯创意生成 | 基于现有图片编辑/转换/合成 |
| `--images` 参数 | 无 | 必填 |
| 默认比例 | `9:16` | `3:4` |
| 默认质量 | `medium` | N/A |

**选择原则**：
- 有参考图 → 用 `rh-image-pro-img2img`（图生图），效果更可控
- 无参考图 / 纯创意探索 / 用户明确要求"不参考图片" → 用本 skill（GPT-image 2 文生图）
- 文生图任务中需要文字渲染、真实商业摄影质感、海报级画面时，本 skill 作为默认首选。

---

## 使用场景

### 概念创作
- **创意插画**：根据文字描述生成全新插画风格作品
- **概念场景**：构建从未存在的虚拟场景、幻想世界
- **风格探索**：快速测试不同视觉风格方向

### 品牌视觉
- **品牌元素生成**：纹理、图案、背景素材
- **氛围图**：情绪板（Mood Board）素材生成
- **社交媒体内容**：无需素材的快速内容创作

### 辅助设计
- **初始草图**：设计项目的视觉起点
- **背景素材**：纯场景/纹理/材质背景
- **占位图**：设计稿中的临时视觉填充

---

## 工作流程

### 步骤 1：构造提示词

文生图的提示词比图生图需要**更详细**，因为没有参考图片作为视觉锚定。推荐包含：

```
【主体描述】+ 【风格/媒介】+ 【色彩方案】+ 【构图/比例】+ 【光线/氛围】+ 【排除项】
```

提示词越精确，生成结果越可控。参照 `nano-banana-prompt-guide` skill 获取最佳实践。

### 步骤 2：确认参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--prompt` | 是 | 图像描述提示词（默认中文，技术锚点保留英文原样） |
| `--aspect-ratio` | 否 | 默认 `9:16`；可选：`1:1` `9:16` `16:9` `4:3` `3:4` `3:2` `2:3` `5:4` `4:5` `21:9` |
| `--resolution` | 否 | 默认 `2k`；可选：`1k` `2k` `4k` |
| `--quality` | 否 | 默认 `medium`；可选：`low` `medium` `high` |
| `--label` | 否 | 输出文件名前缀 |

**比例速查**：`9:16` 竖版海报/手机壁纸 · `1:1` 方形展示 · `16:9` Banner/横版 · `3:4` 产品图

### 步骤 3：调用脚本

```bash
python "G:\AI设计师助手\.cursor\skills\rh-image-pro-txt2img\scripts\generate_image_t2i.py" --prompt "提示词" --aspect-ratio "9:16" --resolution "2k" --quality "medium" --label "任务标签"
```

### 步骤 4：解读输出

脚本向 stdout 输出 JSON，向 stderr 输出实时进度。

**成功：**
```json
{
  "success": true,
  "task_id": "xxx",
  "saved_paths": ["G:\\AI设计师助手\\生成结果输出\\20260329\\标签_时间戳_1.jpg"],
  "result_urls": ["https://..."],
  "save_dir": "G:\\AI设计师助手\\生成结果输出\\20260329"
}
```

**失败：**
```json
{ "success": false, "error": "未配置 RH_API_KEY！请编辑 config/.env" }
```

### 步骤 5：反馈结果

- 告知用户 `saved_paths` 中的本地路径
- 如需在 Cursor 中预览：`![预览](文件路径)`

---

## 典型示例

### 示例 1：日式极简可爱插画

```bash
python "G:\AI设计师助手\.cursor\skills\rh-image-pro-txt2img\scripts\generate_image_t2i.py" --prompt "日式极简可爱手绘插画，暖米色纯色背景。一个可爱的简化达摩娃娃，厚实笔触，砖红色平涂，白色面孔搭配小点眼睛和圆形鼻子。下方配有匹配红色的汉字。超极简涂鸦风格，仅用3种颜色：米色、砖红色、黑色。无渐变，无阴影，大量留白。" --aspect-ratio "9:16" --resolution "1k" --label "kawaii-daruma"
```

### 示例 2：抽象品牌纹理

```bash
python "G:\AI设计师助手\.cursor\skills\rh-image-pro-txt2img\scripts\generate_image_t2i.py" --prompt "抽象有机纹理图案，深海军蓝配金属金色点缀，流动的大理石液态效果，奢华现代美学，无缝平铺图案，高分辨率细节，深沉神秘氛围。" --aspect-ratio "1:1" --resolution "2k" --label "brand-texture"
```

### 示例 3：概念场景

```bash
python "G:\AI设计师助手\.cursor\skills\rh-image-pro-txt2img\scripts\generate_image_t2i.py" --prompt "黄金时段宁静的日本禅意庭院，耙砂纹路，苔藓覆盖的石块，单株盛开的樱花树，柔和温暖光线穿透花瓣，极简构图留有充足负空间，低饱和大地色系，写实风格。" --aspect-ratio "16:9" --resolution "1k" --label "zen-garden"
```

### 示例 4：电商背景素材

```bash
python "G:\AI设计师助手\.cursor\skills\rh-image-pro-txt2img\scripts\generate_image_t2i.py" --prompt "干净现代的产品摄影背景，暖白色到浅米色柔和渐变，轻微织物纹理叠加，专业棚拍柔光，底部轻微阴影，中央留出产品放置空间，商业级品质。" --aspect-ratio "1:1" --resolution "1k" --label "product-bg"
```

---

## 提示词写作要点（文生图专用）

文生图没有参考图片锚定，提示词质量直接决定输出质量。关键要点：

1. **具体胜于抽象**：「砖红色平涂」优于「红色」；「厚实笔触涂鸦风格」优于「手绘」
2. **指定风格/媒介**：「水彩插画」「3D CGI 渲染」「扁平矢量图形」「油画」
3. **色彩方案明确**：列出具体颜色，如「暖米色背景 + 砖红色 + 黑色墨水，最多 3 种颜色」
4. **正向表述排除项**：「纯色背景」「无文字」「无水印」「无渐变阴影」
5. **构图指引**：「居中构图」「三分法则」「大量留白」「特写裁切」
6. **九宫格防护**：单张图的 Prompt 中不出现九宫格、拼图、网格、系列数量等描述，避免触发拼贴输出

---

## 注意事项

- **API Key**：编辑 `G:\AI设计师助手\config\.env`，设置 `RH_API_KEY=你的密钥`（与图生图共用同一个 Key）
- **默认分辨率为 `2k`**，除非用户明确指定 `4k`（升级）或 `1k`/`快速`（降级），否则一律使用 `--resolution 2k`
- **运行时间**：通常 30-120 秒，最长 600 秒
- **提示词语言**：默认使用中文（技术锚点保留英文原样：HEX 色号、`--aspect-ratio` 等参数）
- **无参考图锚定**：输出可控性低于图生图，建议用更详细的提示词补偿
- **与图生图配合**：先用文生图探索方向 → 选出满意的结果 → 作为参考图传入图生图迭代精修

---

## 相关资源

- **提示词规范**：`nano-banana-prompt-guide` skill
- **图生图工具**：`rh-image-pro-img2img` skill（需要参考图时使用）
- **API Key 配置**：`G:\AI设计师助手\config\.env`
- **图片输出目录**：`G:\AI设计师助手\生成结果输出\`
