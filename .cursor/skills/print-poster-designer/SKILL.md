---
name: print-poster-designer
description: 印刷海报与平面物料设计专家——双模式：**独立模式**（用户说"印刷海报/折页/展架/易拉宝/名片/线下物料"，做非 AI 生图的版式设计）走完整 Step 1-4 输出视觉构图方案 + 印刷规范（出血/色域/字体外发/印前文件）；**Step 0 协同模式**（被 ai-image-prompt-builder 声明协同且物料为海报/Banner/电商主图/社媒/详情页模块时）轻量产出【构图决策卡 F】（构图类型/信息层级/元素空间分配/Prompt 关键词）。两种模式互斥。**独立模式仅做非 AI 生图**（要交付印刷或人工排版），**协同模式仅服务 AI 生图**（不做实际印刷输出）。适用：印刷海报、折页、展架、易拉宝、名片、线下物料、电商主图（协同）、Banner（协同）、社媒图（协同）。关键词：海报、banner、宣传册、展架、物料、平面、印刷、折页、易拉宝、名片、印前、出血、构图、版式。
---

# 印刷海报与平面物料（Print Poster Designer）

## 概述

平面物料的双模式 Skill。前身是能力模块 M5_平面视觉与物料。

## 双模式触发契约

| 模式 | 触发信号 | 工作流 | 主产出 |
|---|---|---|---|
| **独立模式** | "印刷海报/折页/展架/易拉宝/名片/线下物料" — 主任务非 AI 生图 | Step 1-4 | 视觉构图方案 + 印刷规范 |
| **Step 0 协同** | 被 ai-image-prompt-builder 声明协同 + 物料为海报/Banner/电商主图/社媒/详情页模块 | Step 0 轻量 | 【构图决策卡 F】|

## 边界

| 任务 | 主入口 |
|---|---|
| 印刷物料（要交付印厂或人工排版） | **本 Skill 独立模式** |
| AI 生图海报/Banner/主图 | **ai-image-prompt-builder**，本 Skill 协同 Step 0 |
| 详情页 | `detail-page-designer`，内部协同本 Skill Step 0 |
| 印前评审 | `non-ai-design-reviewer` |

## 独立模式（Step 1-4）

```
Step 1：视觉调研（受众/调性/竞品物料）
Step 2：构图方案（中心/对角线/几何分割/三分法/留白/满版）
Step 3：版式规划（信息层级 + 元素空间分配）
Step 4：印刷规范（出血 3mm / CMYK / 字体外发 / 文件格式 PDF/X-1a）
  ↓
（强制协同）
  ├─ color-system-designer 独立 → 完整色板
  └─ typography-designer 独立 → 字体层级
  ↓
（可选）送 non-ai-design-reviewer 印前审稿
```

## Step 0 协同模式（轻量交接卡）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【构图决策卡 F】　print-poster-designer 协同输出
• 物料类型：海报 / Banner / 电商主图 / 社媒图
• 输出尺寸：[WxH] — 比例 [W:H]
• 构图类型：中心 / 对角线 / 几何分割 / 三分法 / 留白 / 满版
• 信息层级：1秒 [焦点] / 2秒 [卖点] / 3秒 [CTA]
• 元素空间分配：[人物区/产品区/文字区/留白区位置]
• Prompt 构图关键词：[英文关键词，如 diagonal split, asymmetric, rule of thirds]
• 下游衔接：→ ⑥.9 版式分析 + ⑦ Prompt 构造
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 独立 → 协同桥接

- Step 2 构图类型 → 卡 F 的 `composition_type`
- Step 3 信息层级 + 元素空间分配 → 卡 F 的 `hierarchy` + `layout`

## 与其他 Skill 的关系

| Skill | 关系 |
|---|---|
| `ai-image-prompt-builder` | 下游消费者（Step 0 模式）|
| `detail-page-designer` | 下游消费者（Step 0 模式）|
| `color-system-designer` | 协同：独立模式时强协同 |
| `typography-designer` | 协同：独立模式时强协同 |
| `non-ai-design-reviewer` | 下游：独立模式产物可送印前审稿 |
| `layout-reference-analyzer` | 协同工具：分析多模块版式时调用 |

## 输入输出

**输入**：物料类型 + 受众 + 调性 + 尺寸 + 印刷需求（独立）or 调控声明（协同）

**输出**：
- 独立：视觉构图方案 + 印刷规范
- 协同：【构图决策卡 F】

## 注意事项

- 独立模式必须执行印前规范（出血/色域/字体外发）
- 协同模式仅服务生图，不输出印刷文件
- 详细框架见 `归档/v7.9/能力模块/M5_平面视觉与物料.txt`
