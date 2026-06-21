---
name: ai-image-prompt-builder
description: AI 生图任务的统一业务入口——构造可直接喂给 rh-image-pro-img2img / txt2img 的高质量 Prompt（默认中文主体 + 技术锚点保留原样）。融合原 M8 视觉简报生成器 + 3 条核心 Rule（迭代多轮生图 / 模特动作设计 / 人物场景库优先调用）。覆盖：参考精炼摘要 B 提炼（向量检索 Vector-First）、姿势设计七要素（重心/手臂/朝向/头角度/动态感/透视/表情）、场景互动（T1-T6 互动类型谱 + SI 系列动作库 + SCENE-5 五要素）、人物库/场景库优先调用、迭代多轮生图（Pass 1a/1b 并发 → Pass 2 → Pass 3）。**是 AI 静态生图唯一入口**，**视频走 video-prompt-designer**，**详情页走 detail-page-designer**（最终调用本 Skill）。下游强制对接 ai-image-logic-checker（M16 Pre-Gen → 生图 → Post-Gen）。适用：海报、Banner、电商主图、社媒图、模特场景图、白底产品图、纯产品图、纯换背景、换装、风格转换、首帧静态图。关键词：生成 Prompt、AI 生图、图生图、文生图、海报、Banner、模特图、电商主图、换背景、换装、风格转换、Midjourney、Flux、Nano Banana、Gemini、姿势设计、场景互动、迭代生图。
---

# AI 生图 Prompt 构造（AI Image Prompt Builder）

## 概述

AI 静态生图任务的**统一业务入口**。构造可直接喂给 RunningHub Pro / Nano Banana / Gemini 的中文为主、技术锚点保留的 Prompt。前身是能力模块 M8_视觉简报生成器，并融合三条核心 Rule（迭代生图 / 模特姿势 / 人物场景库优先）。

## 唯一入口边界

| 任务类型 | 主入口 |
|---|---|
| AI 静态生图（海报/Banner/产品图/模特图） | **ai-image-prompt-builder**（本 Skill） |
| AI 视频生图 | `video-prompt-designer`（视频专属，可调用本 Skill 出首帧） |
| AI 详情页（多模块批量） | `detail-page-designer`（内部调用本 Skill） |
| 非 AI 设计稿 | 不进本 Skill |

## 工作流程

```
读取上游交接卡（A/D/E/F · 来自 M11/M2/M3/M5）
  ↓
①  品牌约束提炼（如品牌激活）
  ↓
①.5 维度分析 & 迭代判定 ← 来自原 iterative-image-generation Rule
   D1 姿势 / D2 背景 / D3 文字 / D4 风格 / D5 换装 / D6 构图
   ≥ 3 维度变更 或 D1+D2 同改 → 启用迭代多轮（输出【迭代生图计划】）
  ↓
②  参考精炼摘要 B 提炼（Vector-First · 强制）
   python 工具/向量检索/search.py "[query]" --rewrite --rerank --top 5 --json --full
   按 score ≥ 0.55 筛选 2-3 条；P 域复用查询；X 域反向陷阱清单
  ↓
③  姿势设计前置 ← 来自原 model-pose-design Rule
   含人物时七要素至少 5 项（重心/手臂/朝向/头角度/动态感/透视/表情）
   推荐姿势库 P1-P7 + 背面 B1-B3 + 场景互动 SI-1~SI-26
  ↓
④  人物库/场景库优先 ← 来自原 person-scene-library-first Rule
   先 Read 人物库索引 / 场景库索引，按文件名标签筛选
   库内匹配 → 用作 image N；无匹配 → 降级 Prompt 文字生成（告知用户）
  ↓
⑤  色卡参考门 + 版式分析门（如触发）
   ⑥.6 色卡（明确色号 / 多色区域 / 模板占位灰）→ 调用 color-palette-generator
   ⑥.9 版式（用户提供版式长图 + 多模块任务）→ 调用 layout-reference-analyzer
  ↓
⑥  品牌资产合成图（如品牌激活，默认字体+色卡，不含 Logo）
   调用 brand-asset-sheet skill 生成
  ↓
⑦  构造 Prompt（默认中文 + 技术锚点）
   写入：[BRAND TONE] / [COLOR PALETTE] / [SCENE REFERENCE] / [MODEL & PRODUCT]
        / [SCENE INTERACTION] / [CAMERA & FOCUS] / [POSE] / [TEXT AREA] / [FRAMING]
   每张 image N 必须有引用 + 借鉴维度
   产品色独立性句式 A + 色彩角色隔离句式 B + 特写防牵引句式 C（如适用）
  ↓
⑧  ai-image-logic-checker Pre-Gen 12 项强制门 → 通过 / 修正
  ↓
⑨  调用 rh-image-pro-img2img / txt2img（按是否含参考图）
   迭代模式：Pass 1a/1b 并发（batch-image-concurrent 规范） → Pass 2 → Pass 3
  ↓
⑩  ai-image-logic-checker Post-Gen V1-V9 + Q1-Q5 评分
  ↓
⑪  ai-image-aesthetic-scorer 双轴评估 → 通过 / 迭代
```

## 核心知识包（融合自 3 条原 Rule）

### A. 迭代多轮生图（原 iterative-image-generation.mdc）

