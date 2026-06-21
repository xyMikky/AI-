---
name: amazon-competitor-quick-analyzer
description: Amazon 简单竞品分析专家——输入单个亚马逊商品 URL，快速抓取套图信息、Amazon 页面元数据和真实评论数据，输出一份纯文字中文简版竞品分析。**只做轻量文字结论**，**不生成 HTML 看板 / visual.json / index.html / review_dashboard.html（→ 深度完整报告走 amazon-competitor-analyzer）**。仍必须获取事实输入：套图与 A+ 抓取报告、metadata.json 页面信息、评论样本与评论聚合摘要。适用于用户说“简单分析一下这个竞品”“快速看下这个 Amazon 链接”“不要看板只要文字结论”“先粗看竞品优缺点”的场景。关键词：简单竞品分析、快速竞品分析、Amazon 简析、Listing 快速拆解、评论数据、套图信息、页面信息、文字报告、轻量分析。
---

# Amazon 简单竞品分析

## 定位与边界

| 维度 | 内容 |
|---|---|
| 做什么 | 对单个 Amazon 商品 URL 做轻量竞品拆解：抓取套图 / A+ 信息、页面元数据、评论样本与评论聚合，然后输出一份中文纯文字结论。 |
| 不做什么 | 不生成 `visual.json`、`index.html`、`review_dashboard.html`、`reviews_data.js`，不做完整六维可视化报告，不做多 SKU 横向沉淀（→ 走 `amazon-competitor-analyzer` / `amazon-multi-asin-visual-synthesizer`）。 |
| 上游依赖 | 复用 `amazon-image-extractor` 的抓图脚本、`amazon-competitor-analyzer` 的元数据与评论聚合脚本、`linkfox-amazon-reviews` 的评论抓取脚本。 |
| 下游对接 | 如果用户看完简析后要求“出完整报告 / 看板 / HTML / 深度分析”，转交 `amazon-competitor-analyzer`，不要在本 Skill 内补 HTML。 |

## 触发条件

- 用户提供一个 Amazon 商品 URL，并使用轻量表述：`简单分析`、`快速分析`、`粗看一下`、`先看这个竞品`、`不要看板`、`只要文字`、`简单拆解`。
- 用户重点想先知道：这个竞品卖点是什么、页面问题在哪里、评论反馈说明什么、我们可借鉴和规避什么。

## 不触发条件

- 用户明确要求完整竞品分析、HTML 报告、可视化看板、评论交互看板、三件套报告 → 使用 `amazon-competitor-analyzer`。
- 用户一次给出 2 个及以上 URL 并要求对比 → 使用 `amazon-competitor-analyzer` 的多 URL 流程，完成后由 `amazon-multi-asin-visual-synthesizer` 做沉淀。
- 用户只想抓取套图 / A+ 图，不要分析 → 使用 `amazon-image-extractor`。

## 输入 / 输出契约

### 输入

| 输入项 | 必需 | 说明 |
|---|---|---|
| Amazon 商品 URL | 必需 | 单个 `/dp/<ASIN>` 链接。 |
| 用户评论文件 | 可选 | `.json` / `.xlsx`。若用户提供，优先使用。 |
| 关注维度 | 可选 | 如视觉策略、卖点排序、评论痛点、是否值得借鉴。 |

### 输出

默认只向用户输出一份中文纯文字简析，同时可落地一个 `quick_competitor_analysis.md` 作为存档。

允许产物：

```text
<输出目录>/
├─ fetched_page.html
├─ report.json
├─ metadata.json
├─ reviews_linkfox_raw*.json       # 条件：自动评论抓取成功
├─ reviews_aggregate.json          # 条件：存在评论数据
└─ quick_competitor_analysis.md    # 可选，但推荐保存
```

禁止产物：

```text
visual.json
index.html
review_dashboard.html
reviews_data.js
comparison_matrix.*
synthesis.*
```

## 工作流程

### 阶段 1：素材采集

调用 `amazon-image-extractor` 抓取页面素材与套图信息：

```powershell
python ".cursor/skills/amazon-image-extractor/scripts/extract_and_stitch.py" `
  --url "<商品URL>" --save-fetched-html
```

获得：

- `fetched_page.html`
- `report.json`
- 套图数量、A+ 图片数量、视频封面数量
- 如抓取成功，可能包含 `gallery_vertical.png` / `aplus_vertical.png`

如果直连被 Amazon 机器人页拦截，沿用 `amazon-competitor-analyzer` 的浏览器 HTML 兜底路径：先用浏览器打开商品页，抓取 `document.documentElement.outerHTML` 保存为 `fetched_page.html`，再用 `--html-path` 模式重跑提取脚本。

### 阶段 2：页面元数据抽取

必须抽取页面信息，不得只凭视觉观察写结论：

```powershell
$env:PYTHONIOENCODING="utf-8"
python ".cursor/skills/amazon-competitor-analyzer/scripts/extract_metadata.py" `
  --html "<输出目录>/fetched_page.html" --url "<商品URL>"
```

重点使用字段：

- `asin`、`title`、`brand`
- `rating`、`rating_count`
- `price`
- `category_rank`
- `bullets`
- `specs`
- `variations`
- `media.gallery_count`、`media.aplus_module_count`

### 阶段 3：评论数据获取

评论数据是简版分析的必需事实输入。处理优先级：

1. 用户提供 `.json` / `.xlsx` 评论文件 → 直接使用。
2. 用户只提供 URL → 从 `metadata.json.asin` 提取 ASIN，调用 `linkfox-amazon-reviews` 抓取评论样本。
3. 评论抓取失败 / 未授权 / 返回 0 条 → 不阻塞简析，但必须在最终文字中写明“评论样本未获取成功，本次仅使用 Amazon 页面全局评分与页面信息”。

