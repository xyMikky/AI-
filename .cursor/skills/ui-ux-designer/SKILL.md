---
name: ui-ux-designer
description: UI/UX 界面设计专家——APP/Web/小程序界面、原型、组件库、交互流程设计。覆盖 IA 信息架构、组件层级（页面→区块→组件→原子）、交互流程、状态设计（默认/hover/active/disabled/error/loading）、响应式断点、设计系统构建。**仅做 UI 界面设计**，**不做平面物料**（海报/印刷 → print-poster-designer），**不做 AI 生图 UI 截图**（→ ai-image-prompt-builder）。常协同 color-system-designer + typography-designer 做完整设计系统。适用：APP 设计、Web 界面、小程序、原型设计、组件库、交互流程、设计系统、Design System、UI Kit。关键词：APP、界面、交互、原型、组件、按钮、页面、流程、UI、UX、设计系统、Design System、UI Kit、Figma 设计。
---

# UI/UX 界面设计（UI/UX Designer）

## 概述

UI/UX 界面设计专家。前身是能力模块 M4_UI_UX界面设计。

## 边界

| 任务 | 主入口 |
|---|---|
| APP/Web/小程序界面 | **本 Skill** |
| 原型/组件库/设计系统 | **本 Skill** |
| 海报/印刷物料 | `print-poster-designer` |
| AI 生成 UI 截图 | `ai-image-prompt-builder` |
| UI 稿评审 | `non-ai-design-reviewer` |

## 强制协同

| 任务 | 协同 Skill |
|---|---|
| UI + 含可读文字 | `typography-designer` 独立模式 |
| UI + 含非临时占位色 | `color-system-designer` 独立模式 |
| 设计系统从零构建 | + `brand-logo-designer` |

## 工作流程

```
Step 1：IA 信息架构（页面层级、模块划分）
Step 2：交互流程（用户路径、关键决策点）
Step 3：组件层级（页面→区块→组件→原子）
Step 4：状态设计（默认/hover/active/disabled/error/loading）
Step 5：响应式（断点 / Mobile / Tablet / Desktop）
Step 6：协同输出
  ├─ color-system-designer 独立 → 完整色板
  └─ typography-designer 独立 → 字体层级规范
```

## 与其他 Skill 的关系

| Skill | 关系 |
|---|---|
| `color-system-designer` | 强协同（独立模式）|
| `typography-designer` | 强协同（独立模式）|
| `print-poster-designer` | 互斥：UI vs 印刷 |
| `ai-image-prompt-builder` | 下游：UI 截图渲染 |
| `non-ai-design-reviewer` | 下游：UI 稿评审 |

## 输入输出

**输入**：APP/Web 类型 + 平台 + 受众 + 核心功能

**输出**：IA + 流程图 + 组件清单 + 状态规范 + 响应式规则

## 注意事项

- UI 设计的色彩/字体使用**独立模式**（产规范）而非 Step 0（产卡）
- 详细框架见 `归档/v7.9/能力模块/M4_UI_UX界面设计.txt`