- **维度判定**：D1-D6 中 ≥3 维或 D1+D2 同改 → 强制迭代
- **拆解模式**：A 姿势优先 / B 背景优先 / C 元素分层 / D 渐进逼近
- **Pass 编排**：Pass 1 子任务并发；Pass 2/3 串行
- **批量并发**：参考 `batch-image-concurrent.mdc` Rule

详细见 references/iteration.md（V8.0 后续补充，V7.9 期间见 `归档/v7.9/rules/iterative-image-generation.mdc`）

### B. 模特姿势设计（原 model-pose-design.mdc）

**七要素**（七要素至少 5 项 + 七要素本身就是 7 项也可全写）：
1. 重心分配
2. 手臂位置
3. 身体朝向
4. 头部角度
5. 动态感描述
6. 拍摄透视（正视平拍/低角度仰拍/高角度俯拍/3/4 侧/特写局部/俯视 45°）
7. 人物表情（自信直视/侧望远眺/轻柔微笑/回眸/专注/自然放松/冷酷高级感）

**推荐姿势库**：
- 塑身衣类：P1 单手托腰侧望 / P2 双臂上举 / P3 走步 / P4 撩发斜侧 / P5 弓步拉伸 / P6 侧身展腰（最推荐）/ P7 背面单手腰回眸
- 背面专用：B1 S 形 / B2 双手垂回眸 / B3 手放臀侧

**塑身衣禁忌**：双手交叉腹前 / 正面垂手 / 蹲坐 / 俯身前倾 / 背面双手后放

### C. 场景互动（原 person-scene-library-first.mdc）

**互动类型谱 T1-T6**：
- T1 承压贴靠（坐/靠/倚）
- T2 握持推撑（扶/撑/搭）
- T3 多点几何（错层踏踩）
- T4 大型道具（车/船舷）
- T5 软装陷落（沙发/抱枕）
- T6 非接触融合（窗光/投影/风动）

**场景库优先调用**：
1. 任务含模特+场景且非白底 → 自动 Read 场景库索引
2. 库内匹配 → 用作 image N
3. 库内无匹配 → 降级 Prompt 文字 + 告知用户

**SCENE-5 引用五要素**（场景库图片必写）：
- S1 角色声明（image N 仅作场景参考）
- S2 空间层次（前景/中景/背景）
- S3 光线锚定（主光方向 + 硬度 + 色温）
- S4 融合锚定（接触面 + 投影）
- S5 排除项（不引入无关人物/文字）

**SI 系列互动姿势库** SI-1 ~ SI-26（详见 references/scene.md，V7.9 期间见 `归档/v7.9/rules/person-scene-library-first.mdc`）

## 默认参数

| 参数 | 默认值 | 覆盖条件 |
|---|---|---|
| `--resolution` | `2k` | 用户明确说"4k"升级 |
| `--aspect-ratio` | `3:4`（图生图）/ `9:16`（文生图） | 用户指定覆盖 |
| 语言 | 中文 + 技术锚点 | 用户明确说英文 |

## 与其他 Skill 的关系

| Skill | 关系 |
|---|---|
| `market-platform-analyzer` | 上游：读取卡 A |
| `color-system-designer` (Step 0) | 上游：读取卡 D |
| `typography-designer` (Step 0) | 上游：读取卡 E |
| `print-poster-designer` (Step 0) | 上游：读取卡 F |
| `ai-image-logic-checker` | 强制下游：Pre/Post Gen |
| `ai-image-aesthetic-scorer` | 后续：M16 通过后评分 |
| `nano-banana-prompt-guide` | 知识工具：写作时参考 |
| `rh-image-pro-img2img` / `txt2img` | 执行工具：实际生图调用 |
| `brand-asset-sheet` | 工具：合成品牌资产图 |
| `color-palette-generator` | 工具：生成色卡图 |
| `layout-reference-analyzer` | 工具：分析多模块版式参考图 |
| `video-prompt-designer` | 互补：视频任务走它 |
| `detail-page-designer` | 上游：详情页内部调用本 Skill |
| `reference-library-learner` | 数据源：读取参考库素材 |
| `brand-spec-learner` | 数据源：读取品牌规范 |
| 多条 Rule | image-logic-check / ref-image-must-include / color-palette-authority / prompt-hygiene 强制约束本 Skill 输出 |

## 输入输出

**输入**：
- 用户任务描述（已经过 design-requirement-guide 引导）
- 卡 A/D/E/F（如有协同）
- 用户主图 / 参考图
- 品牌上下文（如激活）

**输出**：
- 完整 Prompt 文本（中文主体 + 技术锚点）
- `--images` 参数清单（产品图 + 人物库 + 场景库 + 参考素材 + 色卡 + 品牌资产）
- 评估维度（供 ai-image-aesthetic-scorer 使用）
- 迭代生图计划（如需）

## 注意事项

- **任何 Prompt 都必须先过 ai-image-logic-checker Pre-Gen**，禁止直接调用生图 API
- 默认中文，**禁止以"英文模型理解更准"为由切换英文**（详见 ai-designer-assistant.mdc 默认输出语言规范）
- image N 引用与 `--images` 数量一一对应，**未引用 = 模型忽略**
- 详细工作流见 `归档/v7.9/能力模块/M8_视觉简报生成器.txt`