美国站 URL 使用：

```powershell
$env:PYTHONIOENCODING="utf-8"
python ".cursor/skills/linkfox-amazon-reviews/scripts/response_io.py" run `
  --script ".cursor/skills/linkfox-amazon-reviews/scripts/amazon_us_reviews.py" `
  --out-dir "<输出目录>" `
  --label "reviews_linkfox_raw" `
  '{"asin":"<ASIN>","marketplace":"US","positiveNum":50,"criticalNum":50,"allStarsNum":50,"sortBy":"recent","formatType":"current_format"}'
```

PowerShell JSON 参数如果被撕裂，改用临时 Python `subprocess` 参数列表调用，不要反复调引号。

### 阶段 4：评论聚合

存在评论数据时必须生成 `reviews_aggregate.json`：

```powershell
$env:PYTHONIOENCODING="utf-8"
python ".cursor/skills/amazon-competitor-analyzer/scripts/aggregate_reviews_json.py" `
  --input "<评论数据路径>" `
  --meta "<输出目录>/metadata.json" `
  --output "<输出目录>/reviews_aggregate.json"
```

口径规则：

- 综合判断用 `reviews_aggregate.json.global` 或 `metadata.json.reviews` 的 Amazon 页面全局评分。
- 抓取样本只用于找高频抱怨、好评原因和真实用户语言，不得把样本均分当作产品综合评分。
- 默认只分析 URL 对应目标 ASIN；除非用户明确说“分析整个系列”，否则不得混入同系列其它 ASIN。

### 阶段 5：纯文字简析

根据 `report.json`、`metadata.json`、`reviews_aggregate.json` 输出简版报告。建议结构固定为：

```markdown
## 简单竞品分析：<品牌 / 产品简称>

### 1. 一句话判断
<30-80 字，直接说这个 listing 最大机会或最大问题。>

### 2. 页面基本面
- ASIN / 品牌 / 标题：
- 星级与评价数：
- 类目排名：
- 价格状态：
- 套图 / A+：

### 3. 卖点排序
1. <页面第一优先级卖点>
2. <页面第二优先级卖点>
3. <页面第三优先级卖点>

### 4. 评论反馈
- 全局口碑：
- 好评集中在：
- 差评集中在：
- 需要注意的近期趋势：

### 5. 主要优点
- <优点 1>
- <优点 2>
- <优点 3>

### 6. 主要问题
- <问题 1>
- <问题 2>
- <问题 3>

### 7. 可借鉴 / 要规避
- 可借鉴：
- 要规避：
```

如果用户要求“更简单”，压缩为 5 段：

```markdown
结论：
页面打法：
评论反馈：
可借鉴：
要规避：
```

## 分析口径

简版报告仍必须基于事实，不允许编造：

- 页面卖点以 `metadata.json.bullets` 和套图 / A+ 抓取结果为依据。
- 价格、评分、评价数、BSR 以 `metadata.json` 为依据。
- 评论结论以 `reviews_aggregate.json` 为依据。
- 若某字段缺失，写“页面未解析到”，不得臆造。

## 与完整竞品分析的边界

本 Skill 适合快速判断，不适合正式汇报。如果出现以下情况，应建议切换到 `amazon-competitor-analyzer`：

- 用户需要可视化 HTML 报告。
- 用户需要交互式评论看板。
- 用户需要沉淀成可发客户 / 老板的正式报告。
- 用户需要多 SKU 横向对比。
- 用户需要完整六维评分与行动结论卡片。

## 示例回复

```markdown
## 简单竞品分析：Ontel Turbo Jet HydroX5 Pro

### 1. 一句话判断
这个 listing 的核心问题是预期管理失败：页面用 5X / 350 PSI / Power Wash 抬高“强力清洗机”预期，但评论集中反馈压力弱、电池和故障问题。

### 2. 页面基本面
- ASIN：B0F1Z74B63
- 品牌：Ontel
- 星级：3.3 ★ / 1,598 评价
- 类目：#30 in Pressure Washers
- 套图 / A+：6 张套图 / 0 个 A+ 模块

### 3. 卖点排序
1. 便携无线 + 5X 清洁力。
2. 6 合 1 喷嘴、泡沫炮、双水源。
3. 21V 电池与 350 PSI 参数。

### 4. 评论反馈
全局 1-2 星占 36%，差评主要集中在压力弱、像普通水管、电池充电故障、广告承诺过高。好评则认可轻度清洁、无线便携、配件完整。

### 5. 可借鉴 / 要规避
可借鉴它的套图卖点拆分方式；要规避把轻度便携工具包装成传统高压清洗机替代品。
```

## 禁止行为

- 跳过评论数据获取，只看 Amazon 页面评分就写评论洞察。
- 跳过套图 / A+ 抓取，只凭标题和 bullet 写视觉策略。
- 为“简单”而编造缺失字段。
- 生成 HTML、可视化 JSON、评论看板或横向沉淀文件。
- 把样本均分当作产品综合口碑。
- 多 URL 对比仍使用本 Skill。

## 正确行为

- 即使是简单分析，也必须先拿到三类事实：套图信息、页面元数据、评论数据。
- 输出文字要短，但判断要落在“页面承诺 vs 评论反馈”的缝隙上。
- 结论优先，不铺长篇模板。
- 若用户继续追问某一节，再基于已有文件补充，不重新生成 HTML。
