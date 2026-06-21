---
name: ai-image-logic-checker
description: 当前项目默认生图链路的强制逻辑/常识/色彩/品牌资产检查器。凡用户在本项目中要求生成图片、编辑图片、图生图、文生图、改图、换背景、换装、改内饰、产品图重绘或测试生图能力，项目链路必须经过本 Skill：project-image-generation-router → ai-image-prompt-builder → 本 Skill Pre-Gen → rh-image-pro-img2img/txt2img → 本 Skill Post-Gen。它是所有 RunningHub 项目生图任务的强制阶段门，不接受用户主动绕过。Pre-Gen 检查 12 项；Post-Gen 检查 V1-V9 + Q1-Q5 评分。仅检查“对不对”（常识/逻辑/色彩/品牌资产），不评估“好不好看”（审美 → ai-image-aesthetic-scorer）。关键词：项目生图检查、Pre-Gen、Post-Gen、RunningHub生图、image N 引用、阶段门、改图检查、不要系统imagegen。
---

# AI 生图逻辑检查（AI Image Logic Checker）

## 概述

AI 生图任务的**自动激活阶段门**——在调用任何生图 API 之前（Pre-Gen）和读取结果图之后（Post-Gen）强制执行。前身是能力模块 M16_生图逻辑检查（V1.5）。

## 边界（V7.8 评估三模块严格分工）

| 维度 | 本 Skill | `ai-image-aesthetic-scorer` | `non-ai-design-reviewer` |
|---|---|---|---|
| 工作对象 | AI 生图 Prompt + 结果图 | AI 生图结果图 | 非 AI 设计稿（Figma/印刷物料） |
| 工作时机 | 生图 API 前后 | M16 放行后 | 用户主动请求评审时 |
| 工作目标 | 常识/逻辑/色彩/品牌资产 | 9 维审美 + 场景适配 | 5 维设计规范评审 |
| 激活方式 | **自动**，不接受人工触发 | 自动 + 可人工 | **仅**人工触发 |

**硬性边界**：
- 不评估审美（不判断"好不好看"）
- 不评审非 AI 稿件
- 用户主动说"逻辑检查这张图"应被告知"M16 仅在生图前后自动触发，不接受人工主动触发"

## Gate A：Pre-Gen 检查（12 项）

| 项 | 检查内容 |
|---|---|
| L0 姿势设计 | 七要素至少 5 项 + 拍摄透视 + 表情 + 非默认站姿 |
| L1 产品使用常识 | 成对物品、穿戴方式、数量一致 |
| L2 人体物理常识 | 肢体完整、姿势可行、透视一致 |
| L3 场景一致性 | 光向、季节、场景库 SCENE-5 |
| L4 歧义消除 | 单复数、展示 vs 穿戴 |
| L5 image N 引用完备性 | 每张 --images 必须在 Prompt 中被 image N 引用 + 借鉴维度 |
| L5-a 图生图保留锚点 | 图生图/改图必须包含“除变更对象外，保持 image N 中所有内容完全一致”的引用式保留锚点；细节枚举不能替代锚点 |
| L6 阶段门完备性 | L6-a 色卡门 / L6-b 版式门 / L6-c 参考库门 / L6-d 品牌资产门 / L6-e 协同模块门 |
| L7 色彩权威 | 禁句清单 + 句式 A/B/C 必查 |
| L8 用户色彩偏好对齐 | 默认白底 / 禁用灰系大面积 / 参考图有色背景必询问 |
| L9 X 域陷阱规避清单 | 历史翻车反向约束句 |
| L10 场景图取景比例 | 三档声明 + 产品结构五点 + 发尾遮挡自检 + 中间档过渡 |
| L11 默认输出语言 | Prompt 主体中文 + 技术锚点保留原样 |
| L12 token 效率 | 英文结构标签 + 品牌名位置合法 + 元描述精简 + 抽象调性词保留 |

任一不通过 → **必须修正 Prompt 后重过**，不得带已知缺陷生图。

### 图生图保留锚点检查

对所有 `img2img` 任务，Pre-Gen 必须额外确认：

- Prompt 是否先定义了本次变更对象；
- Prompt 是否使用 `image 1` / `image N` 引用式保留锚点；
- 保留锚点是否覆盖构图、透视、比例、主体结构、材质、光影、背景和未指定元素；
- 后续细节清单是否只是补充，而不是替代引用式保留；
- `pre_gen_notes` 是否写明 `保留锚点：已使用`。

缺少任一项时，先退回 `ai-image-prompt-builder` 修正 Prompt，不得执行生图。

## Gate B：Post-Gen 检查（V1-V9 + 5 维评分）

### V1-V9 验证项

V1 穿戴完整 / V2 人体合理 / V3 物理合理 / V4 品牌敏感 / V5 参考图一致性（含 V5-d 产品色独立性）/ V6 用户色彩偏好一致 / V7 5 维评分 / V8 X 域入库建议 / V9 场景图产品可视面积 + 结构完整性

### Q1-Q5 五维评分（V1.5）

| 维度 | 权重 | 满分 |
|---|---|---|
| Q1 产品准确度 | 30% | 10 |
| Q2 人物/物理合理性 | 20% | 10 |
| Q3 构图/版式 | 20% | 10 |
| Q4 色彩准确性 | 15% | 10 |
| Q5 文字/品牌资产 | 15% | 10 |

**加权总分** = `Q1×3 + Q2×2 + Q3×2 + Q4×1.5 + Q5×1.5`（0-100）

**X 域入库判定**：
- 总分 < 40 → 主动输出【X 域入库建议】询问用户
- 40-59 + 用户软触发词（"不行/翻车"）→ 询问入库
- ≥ 60 → 沉默通过，进入 ai-image-aesthetic-scorer

## 工作流程

```
Prompt 构造完毕
  ↓
Gate A · Pre-Gen 12 项 → 通过 / 修正
  ↓
调用生图 API（→ rh-image-pro-img2img / txt2img）
  ↓
读取结果图
  ↓
Gate B · Post-Gen V1-V9 + Q1-Q5 评分 → 通过 / 迭代修正
  ↓
评分 < 40 → 输出【X 域入库建议】
评分 ≥ 60 → 进入 ai-image-aesthetic-scorer 审美评估
```

## 与其他 Skill 的关系

| Skill | 关系 |
|---|---|
| `ai-image-prompt-builder` | 上游：所有 Prompt 必经 Pre-Gen Gate |
| `rh-image-pro-img2img` / `txt2img` | 上游：所有生图调用前后必经本 Skill |
| `ai-image-aesthetic-scorer` | 下游：本 Skill 通过后才进入审美评分 |
| `non-ai-design-reviewer` | 互斥：仅评 AI 生图，非 AI 稿不进 |
| `image-logic-check.mdc` | 配套强制 Rule，触发本 Skill 自动激活 |

## 输入输出

**输入**：
- Pre-Gen：完整 Prompt + `--images` 列表 + 调控决策
- Post-Gen：结果图本地路径 + 原 Prompt + 参考图

**输出**：
- 【Pre-Gen 报告】（含 12 项检查结果）
- 【Post-Gen 报告】（含 V1-V9 验证 + Q1-Q5 评分 + 加权总分）
- 必要时：【X 域入库建议】

## 注意事项

- **不接受人工主动触发**——用户说"检查一下这张图"应识别为审美评估，路由到 `ai-image-aesthetic-scorer`
- 评分仅"打分"，不"打回"——通过 Q 评分 + 文字诊断给改进建议
- 详细禁句清单/失败案例库见 `归档/v7.9/能力模块/M16_生图逻辑检查.txt`
