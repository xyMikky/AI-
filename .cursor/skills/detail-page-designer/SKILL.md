---
name: detail-page-designer
description: 详情页设计（电商 listing / Amazon A+ / DTC 落地页 / 天猫详情页）的核心闭环——覆盖中国/欧美双市场，三种工作模式：A 完整详情页设计（产品+平台+受众→结构规划+文案+全部模块 AI 生图）、B 单模块设计/优化、C 详情页学习分析（reference-library-learner 处理详情页素材时的分析框架）。HERO 首图 + M2-M7 模块通过批量并发生图（batch-image-concurrent 规则）调用 ai-image-prompt-builder 实现。HERO 用品牌资产合成图（含 Logo），M2-M7 用字体参考图（不含 Logo）。**详情页任务唯一入口**，**单张电商主图走 ai-image-prompt-builder**。适用：详情页、产品页、listing、A+、宝贝详情、商品详情、长图、详情设计、产品描述页、电商详情、详情页模板、详情页生图、详情页学习。关键词：详情页、产品页、listing、A+、宝贝详情、商品详情、长图、详情设计、产品描述页、电商详情、详情页模板。
---

# 详情页设计（Detail Page Designer）

## 概述

详情页设计的统一业务入口。前身是能力模块 M15_详情页设计专家。

## 与 ai-image-prompt-builder 的边界

| 任务 | 主入口 |
|---|---|
| 单张电商主图 / 海报 / Banner | `ai-image-prompt-builder` |
| 详情页（多模块批量） | **本 Skill** |
| 详情页内部生图调用 | 本 Skill → ai-image-prompt-builder（批量并发） |

## 三种工作模式

| 模式 | 触发 | 输出 |
|---|---|---|
| A 完整详情页设计 | 用户提供产品+平台+受众，从零设计 | 结构规划 + 文案 + 全部模块批量生图 |
| B 单模块设计/优化 | 用户需设计/优化某个特定模块 | 单模块方案 + 生图 |
| C 学习分析 | reference-library-learner 处理详情页素材 | 增强版学习记录（含模块清单+节奏+品类规律） |

## 中国 vs 欧美双市场

| 市场 | 平台 | 风格 | 模块数 |
|---|---|---|---|
| 中国 | 天猫/淘宝/京东/拼多多 | 长图、信息密度高 | 8-15 |
| 欧美 | Amazon/Shopify/独立站 | A+ 模板、留白多 | 5-7 |

## 工作流程（模式 A 完整设计）

```
读取产品 + 平台 + 受众
  ↓
（强制）design-requirement-guide 需求引导
  ↓
（如涉及平台规范）market-platform-analyzer → 卡 A
  ↓
（如品牌激活）brand-spec-learner 加载品牌档案 + 视觉系统
  ↓
（如用户提供版式参考长图）layout-reference-analyzer Phase 1-4 分析
  → 输出【版式分析报告】（每模块 D1-D8 八维分析）
  ↓
确定详情页结构（模块清单 + 顺序 + 内容定位）
  ↓
为每个模块设计文案 + 视觉策略
  ↓
HERO 首图：调用 brand-asset-sheet（含 Logo 模式）+ ai-image-prompt-builder
  ↓
M2-M7 模块：仅字体参考图（不含 Logo）+ ai-image-prompt-builder 批量并发
  ↓
ai-image-logic-checker 对每张图执行 Pre/Post Gen
  ↓
ai-image-aesthetic-scorer 评估
  ↓
输出完整详情页（图 + 文案 + 模块说明）
```

## 详情页结构典型清单

### 欧美 Amazon A+
1. HERO（产品+品牌名+核心卖点）
2. 功能可视化模块
3. 面料/材质模块
4. 尺寸表
5. 模特实穿场景
6. 信任背书
7. CTA / FAQ

### 中国天猫
1. HERO 首屏
2. 痛点+承诺
3. 功能可视化
4. 面料/工艺
5. 模特场景图（多套）
6. 尺寸/穿搭建议
7. 用户评价
8. 信任叠加（销量/媒体/检测）
9. CTA + 服务承诺

## 模式 C：学习分析框架（被 reference-library-learner 调用）

当 reference-library-learner 检测到素材是详情页（路径 N 域 / 长图 / 含模块化版式）时，调用本 Skill 输出**增强版学习记录**，含：
- 📐 详情页结构速写（按上→下罗列模块）
- 模块节奏分析（产品/卖点/信任/CTA 的密度比）
- 品类规律提取（如塑身衣类详情页的标配模块）

## 与其他 Skill 的关系

| Skill | 关系 |
|---|---|
| `ai-image-prompt-builder` | 下游：详情页每张图都通过它生成 |
| `market-platform-analyzer` | 上游：平台规范输入 |
| `brand-spec-learner` | 数据源：品牌激活时读取规范 |
| `layout-reference-analyzer` | 工具：版式参考图分析 |
| `brand-asset-sheet` | 工具：HERO 首图生成品牌资产 |
| `ai-image-logic-checker` | 强制：每张图过 M16 |
| `ai-image-aesthetic-scorer` | 强制：每张图过审美 |
| `reference-library-learner` | 互调：M10 学习详情页素材时调用本 Skill 模式 C |

## 输入输出

**输入**：产品信息 + 平台 + 受众 + 模块需求 + 用户版式参考图（可选）

**输出**：
- 模式 A：完整详情页设计（图集 + 文案 + 模块说明）
- 模式 B：单模块方案 + 生图
- 模式 C：增强版学习记录

## 注意事项

- HERO 首图唯一一次生成品牌资产合成图（含 Logo），M2-M7 不再传 Logo
- 批量生图必须遵守 `batch-image-concurrent` Rule（Shell + block_until_ms: 0）
- 中国详情页模块数远多于欧美，注意控制图片总数（避免 API 限流）
- 详细模块编排详见 `归档/v7.9/能力模块/M15_详情页设计专家.txt`
