---
name: brand-logo-designer
description: 品牌与 Logo 设计专家——从零创建品牌视觉识别系统（VI/Logo/品牌定位），覆盖品牌策略分析、Logo 概念探索、字体设计、应用场景规范输出。**只做"从零创建"**，**不做"学习已有品牌"**（学习已有素材 → brand-spec-learner），**不做 Logo 渲染生图**（实际渲染 → ai-image-prompt-builder）。本 Skill 输出文档+概念草图+设计原则；Logo 视觉化由下游生图 Skill 完成。常协同 color-system-designer + typography-designer 做完整品牌体系。适用：从零创建品牌、Logo 设计、VI 设计、品牌定位、商标设计、品牌焕新、视觉识别系统、品牌策略。关键词：logo、标志、品牌、VI、视觉识别、商标、品牌设计、品牌创建、品牌焕新、品牌策略、Logo 设计。
---

# 品牌与 Logo 设计（Brand Logo Designer）

## 概述

品牌视觉识别系统（VI）的从零创建。前身是能力模块 M1_品牌与Logo设计。

## 边界

| 任务 | 主入口 |
|---|---|
| 从零创建品牌/Logo | **本 Skill** |
| 学习已有品牌素材 | `brand-spec-learner` |
| Logo 渲染生图 | `ai-image-prompt-builder`（本 Skill 输出概念后下游执行） |
| 评审已完成 Logo 稿 | `non-ai-design-reviewer` |

## 工作流程

```
Step 1：品牌策略分析（行业/受众/调性/差异化）
  ↓
Step 2：Logo 概念探索（≥3 个方向草图描述）
  ↓
Step 3：协同模块输入
  ├─ color-system-designer → 主色/辅色/点缀
  └─ typography-designer → 主字族/字重
  ↓
Step 4：应用场景规范（最小尺寸/安全空间/反白/单色/禁忌）
  ↓
Step 5（可选）：交付 ai-image-prompt-builder 渲染概念图
```

## 完整品牌体系（强制协同）

| 任务 | 协同 Skill |
|---|---|
| 完整品牌设计 | M1（本）+ M2（color-system-designer）+ M3（typography-designer）|
| 品牌焕新提案 | + design-proposal-writer |

## 与其他 Skill 的关系

| Skill | 关系 |
|---|---|
| `brand-spec-learner` | 互斥：从零 vs 学已有 |
| `color-system-designer` | 强协同：品牌色板 |
| `typography-designer` | 强协同：品牌字体 |
| `ai-image-prompt-builder` | 下游：概念视觉化 |
| `non-ai-design-reviewer` | 下游：完成稿评审 |

## 输入输出

**输入**：行业 + 受众 + 调性 + 竞品参考（可选）

**输出**：品牌策略文档 + Logo 概念方向 + 视觉识别规范

## 注意事项

- 不直接生成 Logo 图片，概念交给下游
- 详细策略框架见 `归档/v7.9/能力模块/M1_品牌与Logo设计.txt`
