---
name: amazon-competitor-analyzer
description: Amazon 单 SKU 竞品分析专家——输入亚马逊商品 URL，自动抓取套图 + A+ 图 + 视频封面 + 页面元数据（品牌/星级/评价数/价格/BSR/变体），按专业六维评分体系（视觉一致性 / 信息层级 / 图文契合度 / 连贯叙事效率 / 品牌沉淀 / 预期管理）输出结构化中文竞品分析报告，含基础信息卡 + 风格五标签 + 内容逻辑分层 + 用户视角 + 适合谁 / 不适合谁 + 客户购买行为 5W2H + 客户画像 + 客户卡诺模型（Kano）真实需求 + 产品开发注意点 + 优势亮点 + 不足问题 + 可借鉴点 + 规避方向 + 加权总分。V4 起新增「客户洞察」分析簇：以 5W2H（Who/What/When/Where/Why/How/How much）拆解购买行为，沉淀典型客户画像，用 Kano 模型把买家需求分为基本型/期望型/兴奋型/无差异/反向五类，并据此输出本品的产品开发注意点。每个 SKU 必出三件套（md + visual.json + html）；评论数据优先使用用户额外提供的完整 `.json/.xlsx`，若用户只提供亚马逊链接且没有评论文件，必须调用 `linkfox-amazon-reviews` 按 URL 对应 ASIN 自动抓取评论样本，保存为 `reviews_linkfox_raw.json` 后复用评论聚合、证据提取与交互式看板链路，追加产出第 4 件套 `review_dashboard.html`。多 URL 模式下：本 Skill 只负责出 N 份单品三件套（有评论样本时每个 SKU 追加看板），**完成后强制 request_user_input 让用户三选一**（A 补充内容 / B 对比总结 / C 结束）；选 B 时控制权移交给独立 Skill `amazon-multi-asin-visual-synthesizer` 出多 ASIN 综合可视化沉淀（自包含 HTML 看板：痛点热力矩阵 / 市场定位气泡图 / 竞品×卖点关系网络图 / Kano 行业需求聚合 四图）。适用：电商竞品 listing 拆解、对标选品分析、A+ 与套图视觉策略评估、Amazon 多 SKU 横向竞品研究、竞品评论研究、客户购买行为分析、客户画像、Kano 需求分析、产品开发方向。关键词：竞品分析、Amazon 竞品、Listing 拆解、A+ 评分、评论分析、买家反馈、视觉策略、信息层级、卖点排序、对标分析、可借鉴点、规避方向、横向竞品研究、多 SKU 对比、5W2H、购买行为、客户画像、用户画像、卡诺模型、Kano、真实需求、产品开发注意点。
---

# Amazon 竞品分析专家

> ⚠️ **核心交付铁律 ①（单 URL）**：每次竞品分析必须产出三件套——`competitor_analysis.md` + `visual.json` + `index.html`。**不允许只产 md 就调用渲染脚本**，否则 HTML 底部会出现大段纯文字 Markdown，用户体验差。详见 §3 阶段⑤。
>
> ⚠️ **核心交付铁律 ②（多 URL · N ≥ 2 时强制）**：N 个 URL 必须**各自产出独立的完整三件套**（N × 三件套）。**严格禁止**以下偷懒行为：
>
> - ❌ 只跑阶段 ①素材采集 + ②元数据抽取，然后在对话里给口头评分总结，不落地任何文件
> - ❌ 把 N 份单品压缩成一份合并报告 / 跳过任一 SKU 的三件套
> - ❌ 因 N 个 SKU "工作量大" 就降级为简版评分
> - ❌ 在第 N 个 SKU 上偷懒（前 1-2 个做完整三件套，后面只在对话里口述）
>
> **如果 token / 时间预算真的不够**：先确认完整范围 → 通过 `request_user_input` 与用户协商是否拆批次产出，**而不是擅自降级**。详见 §3 阶段⑤ 多 URL 段 + §5。
>
> ⚠️ **核心交付铁律 ③（对比沉淀必须走独立 Skill · V2.3 新增）**：N ≥ 2 时，本 Skill **只负责出 N 份单品三件套**；任何"行业共性 / 横向对比 / 竞品逻辑 → 本品建议逻辑 / 战略对比沉淀"都由 `**amazon-multi-asin-visual-synthesizer`** 独立 Skill 完成（自带 ECharts 渲染器，输出 4 图自包含 HTML 综合看板）。本 Skill 完成 N 份单品三件套后**必须 `request_user_input`** 让用户在 "补充内容 / 对比总结 / 都不要" 三选一（详见 §5.4）。严禁本 Skill 自己产出 `comparison_matrix.md / .html`——历史上这种产物会复用单品渲染脚本，导致对比页"长得像单品页"（左侧仍出现套图缩略图与 A+ 模块切换器），与对比沉淀的定位严重错位。

## 1. 何时使用

用户表述任一即触发本 Skill：

- "竞品分析"、"分析这个竞品"、"对标分析"、"拆解 listing"、"分析 A+"
- "amazon.com/dp/xxxx 的产品做个竞品分析"
- "把这两个竞品对比一下"（多 URL 并联）
- 用户在使用 `amazon-image-extractor` 抓完素材后，主动表达要"分析"

**不接管的场景**：

- 仅仅是"抓套图 / 抓 A+ 图" → 走 `amazon-image-extractor`（本 Skill 会调用它，但单独抓素材不要走本 Skill）
- 评审自家设计稿（非 AI 生成）→ 走 `non-ai-design-reviewer`
- 设计本品的新主图 / 新 A+ → 走 `ai-image-prompt-builder` 或 `detail-page-designer`

## 2. 输入


| 项                        | 必填  | 说明                                                                                                                                                                                                                                     |
| ------------------------ | --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 商品 URL                   | 必填  | 一个或多个亚马逊商品页 URL（`/dp/<ASIN>`），多个 URL 走对比模式                                                                                                                                                                                             |
| 完整评论数据（JSON / **Excel**） | 可选  | 用户导出的整份评论文件，支持 `.json` 与 `.xlsx`（openpyxl 直读，**无需先手动转 JSON**）。列/键兼容中文：`ASIN / 标题 / 内容 / 星级 / 型号 / 所属国家 / 评论时间 / VP评论`。**默认只分析 URL 对应的目标 ASIN 的评论**——文件内同系列其它 ASIN（不同款式/颜色）默认剔除（详见 §3 阶段 ②.5 / ②.6）。仅当用户明确要求"分析全系列"时才加 `--all-variants` |
| 评论数据自动抓取                 | 自动  | 当用户只提供亚马逊商品 URL、未提供评论文件时，阶段 ② 后必须读取 `metadata.json.asin` 和 URL 站点，调用 `linkfox-amazon-reviews` 获取评论样本，保存为 `<阶段①输出目录>/reviews_linkfox_raw.json`，再进入阶段 ②.5 / ②.6 / ②.7。用户提供完整评论文件时，优先使用用户文件，不重复抓取                                         |
| 对标参照                     | 可选  | 用户的"本品"或品牌 DNA 档案，用于做"可借鉴/规避"判断的基准                                                                                                                                                                                                     |
| 关注维度                     | 可选  | 用户特别关心的方向（如"我想看视觉策略"、"我想看卖点排序"），用于在报告中加重该维度                                                                                                                                                                                            |


## 3. 工作流（5 阶段）

**单 URL 流水线**：

```
① 素材采集（必）         → amazon-image-extractor
② 元数据抽取（必）       → .codex/skills/amazon-competitor-analyzer/scripts/extract_metadata.py
②.1 全局星级分布补抓（必尝试）→ fetch_review_histogram.py
                          ⚠️ 当 metadata.reviews.histogram 为空但页面存在 average-customer-review/popover URL 时触发；
                          成功后回填 metadata.json.reviews.histogram；失败时必须显式记录“全局分布缺失”，不得用样本分布冒充
②.4 评论数据来源决策（必）→ 用户文件优先；若只有 URL 则调用 linkfox-amazon-reviews 自动抓取
                          输出 reviews_source.json / reviews_linkfox_raw.json（按实际来源）
②.5 评论聚合（条件）     → .codex/skills/amazon-competitor-analyzer/scripts/aggregate_reviews_json.py
                          ⚠️ 当存在用户评论文件或 ②.4 自动抓取成功时触发；默认只分析 URL 对应的目标 ASIN
                          ⚠️ V3 起数据驱动关键词/主题（不再绑定品类）+ 支持 .json/.xlsx + LinkFox data[] JSON
②.6 交互看板生成（条件） → build_review_dashboard.py + aspects.json + keywords.json（强制）
                          ⚠️ 当存在用户评论文件或 ②.4 自动抓取成功时触发，产出第 4 件套 review_dashboard.html
                          ⚠️ Agent 必须先产出 aspects.json（智能问题归类）+ keywords.json（中文策展词云），再传 --aspects / --keywords
                          默认只分析目标 ASIN + 离线自包含（内联 ECharts）+ 多维图表 + 时间范围框选联动
②.7 评论证据提取（条件） → .codex/skills/amazon-competitor-analyzer/scripts/extract_review_evidence.py
                          ⚠️ 只要有评论来源就必须执行；报告优缺点必须基于全样本命中证据
②.8 关键词架构与流量入口（详细报告必尝试）→ .codex/skills/amazon-competitor-analyzer/scripts/fetch_keyword_traffic.py
                          ⚠️ 配置了 LINKFOXAGENT_API_KEY 时必须触发；调 SIF 反查 ASIN 流量词 + 流量来源构成
                          产出 keyword_arch.json + traffic_source.json 后，必须喂报告「三-3 关键词架构 / 三-4 流量入口」两章
③ 模块化拆解（可选）     → layout-reference-analyzer（仅当 A+ 模块数 ≥ 4 且用户希望深度版式分析）
④ 五维评分（必）         → 本 Skill 内逻辑（基于素材 + 元数据 + 视觉观察）
④.4 客户洞察（必 · V4 新增）→ 本 Skill 内逻辑（基于 bullets + 页面定位 + 评论证据 review_evidence.json）
                          产出四块：5W2H 购买行为 / 客户画像 / Kano 真实需求 / 产品开发注意点
                          ⚠️ 必须基于事实（评论原话、变体分布、页面卖点）推断，禁止凭空虚构画像
                          ⚠️ 5W2H 每项必须同时包含 key + 中文标题(label/zh) + 正文(value/finding)，HTML 不允许只显示 who/what/when 彩色标签
⑤ 三件套报告输出（必）   → md（§4 模板） + visual.json（§4.1 契约） + html（渲染脚本）
                          ⚠️ 必须三件套同时产出，不允许只产 md
                          ⚠️ 若 ②.6 已生成看板，html 渲染会自动注入"📊 交互式评论看板"跳转入口
```

**多 URL 流水线（N ≥ 2 时强制走此分支）**：

```
FOR each url in [url_1, url_2, ..., url_N]:
   跑完整阶段 ①→②→③→④→⑤（产出该 SKU 的独立三件套，并通过 validate_report_consistency.py）

THEN：⑥ 交接询问（强制 request_user_input · 详见 §5.4）
   询问用户三选一：
     A. 补充内容（在本 Skill 内继续对某 SKU 报告做修订）
     B. 综合可视化沉淀（→ 调用 amazon-multi-asin-visual-synthesizer，输出综合可视化看板）
     C. 都不需要（结束）

强制产物 = N 套单品三件套，全部写入同一父目录
         生成结果输出/amazon图片提取/_compare_<时间戳>/

可选追加 = 若用户选 B，则由 amazon-multi-asin-visual-synthesizer
         在 _compare_<时间戳>/ 根目录追加综合可视化看板 index.html + viz_data.json（本 Skill 不亲自产出）
```

> ⚠️ **多 URL 流水线不可降级**：哪怕用户只问"哪个最好"，也必须先产出 N 份单品三件套作为评分依据，再回答。"对话里口头评分 + 不落地文件"对 N ≥ 2 是禁止行为（详见 §6）。
> ⚠️ **对比矩阵 HTML 已下线**：本 Skill 不再自产 `comparison_matrix.md / .html`——历史版本 V2.2 之前的对比矩阵走单品渲染脚本，对比页会带左侧套图栏（用户已明确反馈"不合适"）。所有横向综合可视化沉淀走 `amazon-multi-asin-visual-synthesizer`。

### 阶段 ①：素材采集

调用 `amazon-image-extractor`：

```powershell
python ".codex/skills/amazon-image-extractor/scripts/extract_and_stitch.py" `
  --url "<商品URL>" --save-fetched-html
```

获得：

- 套图原图列表 + `gallery_vertical.png`
- A+ 分组图 + `aplus_vertical.png`（含视频封面）
- `fetched_page.html`（供阶段 ② 使用）
- `report.json`

> ⚠️ **反爬拦截降级路径（V3.1 · 高频踩坑，必读）**：`--url` 直连对热门 listing **经常被拦截**，返回 `blocked_by_amazon: robot_check_page`（机器人校验页）。一旦命中，**不要反复重试直连**，立即走"浏览器取 HTML → 本地解析"降级链：
>
> 1. 用浏览器（`browser_navigate` / 已开标签页）**实际打开商品 URL**，等页面加载完；
> 2. 通过 CDP 抓整页 HTML（`browser_cdp` → `Runtime.evaluate`，表达式 `document.documentElement.outerHTML`）；
> 3. 把抓到的 `outerHTML` 落地为 `<输出目录>/fetched_page.html`（注意 CDP 返回的是 JSON，正文在 `result.result.value`，需用 Python 解析后写文件，按 UTF-8）；
> 4. 改用 `**--html-path` 模式**重跑提取脚本，吃这份本地 HTML：
>
> ```powershell
> python ".codex/skills/amazon-image-extractor/scripts/extract_and_stitch.py" `
>   --html-path "<输出目录>/fetched_page.html" --output-dir "<输出目录>"
> ```
>
> 同一份 `fetched_page.html` 直接供阶段 ② 元数据抽取复用，**无需二次请求**。判断标准：`report.json` 报 `blocked_by_amazon` / 套图数为 0 / 返回明显是校验页 → 一律切降级链，不要在直连上空转。

### 阶段 ①.5：图片链路验收（必做）

`render_report_html.py` 左侧套图栏和 A+ 预览**只读取同目录 `report.json`**，不会自动扫描 `gallery/` / `aplus/` 目录。图片文件存在但 `report.json` 缺失或为空，会生成 `class="gallery-main" src=""`，页面看起来像“套图无法查看”。因此阶段 ① 后、阶段 ⑤ 渲染前必须做以下检查：

- `report.json` 必须存在，且 `gallery.files[]` 指向 `gallery/01_...` 等相对路径，`aplus.groups[].files[]` 指向 `aplus/g01_...` 等相对路径。
- `report.json` 中引用的每个图片相对路径都必须在当前 ASIN 目录下真实存在。
- `metadata.json.media.gallery_count`、`metadata.json.media.aplus_module_count` 必须与 `report.json` 可用图片数/模块数保持一致；若 metadata 抽取阶段没有写入，必须回填后再生成 `visual.json`。
- 单品 `index.html` 生成后必须抽检：不得包含 `class="gallery-main" src=""`；若 `report.json.gallery.files` 非空，HTML 必须包含第一张套图相对路径；若 A+ 非空，HTML 必须包含第一张 A+ 相对路径。

修复规则：优先重跑 `amazon-image-extractor`（URL 或 `--html-path` 模式）补出标准 `report.json`。只有在图片文件已经完整存在、只是 `report.json` 缺失时，才允许从 `gallery/` 与 `aplus/` 目录合成最小 `report.json`，并同步回填 `metadata.media` 后重渲染 HTML。不得只因为 `gallery/` 目录非空就认为单品三件套合格。

### 阶段 ②：元数据抽取

> ⚠️ **中文路径 + 编码铁律（V3.1）**：本 Skill 全部 Python 调用**默认先设** `$env:PYTHONIOENCODING="utf-8"`——否则脚本向 PowerShell 控制台打印含 `・`/特殊符号的 JSON 会报 `UnicodeEncodeError: 'gbk' codec`。下方各阶段命令已内置该前缀，勿删。

调用本 Skill 配套工具：

```powershell
$env:PYTHONIOENCODING="utf-8"
python ".codex/skills/amazon-competitor-analyzer/scripts/extract_metadata.py" `
  --html "<阶段①输出目录>/fetched_page.html" --url "<商品URL>"
```

获得（JSON）：

- `asin`、`title`、`brand`
- `rating`、`rating_count`
- `reviews.histogram[]`：Amazon 页面全局星级分布（若静态 HTML 未内嵌，阶段 ②.1 必须尝试补抓）
- `price.current`、`price.list`、`price.currency`
- `price.main_offer_status`（`available` / `no_featured_offer` / `unknown`）
- `price.variant_from_price`、`price.variant_from_currency`（变体起售价）
- `category_rank[]`（如 `#27 in Women's Shapewear Bodysuits`）
- `variations.colors`、`variations.sizes`
- `bullets[]`（卖点要点列表）
- `specs[]`（产品基本参数，**格式自适应**：`[{label, value}, ...]`）
- `aplus_module_count`、`gallery_count`（来自阶段 ①）

### 阶段 ②.1：全局星级分布补抓（必尝试）

**触发条件**：`metadata.json.reviews.histogram` 为空，且 `fetched_page.html` 中存在 `average-customer-review/popover` 小组件 URL。

调用：

```powershell
$env:PYTHONIOENCODING="utf-8"
python ".codex/skills/amazon-competitor-analyzer/scripts/fetch_review_histogram.py" `
  --html "<阶段①输出目录>/fetched_page.html" `
  --metadata "<阶段①输出目录>/metadata.json" `
  --url "<商品URL>"
```

若 Amazon 对小组件请求返回验证码页，可用浏览器或其它已通过风控的方式保存该小组件 HTML，再离线解析：

```powershell
$env:PYTHONIOENCODING="utf-8"
python ".codex/skills/amazon-competitor-analyzer/scripts/fetch_review_histogram.py" `
  --html "<阶段①输出目录>/fetched_page.html" `
  --metadata "<阶段①输出目录>/metadata.json" `
  --widget-html "<阶段①输出目录>/review_histogram_widget.html"
```

验收：
- 成功时 `metadata.json.reviews.histogram` 必须包含 5/4/3/2/1 星百分比，总和约 100%。
- `reviews_aggregate.json.global.histogram` 必须继承这个全局分布。
- `visual.json.sections[].type=="review-sentiment"` 的 `histogram` 必须使用 `reviews_aggregate.json.global.histogram`，不得使用样本口径直方图。
- 若补抓失败，报告「六」节必须写明“Amazon 页面未提供全局星级分布 / 小组件被风控”，并只展示综合星级与评价数；禁止用 LinkFox 样本分布冒充全局分布。

> `**specs[]` 产品参数（格式自适应）**：脚本会依次扫描详情页 4 类常见参数布局——
> ① 顶部产品概览表 `po-`*（Brand / Power Source / Item Weight / Maximum Pressure / UPC…）、
> ② Product information 键值表（技术规格 + 附加信息）、
> ③ Detail bullets 列表（"Label : Value"，书籍/3C 常见）、
> ④ 新版 Product facts 网格——按出现顺序合并、按标签别名归一去重
> （Brand / Brand Name / Manufacturer 视为同项；Product Dimensions / Item Dimensions L x W x H 视为同项）。
> **不同品类参数差异极大，脚本不预设固定字段**。若标准参数表缺失，但 bullets 中出现明确事实参数
> （如电池数量、续航分钟数、充电输入、水流量、重量、随附配件、O-ring/滤网等），必须从 bullets 做
> `derive_specs_from_bullets` 兜底抽取并合并到 `specs[]`。这类参数要保持页面原始数值与单位，不能改写成
> 无来源的卖点。只有标准参数表和 bullets 都没有可结构化事实时，`specs` 才允许为空，并需在报告口径里
> 说明「页面未提供可结构化产品参数」，不得静默让「产品参数」子区消失。

### 阶段 ②.4：评论数据来源决策（必触发）

**触发条件**：阶段 ② 完成后必做。目标是保证竞品分析默认有真实买家反馈参与，而不是只有页面视觉和 Amazon 全局评分。

**评论来源优先级**：

1. **用户提供完整评论文件**（`.json` / `.xlsx`）→ 直接作为权威评论样本，记为 `reviews_source = user_file`。
2. **用户只提供亚马逊 URL、未提供评论文件** → 必须调用 `linkfox-amazon-reviews`，按 `metadata.json.asin` 抓取目标 ASIN 评论样本，保存为 `<阶段①输出目录>/reviews_linkfox_raw.json`，记为 `reviews_source = linkfox_sample`。
3. **LinkFox 评论抓取失败**（未配置 `LINKFOXAGENT_API_KEY`、接口错误、目标站点不支持、0 条返回）→ 不阻塞三件套报告，但必须在报告第六节和最终回复中注明「评论样本未获取成功，仅使用 Amazon 页面全局评分口径」，且不得编造买家原话。

**站点路由**：

- URL 域名为 `amazon.com` → 使用 `linkfox-amazon-reviews/scripts/amazon_us_reviews.py`，参数固定 `marketplace:"US"`。
- 其它站点 → 使用 `linkfox-amazon-reviews/scripts/amazon_reviews.py`，按域名映射 `domainCode`：`amazon.co.uk → co.uk`、`amazon.de → de`、`amazon.fr → fr`、`amazon.it → it`、`amazon.es → es`、`amazon.co.jp → co.jp`、`amazon.com.au → com.au`、`amazon.com.br → com.br`、`amazon.com.mx → com.mx`、`amazon.ca → ca`、`amazon.nl → nl`、`amazon.se → se`、`amazon.ae → ae`。
- 若无法从 URL 判断站点，优先从 `metadata.json.source_url` 解析；仍无法判断时向用户确认，不要默认用加拿大站。

**自动抓取默认参数（最大化评论覆盖）**：

```powershell
# Windows / PowerShell 标准模板：先写 UTF-8 params.json，再用 --params-file。
# 不要把 JSON 直接内联到命令行；PowerShell 可能吞掉双引号。
$env:PYTHONIOENCODING="utf-8"
$outDir = "<阶段①输出目录>"
$paramsPath = Join-Path $outDir "reviews_params.json"
@{
  asin = "<metadata.asin>"
  marketplace = "US"
  star1Num = 100
  star2Num = 100
  star3Num = 100
  star4Num = 100
  star5Num = 100
  allStarsNum = 0
  sortBy = "recent"
  formatType = "all_formats"
} | ConvertTo-Json -Compress | Set-Content -LiteralPath $paramsPath -Encoding UTF8
python ".codex/skills/linkfox-amazon-reviews/scripts/response_io.py" run `
  --script ".codex/skills/linkfox-amazon-reviews/scripts/amazon_us_reviews.py" `
  --out-dir $outDir `
  --label "reviews_linkfox_raw" `
  --params-file $paramsPath

# 非美国站：params.json 使用 domainCode，并保留 all_reviews / all_contents / all_formats
$paramsPath = Join-Path $outDir "reviews_params.json"
@{
  asin = "<metadata.asin>"
  domainCode = "<站点代码>"
  star1Num = 100
  star2Num = 100
  star3Num = 100
  star4Num = 100
  star5Num = 100
  sortBy = "recent"
  reviewerType = "all_reviews"
  mediaType = "all_contents"
  formatType = "all_formats"
} | ConvertTo-Json -Compress | Set-Content -LiteralPath $paramsPath -Encoding UTF8
python ".codex/skills/linkfox-amazon-reviews/scripts/response_io.py" run `
  --script ".codex/skills/linkfox-amazon-reviews/scripts/amazon_reviews.py" `
  --out-dir $outDir `
  --label "reviews_linkfox_raw" `
  --params-file $paramsPath
```

`response_io.py run` 会输出落盘文件路径；只有 `exit_code=0`、`size_bytes>0`、且文件名以 `__reviews_linkfox_raw.json` 结尾的文件，才能作为后续 `<评论数据路径>`。失败文件会落为 `*.failed.json`，不得传给聚合、证据或看板脚本。若直接调用主脚本，也必须把完整 stdout JSON 写入 `<阶段①输出目录>/reviews_linkfox_raw.json`，不能只读取预览摘要。

> ⚠️ **评论抓取策略铁律（V3.2）**：默认目标是"尽量获取接口最大样本"，不是"快速正负各半样本"。US 站不要使用 `positiveNum + criticalNum + allStarsNum` 组合做默认参数；该组合可能被接口侧去重、忽略或按正负桶优先返回，实际只能得到约 100 条，且 `allStarsNum` 不会稳定额外叠加。默认必须走 `star1Num~star5Num` 各 100，并使用 `formatType:"all_formats"` 覆盖全部变体/格式。只有当用户明确要求"快速样本 / 正负各取 N 条 / 当前变体"时，才允许改用较小配额或 `current_format`。

> ⚠️ **Windows 中文路径与参数铁律（V3.3）**：不要用 `PowerShell here-string | python -`、`python -c "..."` 或 Node 包装器拼接包含中文的路径和 JSON；这些路径可能被当前控制台编码转成 `????`，也可能丢失 `LINKFOXAGENT_API_KEY`。统一使用上面的 `params.json + --params-file` 模板，并用 `Join-Path` / `-LiteralPath` 传路径。

> ⚠️ **失败文件污染铁律（V3.3）**：评论源文件必须从 `response_io.py` 本次 stdout 的 `file` 字段读取，或用 PowerShell 过滤：`Get-ChildItem <输出目录> -Filter '*__reviews_linkfox_raw.json' | Where-Object { $_.Length -gt 0 } | Sort-Object LastWriteTime -Descending | Select-Object -First 1`。禁止使用 `*reviews_linkfox_raw*.json` 宽匹配；它可能捞到 `.failed.json`、旧失败文件或空文件。

**LinkFox 返回体兼容**：

`review_core.py` 已兼容 LinkFox 原始响应 JSON：读取顶层 `data[]`，并归一化 `asin / title / text / rating / date / verified / attributes / domainCode`。因此 `reviews_linkfox_raw.json` 可直接喂给 `aggregate_reviews_json.py` / `build_review_dashboard.py` / `extract_review_evidence.py`，无需手工改字段名。

### 阶段 ②.5：外部完整评论 JSON 聚合（条件触发）

**触发条件**：存在可用评论数据路径：用户提供的"完整评论数据"文件（`.json` / `.xlsx`），或阶段 ②.4 自动抓取的 `reviews_linkfox_raw.json`。

> ⚠️ **核心规则（只分析目标 ASIN）**：用户给的 URL 里的 ASIN **就是要做竞品分析的目标产品**。==默认只分析该目标 ASIN 对应的评论==，文件内同系列其它 ASIN（不同款式 / 颜色）默认剔除——因为本次分析的对象是这一个竞品 listing，而非整个产品系列。
>
> 目标 ASIN 默认从 `metadata.json.asin` 自动解析（即 URL 对应的 ASIN）；脚本不传 `--asin` 时即按它过滤。
> 仅当用户**明确**要求"分析整个系列 / 全部款式颜色一起看"时，才加 `--all-variants` 逃生开关。

调用本 Skill 配套工具：

```powershell
# 默认：只分析 URL 对应的目标 ASIN（从 metadata.json 自动解析）—— 推荐
$env:PYTHONIOENCODING="utf-8"
python ".codex/skills/amazon-competitor-analyzer/scripts/aggregate_reviews_json.py" `
  --input "<评论数据路径 .json/.xlsx；或 reviews_linkfox_raw.json>" `
  --meta "<阶段①输出目录>/metadata.json" `
  --output "<阶段①输出目录>/reviews_aggregate.json"

# 也可显式指定目标 ASIN
python ".codex/skills/amazon-competitor-analyzer/scripts/aggregate_reviews_json.py" `
  --input "<评论数据路径>" --asin "<目标ASIN>"

# 仅当用户明确要分析整个系列时才加 --all-variants
python ".codex/skills/amazon-competitor-analyzer/scripts/aggregate_reviews_json.py" `
  --input "<评论数据路径>" --all-variants
```

获得（JSON · 与渲染器 `review-sentiment` 字段对齐）：

- `**global`（口径一 · 综合主口径，V3.1 新增）**：`{available, rating, rating_count, histogram[{star,percent}], avg, avg_from_histogram, low_star_ratio_percent}`。来自 `metadata.reviews` 的 Amazon 页面 global ratings，**覆盖全部评论**，是产品真实口碑分。报告综合评分（尤其第六维"预期管理"）一律取此口径。
- `**sample`（口径二 · 抓取样本挖掘口径，V3.1 新增）**：`{scope, total, avg, low_star_ratio_percent, caveat}`。受抓取星级配额放大低星，**仅用于挖抱怨主题，不可当产品综合分**。
- `scope`：`single_asin:<ASIN>`（默认，目标 ASIN）/ `all_variants`（仅 `--all-variants` 时）
- `distinct_asin_count` + `distinct_asin`：文件内 ASIN 分布（用于注明剔除了哪些同系列 ASIN）
- `total` / `avg` / `histogram[{star, percent}]` / `star_counts` / `low_star_ratio_percent`：**均为样本口径**（与 `sample` 块同源，保留为顶层是为兼容旧渲染器）
- `theme_summary`：各抱怨主题在全部 + 差评内的命中数（仅当传 `--themes` 时）
- `positive_keywords` / `critical_keywords`：好评 / 差评关键词云
- `real_voice_candidates`：真实买家原话候选（含 `stars` / `variation` / `asin`）

> ⚠️ **双口径不可混淆（V3.1 强化）**：聚合输出已**显式分离** `global`（全局综合，覆盖全部评论）与 `sample`（抓取样本，顶层 `total/avg/histogram` 同源）。脚本会在 stderr 打印偏差告警：当全局综合分与样本均分差 ≥ 1.0★ 时标 `⚠️ 偏差显著`。
>
> **抽样偏置原理**：LinkFox / 手动抓取每星级上限约 100 条；即便默认按 `star1Num~star5Num` 各 100 最大化抓取，也仍会相对 Amazon 全量评论放大低星占比（低星总量常小于高星但会被尽量抓满）→ 样本均分（如 2.5★）可能**远低于**真实综合分（如 4.4★）。**这不是产品变差，而是抽样口径不同。**
>
> **铁律**：报告综合评分一律取 `global`（如 4.4★）；样本（如 2.5★）只用于挖抱怨主题与真实原话，**禁止把样本均分/低星比当作产品综合评分写进报告**。报告「六」节必须分别标注两个口径（详见 §4 模板「六」）。

> ℹ️ **V3 数据驱动**：`aggregate_reviews_json.py` 已不再写死任何品类的痛点主题 / 好评差评关键词——关键词由 unigram+bigram 词频自动抽取，可泛化任意品类。主题改为**可选**：仅当 AI 按品类传入 `--themes themes.json`（格式 `{主题名:[关键词...]}`）时才统计主题命中，不传则跳过。

### 阶段 ②.6：交互式评论看板生成（条件触发 · 第 4 件套）

**触发条件**：与 ②.5 相同——存在用户提供的评论文件或阶段 ②.4 自动抓取的 LinkFox 评论样本。

本阶段产出**第 4 件套** `review_dashboard.html`：一个**完全离线、自包含**的交互式评论分析看板，从主报告 `index.html` 一键跳转（渲染脚本自动注入入口，见阶段 ⑤）。当评论样本量大（数百~数千条）时，静态 review-sentiment 卡只能给"快照"，看板则提供**可下钻的多维分析**。

调用本 Skill 配套工具：

```powershell
$env:PYTHONIOENCODING="utf-8"
python ".codex/skills/amazon-competitor-analyzer/scripts/build_review_dashboard.py" `
  --input "<评论数据路径 .json/.xlsx；或 reviews_linkfox_raw.json>" `
  --meta "<阶段①输出目录>/metadata.json" `
  --output "<阶段①输出目录>" `
  --aspects "<阶段①输出目录>/aspects.json" `   # ⚠️ 强制：智能问题归类表（见下 · 不传则校验 FAIL）
  --keywords "<阶段①输出目录>/keywords.json"   # ⚠️ 强制：中文策展词云（见下 · term 必须中文）
# 默认只分析 --meta 里的目标 ASIN（URL 对应竞品）
# 可选：--asin <显式指定ASIN> / --all-variants <分析整个系列> / --themes <主题配置 JSON>
```

### 阶段 ②.6.1：`aspects.json` + `keywords.json` 强制门（Agent 必做 · 校验硬拦截）

> ⚠️ **不传 `--aspects` → 看板不渲染「🧩 智能问题归类」→ `validate_report_consistency.py` FAIL**
> ⚠️ **不传 `--keywords` 或 `term` 非中文 → 词云回退英文自动分词 → 校验 FAIL**
> ⚠️ **顺序铁律**：`aspects + keywords 定稿` → `build_review_dashboard.py` → `extract_review_evidence.py` → 据证据写报告 → 渲染 HTML

**必须同时产出 `aspects.json`（智能问题归类表）**：光给关键词云不够——用户还得回去翻评论才知道"电池"到底在说续航差、易损坏还是要备用。你（AI）应**先读评论样本，把同类问题归类成「维度 → 子问题 → 关键词」三层结构**，写成 `aspects.json` 一并喂入。看板据此渲染「🧩 智能问题归类」面板：每个子问题显示命中量 + 低星比色条 + **一句定位到关键词上下文的代表性原话**，点击子问题即把下方「评论明细」筛成该问题的全部原话（下钻看"为什么"）。

> 空白起点可复制 `assets/templates/aspects_keywords_template.json`，拆成两个独立 JSON 写入输出目录。

`aspects.json` 结构（关键词用**去撇号小写**形式，看板会对评论做同样归一化，故 `wont charge` 可命中 `won't charge`）。**每个维度必须声明 `polarity` 情感极性**，避免"正面维度筛出差评"的语义错配——看板匹配时会做「关键词 + 星级」双门控：


| polarity | 含义      | 星级门控               |
| -------- | ------- | ------------------ |
| `pos`    | 正面体验维度  | 只匹配 **4-5★** 好评    |
| `neg`    | 问题/痛点维度 | 只匹配 **1-3★** 差评/中评 |
| `any`    | 中性（不限）  | 不做星级门控             |


新结构用 `{"polarity": ..., "issues": {子问题: [关键词...]}}`：

```json
{
  "🔋 电池 & 续航": {
    "polarity": "neg",
    "issues": {
      "续航短 / 掉电快": ["battery life", "runtime", "dies", "only last", "doesnt last"],
      "充电 / 电池故障": ["wont charge", "dead battery", "stopped charging"],
      "需要备用电池": ["second battery", "backup battery", "extra battery"]
    }
  },
  "👍 正面体验": {
    "polarity": "pos",
    "issues": {
      "便携 / 无线": ["portable", "cordless", "lightweight", "no cord"],
      "易用 / 方便": ["easy to use", "convenient", "user friendly"]
    }
  }
}
```

> 维度名建议带 emoji 前缀；子问题名要"一眼说清是什么问题"；正面体验维度务必设 `polarity:"pos"`、问题维度设 `"neg"`。关键词宁可多列同义/否定锚点（`not worth`、`waste of money`、`overpriced`）以提高召回。
> 兼容旧格式：若某维度直接写成 `{子问题:[词]}`（无 `polarity/issues` 包裹），看板会按维度名推断极性（名称含"正面/好评/优点/positive"等→`pos`，否则→`any`），但**新建议一律显式声明**。

#### 策展词云 `keywords.json`（强制 · agent 二次校正 · term 必须中文）

纯程序自动分词的关键词云有两个固有缺陷，**必须由 agent 介入二次判断**：

1. **语义误判**：否定合并出来的词（如 `not waste money`）字面像正面"不浪费钱"，实际在差评里是 `Don't waste your money`（别买）。机器分不清，只有**读了原文**才能定性。
2. **碎片/歧义词**：`good`、`water`、`hose` 这类词单独出现毫无信息量，却高频上榜。

因此在生成看板前，你（AI）应：**①先跑一遍或预估自动词云 → ②抽样阅读对应评论原文确认真实语义 → ③把关键词归并成「可读中文标签 + 真实匹配子串」，并按真实情感极性放进 `pos`/`neg`**，写成 `keywords.json`。传入 `--keywords` 后，看板用策展词云**覆盖**该极性的自动词云（只传 `pos` 则 `neg` 仍自动）。

```json
{
  "pos": [
    {"term": "喜欢 / 推荐", "match": ["love it", "i love", "great", "recommend", "nice"]},
    {"term": "好用 / 方便", "match": ["easy to use", "convenient", "user friendly"]}
  ],
  "neg": [
    {"term": "不工作 / 故障", "match": ["not work", "doesnt work", "stopped working"]},
    {"term": "别买 / 纯浪费钱(非\"不浪费钱\")", "match": ["waste your money", "waste of money", "dont waste"]}
  ]
}
```

- `term`：词云上显示的可读标签（建议中文）；`match`：**去撇号小写的真实子串**列表（命中任一即算），故 `dont waste` 可命中 `don't waste`。
- 计数与点击口径一致：`pos` 条目计于 **4-5★** 评论、`neg` 计于 **1-2★** 评论；点击某词即把「评论明细」筛成"该极性星档 + 命中任一 match 子串"的评论——**count 与底部条数严格相等，绝不会出现"点了却 0 条"**。
- 关键：用 `match` 真实子串而非合成 token，根治了"自动词 `not waste money` 在原文非连续子串、点击筛不出评论"的 bug。即便不传 `--keywords`，自动词云的点击也已改为「词元集合命中 + 极性星档」匹配，同样保证 count==底部条数。

#### 主报告的优缺点必须「逐条取全样本」再综合（`extract_review_evidence.py`）

⚠️ **强制**：竞品报告（`competitor_analysis.md/.html`）里的「评论情感解析 / 优缺点证据分布 / 行动结论」**不得靠抽几条评论拍脑袋**，必须先用工具把**每个优缺点对应的全部评论**提取出来，再据实综合。

```powershell
$env:PYTHONIOENCODING="utf-8"
python ".codex/skills/amazon-competitor-analyzer/scripts/extract_review_evidence.py" `
  --input "<评论数据路径 .json/.xlsx；或 reviews_linkfox_raw.json>" `
  --meta "<阶段①输出目录>/metadata.json" `
  --keywords "<阶段①输出目录>/keywords.json" `
  --aspects "<阶段①输出目录>/aspects.json" `
  --output "<阶段①输出目录>"
```

- 产出 `review_evidence.json`：对 `keywords.json` 每个优缺点分组、`aspects.json` 每个维度子问题，给出 **命中量 / 均分 / 低星比 / 星级分布 / 代表原话 / 命中的全部评论原文**；匹配口径与看板点击**完全一致**（`keywords.pos`→4-5★、`keywords.neg`→1-2★、`aspects` 维度按 polarity 门控），故 count == 看板底部条数。
- stdout 同时打印可读摘要（每组命中量 + Top3 原话）。**你（AI）据此摘要 + 通读 `review_evidence.json` 里的全样本评论**，写出带真实命中量的优缺点综合（如「水压太弱差评 35 条、含中评共 48 条」），落到 `visual.json` 的 `review-sentiment` 关键词 `count` / `gap_table` / 新增「优缺点证据分布」`two-column-list` / `action-cards`，并同步 `.md`。
- 顺序：先 `aspects.json` + `keywords.json` 定稿 → 跑 `extract_review_evidence.py` → 据证据重写报告优缺点 → 渲染 HTML。

看板内容（全部随筛选实时联动）：

- **顶部 KPI**：评论数 / 平均星级 / 低星比(1-2★) / VP 认证占比
- **月度趋势**（评论量柱 + 均分线）——**拖动下方时间轴手柄即可框选时间范围**，全看板联动重算（核心交互）
- **星级分布 / 变体款式 / 国家站点 / VP 对比 / 评论长度分布**——点击任一图元即作为筛选条件；评论长度分布支持 `0-50 / 51-150 / 151-300 / 301-600 / 600+` 五档点击筛选，选中档位会在顶部 chips 回显并联动明细
- **评论关键词云**（好评绿 4-5★ / 差评红 1-2★ · 点击关键词联动全看板）——默认数据驱动自动分词；传入 `--keywords` 后用 **agent 二次校正的策展词云**覆盖（修正语义误判、归并碎片词）。点击任一词即筛出"该极性星档 + 命中评论"，**count 与底部明细条数严格一致**
- **痛点主题分布**（仅当传入 `--themes` 时显示）
- **🧩 智能问题归类**（仅当传入 `--aspects` 时显示）——维度→子问题分层，维度头带 `好评/差评中评` 极性标签；每个子问题带命中量 + 色条（正面维度绿、问题维度按低星比红）+ 关键词上下文原话；点击子问题即下钻到「评论明细」看全部相关原话。**关键词 + 星级双门控**：正面维度只算好评、问题维度只算差评/中评，杜绝"勾选正面体验却筛出差评"的语义错配
- **评论明细表**（展示当前筛选范围内的真实评论，体现"框选范围的数据表现"，列可排序）
  - 自带**快速筛选条**：星级预设（差评 1-2★ / 中评 3★ / 好评 4-5★）+ 单星级开关（1★~5★）+ VP 下拉 + 评论长度下拉 + 关键词搜索框；与全局 state 同源，点选即联动全看板并回显高亮，亦在顶部 chips 反映
  - **正文完整展示**：明细表保留完整评论原文（封顶 5000 字符防极端长文），直接自然换行完整显示，不再用「展开全文」折叠；关键词云 / 搜索 / 智能归类的匹配文本同步放长到 5000 字符以提高召回
- 顶部筛选 chips + 「重置全部筛选」按钮；底部双口径说明（样本口径 vs Amazon 全局评分主口径）

> ⚠️ **离线约束**：看板内联了本地 `assets/echarts.min.js`，生成后双击即可打开、不依赖网络；文件可随输出目录整体移动。
> ⚠️ **看板不替代主报告**：`review_dashboard.html` 是辅页面（看数据），`index.html` 仍是主交付（看结论 + 评分）。两者通过跳转按钮互联。

### 阶段 ②.8：关键词架构与流量入口采集（详细报告必尝试）

**触发条件**：详细报告模式下必须尝试。环境配置了 `LINKFOXAGENT_API_KEY`（与评论抓取同一把钥匙）时必须执行；缺失或接口失败时可继续三件套，但必须在报告/最终回复中说明原因，不能静默省略。

为报告补上「关键词架构」与「流量入口」两条分析线，数据来自已安装的 LinkFox SIF skill（沿用同一 API Key、无需店铺授权）：

```powershell
$env:PYTHONIOENCODING="utf-8"
# 单 ASIN（单 URL 流程）
python ".codex/skills/amazon-competitor-analyzer/scripts/fetch_keyword_traffic.py" `
  --asin "<metadata.asin>" --outdir "<阶段①输出目录>" --country US
# 多 URL：自动发现 _compare 目录下全部 ASIN 子目录，summary 批量一次 ≤10 个
python ".codex/skills/amazon-competitor-analyzer/scripts/fetch_keyword_traffic.py" `
  --compare-dir "生成结果输出/amazon图片提取/_compare_<时间戳>" --country US
```

底层接口（脚本已封装，无需手调）：

- `linkfox-sif-asin-keywords`（`/sif/asinKeywords`，单 ASIN 反查流量词：自然/广告排名、周搜索量、流量占比、展示位、特征标记）→ 关键词架构
- `linkfox-sif-asin-summary`（`/sif/asinSummary`，一次 ≤10 ASIN，曝光来源构成：自然/SP/SB/SBV/AC/ER/TR 占比 + 各类关键词数 + 周期新进/退出）→ 流量入口

产出（写入各 ASIN 目录）：

- `keyword_arch.json`：Top 流量词表 + 自然/广告词数 + 自然/付费流量占比 + 头部词搜索量
- `traffic_source.json`：曝光构成占比 + 关键词数 + 周期对比
- （多 URL 模式额外在 compare 根目录写 `kw_traffic_index.json`，供综合看板 viz_data 回填）

报告消费：把 `keyword_arch.json` → visual.json 的 `keyword-arch` section（章节「三-3」）；`traffic_source.json` → `traffic-entry` section（章节「三-4」）。两章置于 `info-layers`（三-2）之后、`two-column-list`（四）之前，不进入收尾四联与 V4 客户洞察块。只要对应 JSON 存在，`validate_report_consistency.py` 会强制检查 section 必须出现且顺序为 `info-layers → keyword-arch → traffic-entry → two-column-list`。

> ℹ️ 可选增强：`linkfox-aba-data-explorer`（市场级蓝海词，NL 查询）、`linkfox-sif-keyword-traffic`（词级竞品流量拆解）、`linkfox-product-title-analyze`（标题属性结构，LLM 型）。首版不纳入主链路，按需手动调用。

### 阶段 ③：模块化拆解（可选）

A+ 模块数 ≥ 4 时强烈建议执行：调用 `layout-reference-analyzer`，把 `aplus_vertical.png` 当版式参考图，逐模块输出"模块编号 + 信息载荷 + 视觉权重"，作为阶段 ④ "信息层级"评分的事实依据。

### 阶段 ④：五维评分（核心）

每项 0-5 星（可半星），最终加权总分按下表权重：


| 维度                     | 权重   | 评分要点                                                        |
| ---------------------- | ---- | ----------------------------------------------------------- |
| **视觉一致性**              | 0.20 | 主色调统一度、字体节奏、模特/场景调子、A+ 与套图协调度                               |
| **信息层级**               | 0.15 | 首图 → 卖点 → 场景 → 规格 → 信任状的层级递进是否清晰、是否有"信息泥潭"                  |
| **图文契合度**              | 0.15 | 每个模块的文字是否被画面有效承接；是否存在"图说一套、文字另一套"                           |
| **连贯叙事效率**             | 0.10 | 顺序读下来是否构成连贯故事；模块过渡是否自然；A+ 与套图是否串得起来                         |
| **品牌沉淀**               | 0.15 | Logo/字体/口号/视觉符号的出现频率与一致性；是否容易被记忆                            |
| **预期管理 / 用户筛选**（V2 新增） | 0.25 | 是否明确"适合谁"前置筛选；卖点宽度是否聚焦（避免错配高预期人群）；尺码/体验风险是否前置化解；是否会引起预期偏差差评 |


**加权总分**：`Total = 视觉一致性*0.20 + 信息层级*0.15 + 图文契合度*0.15 + 连贯叙事效率*0.10 + 品牌沉淀*0.15 + 预期管理*0.25`，结果 0-5，保留 1 位小数。

> ⚠️ **第 6 维「预期管理」权重最高**：竞品分析的真正价值是判断页面"会不会卖、会不会引来差评"，而不是"好不好看"。「卖点打得太宽 / 预期拉得太高 / 该挡的高预期用户没挡住」是 Amazon listing 失血最快的伤口。

**刚性评分锚点**（防止打分浮动）：


| 现象                                                            | 强制限分         |
| ------------------------------------------------------------- | ------------ |
| 主色调跨 3+ 完全无关色系（套图/A+ 调子完全断裂）                                  | 视觉一致性 ≤ 2.5  |
| A+ 模块超过 6 个且无明显层级分段                                           | 信息层级 ≤ 2.5   |
| 出现"功能 claim 但画面无承接"模块                                         | 图文契合度 ≤ 3.0  |
| A+ 模块顺序仅按"风格图堆叠"，无叙事递进                                        | 连贯叙事效率 ≤ 2.5 |
| 整个 A+ 仅在最后 1 个模块出现品牌名/Logo                                    | 品牌沉淀 ≤ 2.5   |
| 视频封面与品牌主调严重不一致                                                | 品牌沉淀 ≤ 3.0   |
| 全页**无 Best For / 适合谁 / 不适合谁** 任何前置筛选                          | 预期管理 ≤ 2.5   |
| 卖点笼统（Soft / Stretchy / Comfortable 等口号化表达）超过卖点总数 50%          | 预期管理 ≤ 3.0   |
| 尺码图 / 身材建议出现在 A+ 最末位（即用户已往下翻完才看到）                             | 预期管理 ≤ 3.0   |
| Shapewear / Fit-critical 类目 0 张"穿前 vs 穿后" / "塑形区域示意" / "体型对比" | 预期管理 ≤ 3.0   |


### ⚠️ 关键概念辨析：买家秀（Customer Photos）

评分前必须辨别 A+ 中是否存在"买家秀"模块——但**"买家秀"有两种定义**，**不可混淆**：


| 类型                    | 定义                                         | 能否出现在 A+                          | 视觉特征                                                                                                              |
| --------------------- | ------------------------------------------ | --------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **真买家秀 / Real UGC**   | Customer Reviews 区 verified purchase 用户上传图 | **永远不可能**——Amazon 政策禁止 A+ 含用户原创素材 | N/A                                                                                                               |
| **准买家秀 / Pseudo-UGC** | 品牌方策划的 UGC 化内容：① KOL/网红合作 ② 品牌自拍但刻意做成生活感街拍 | **可以且常见**——头部品牌补足"真买家秀缺位"的标准打法    | 自然光 / 非棚拍场景（咖啡馆、街边、户外）/ 多元 KOL（肤色/发色/体型差异）/ 姿态自然 / Instagram 风 / 常用 tab 切换形态（如 "Everyday X / Effortless Y" 双 tab） |


**评分时禁止说"零买家秀"——必须明确指出**：

- 准买家秀做了 ✓ → 评估其品牌锚点埋入度（是否有边框 / 角标 / 字幕条带品牌字 / KOL @ 标签 / "Customer styled" 注释）
- 准买家秀没做 ✗ → 才能说"买家秀模块缺位"

**Pseudo-UGC 模块判定信号**（命中 ≥ 3 项即可判定）：

1. 拍摄场景非纯白棚拍背景（咖啡馆/街边/户外/家居场景）
2. 模特姿态自然非定型（坐吧台 / 走路抓拍 / 手扶头发等）
3. 多张图模特肤色/发色/发型差异明显（≥ 3 种）
4. 出现 tab 切换控件（如 "Everyday Glow / Effortless Chic" 双 tab）
5. 拍摄构图带"博主分享感"（手机竖拍比例 / Instagram 滤镜感 / 排版像贴纸）
6. 标签文字偏感性叙事（"day-to-night" / "real wear" / 风格名词 vs 功能描述）

### 阶段 ④.4：客户洞察（5W2H + 客户画像 + Kano + 产品开发注意点 · V4 新增）

> 竞品分析的终极目的不只是"它的页面做得好不好"，而是"它的客户是谁、为什么买、真正想要什么，以及我做本品时该注意什么"。本阶段把视觉/评分层面的分析，向上拉到**消费者购买决策**与**产品需求**层面。
>
> ⚠️ **事实驱动铁律**：本阶段所有结论必须从已采集的事实推断——`metadata.json`（bullets / specs / 变体 / 价格）、阶段 ②.7 的 `review_evidence.json`（全样本评论证据）、`reviews_aggregate.json`（关键词 + 真实原话）。**禁止凭空虚构客户画像或需求**；每条推断尽量挂一条证据（评论原话 / 变体分布 / 页面卖点关键词）。评论样本不可用时，本阶段降级为"仅基于页面定位 + bullets 的推断"，并在报告中注明。

#### ① 5W2H 购买行为分析

用 7 个问句把竞品的"购买逻辑"拆开，回答"它在卖给谁、卖什么、何时何地、为何买、怎么决策、卖多少钱"：

落到 `visual.json` 时，每张卡必须有三层信息：`key`（Who/What/When/Where/Why/How/How much）、中文标题（`zh` 或 `label`）、正文（`finding` 或 `value`）。渲染器兼容新旧字段，但校验器会拦截只有英文 key、没有正文的空心卡。


| 维度               | 问句                            | 数据来源                                                  |
| ---------------- | ----------------------------- | ----------------------------------------------------- |
| **Who** 谁在买      | 目标买家是谁（年龄/身份/身材/使用群体）？        | 模特受众 + 评论中自述（"my wife"/"postpartum"/"for work"）+ 变体偏好 |
| **What** 买什么     | 买的是产品本身还是某个解决方案 / 情绪价值？       | bullets 主卖点 + 评论高频赞点                                  |
| **When** 何时买     | 购买/使用时机（季节、场合、生命阶段：产后/婚礼/健身）？ | 评论场景词 + 节庆/季节信号                                       |
| **Where** 在哪用    | 使用场景与渠道（日常通勤/居家/健身房/正式场合）？    | 评论场景 + A+ 场景图                                         |
| **Why** 为何买      | 核心购买动机与待解决痛点（塑形/遮肉/舒适/自信）？    | 差评里"原本想解决但没解决" + 好评里"终于解决了"                           |
| **How** 怎么决策     | 决策路径与顾虑（看尺码表/对比变体/担心退货）？      | 评论中的对比/退货/尺码纠结原话                                      |
| **How much** 花多少 | 价格敏感度与心理价位（嫌贵/觉得值/对比同类）？      | 价格 + 评论里 "worth it"/"overpriced"/"cheap feel"         |


→ 落到 visual.json 的 `w5h2-grid`（7 张卡），md 对应「四-Y」。

#### ② 客户画像（Persona）

从 5W2H + 评论聚类中提炼 **1-3 个**典型买家画像，每个画像有名有姓、可被设计/产品团队直接代入：

- **画像名 + 头像 emoji**（如「产后修复妈妈 · Maria 🤱」）
- **标签**：年龄段 / 身份 / 价格敏感度 / 身材或场景特征
- **人群画像 / 典型场景 / 核心动机 / 主要顾虑**
- **一句代表性买家原话**（直接取自评论证据，强化真实感）

→ 落到 visual.json 的 `persona-cards`，md 对应「四-Z」。**画像数量按评论聚类自然产生，宁缺毋滥，2 个聚类清晰的画像优于 5 个雷同画像。**

#### ③ Kano 模型真实需求

把买家需求按卡诺模型分到五类，指导"先保命、再拉分、后造爆点"：


| Kano 类别  | 英文              | 判定信号（从评论反推）                      | 产品含义               |
| -------- | --------------- | -------------------------------- | ------------------ |
| **基本型**  | Must-be         | 差评里"理应有却没有/坏了"（漏水、线头、尺码不准、味道大）   | 缺失即差评，必须先做到，做到也不加分 |
| **期望型**  | One-dimensional | 好评差评都围绕"越X越好"（越软越好/塑形越强越好/越透气越好） | 越做越满意，是拉开评分差距的主战场  |
| **兴奋型**  | Attractive      | 好评里的"惊喜/没想到"（送收纳袋、隐形不显痕、可双面穿）    | 超预期爆点，差异化机会，但勿当基本功 |
| **无差异型** | Indifferent     | 页面强调但评论几乎不提的卖点                   | 别过度投入资源/版面         |
| **反向型**  | Reverse         | 做了反而招黑（过度包装、过强压缩导致不适、过多功能堆叠）     | 谨慎，做了可能引发反感        |


→ 落到 visual.json 的 `kano-model`（按类别分组），md 对应「四-K」。**至少覆盖基本型 + 期望型 + 兴奋型三类**（无差异/反向有则补，无则省）。

#### ④ 产品开发注意点

把上面三块洞察收敛成"我做本品时的可执行清单"，带优先级与依据：

- **优先级**：`P0`（必须修复/保命，对应 Kano 基本型失守）/ `P1`（拉分项，对应期望型）/ `P2`（差异化爆点，对应兴奋型）
- **类型**：`must-fix` 必须修复 / `improve` 持续改进 / `innovate` 创新爆点
- **每条挂依据**（来自哪条差评/哪个 Kano 结论/哪个 5W2H 洞察）

→ 落到 visual.json 的 `dev-watchpoints`，md 对应「四-D」。

> ℹ️ **位置约束**：上述四块在 visual.json 中**统一插入到 `best-for-grid`（四-X）之后、`metric-grid`（五 品牌沉淀）之前**，绝不可插入收尾四联（`metric-grid → review-sentiment → score-cards → action-cards`）中间，否则 `validate_report_consistency.py` 会 FAIL。详见 §4.1 编排顺序。

### 阶段 ⑤：报告输出（**三件套必出**）

⚠️ **强制规范**：每次竞品分析必须在同一目录下产出**三件套**，缺一不可：

```
<阶段①输出目录>/
├─ competitor_analysis.md    # ① Markdown 报告（人类可读全文，按 §4 模板）
├─ visual.json               # ② 可视化数据契约（按 §4.1 数据契约，控制 HTML 卡片）
├─ index.html               # ③ 最终 HTML 报告（由前两者渲染生成 · 旧名 competitor_analysis.html 已改为 index.html）
├─ review_dashboard.html     # ④ 交互式评论看板（条件：存在用户评论文件或 LinkFox 评论样本 · 阶段 ②.6）
├─ reviews_data.js           #    └ 看板评论数据（script src 外链，须与看板同目录一起转发）
├─ reviews_linkfox_raw.json   #    └ LinkFox 自动抓取的评论原始响应（条件：用户未提供评论文件时）
├─ reviews_aggregate.json     #    └ 评论聚合摘要（条件：存在用户评论文件或 LinkFox 评论样本）
├─ aspects.json              #    └ 智能问题归类表（agent 产出，喂 --aspects）
├─ keywords.json             #    └ 策展词云（agent 二次校正产出，喂 --keywords）
└─ review_evidence.json      #    └ 各优缺点逐条命中的全样本评论证据（report 优缺点综合的依据）
```

> 第 ④ 件套 `review_dashboard.html` **在存在评论数据时产出**：包括用户提供完整评论文件，或阶段 ②.4 通过 `linkfox-amazon-reviews` 自动抓取到评论样本。只有在评论抓取失败 / 0 条 / 用户明确要求跳过评论时，才可只产三件套。渲染脚本检测到同目录存在 `review_dashboard.html` 时，会自动在主报告 hero 注入"📊 交互式评论看板"跳转按钮 + 右上角浮动入口。
> 看板评论数据外链在 `reviews_data.js`（兼容 file:// 双击直开），**转发时须与 `review_dashboard.html` 同目录一起带上**。`aspects.json` / `keywords.json` 是 agent 校正产物，建议一并保留以便复现/迭代。

**多 URL 任务下的产出规模对照表**（N ≥ 2 时强制）：


| 输入 URL 数 | 本 Skill 强制产出              | 用户选"对比总结"时追加（由独立 Skill 出） | 合计上限         |
| -------- | ------------------------- | ------------------------- | ------------ |
| 1 个      | 1 套单品三件套（3 文件）            | —                         | 3 文件         |
| 2 个      | **2 套单品三件套**（独立目录 · 6 文件） | 1 套综合可视化沉淀（2 文件）          | 8 文件         |
| 3 个      | **3 套单品三件套**（9 文件）        | 1 套综合可视化沉淀（2 文件）          | 11 文件        |
| N 个      | **N 套单品三件套**（N × 3 文件）    | 1 套综合可视化沉淀（2 文件）          | N × 3 + 2 文件 |


> "用户选对比总结时追加"由 `amazon-multi-asin-visual-synthesizer` 完成，**不归本 Skill 产出**——本 Skill 的强制交付物只有 N 套单品三件套。

> 工作量预算（仅参考）：单个 SKU 的阶段 ⑤ 约消耗 8-15 分钟 token 预算（md ~1500 字 + visual.json ~400 行 + 渲染校验）。N 个 SKU 直接乘以 N。**如果预算紧张，正确做法是 `request_user_input` 与用户拆批次，而不是擅自降级为口头评分**。

**为什么三件套都必须**：

- 只产 md → HTML 会回退到启发式渲染，下半部分是大段纯文字 Markdown 全文（用户不喜欢）
- 只产 visual.json → 没有人类可读的全文存档，无法回看原始分析推理
- 必须三件套同步产出，HTML 才能纯卡片化、信息又有 md 兜底

**Amazon 原网址跳转（V2.4 新增 · 自动）**：

- HTML 渲染脚本会自动从 `metadata.json.source_url` 读取原始商品 URL，并在页面三处注入跳转入口：
  1. **顶部 Hero 横幅右侧** — 醒目的橙色"🛒 在 Amazon 打开 ↗"胶囊按钮
  2. **基础信息卡 ASIN 行** — ASIN 值自动变成可点击链接（鼠标悬浮变橙）
  3. **页面右上角浮动悬浮按钮** — 滚动到任意位置都可一键回原网址
- 全部链接默认 `target="_blank" rel="noopener"`（新窗口 + 安全隔离）
- `metadata.json.source_url` 缺失或为空时三处入口自动隐藏，不破坏页面布局
- 此特性无需 visual.json 或 markdown 显式声明，只要阶段 ② `extract_metadata.py --url <URL>` 正常执行即可生效

**默认行为**：

- `visual.json` 存在且含 `sections` 时，HTML 默认**隐藏** Markdown 全文区（整页全卡片）
- 若 AI 特别想让 HTML 同时保留 md 全文做参照，可在 visual.json 顶层显式写 `"hide_full_markdown": false`
- `visual.json` 缺失时，渲染器会向终端打印警告，提示补 json

**发布前一致性校验（强制）**：

```powershell
python ".codex/skills/amazon-competitor-analyzer/scripts/validate_report_consistency.py" `
  --dir "<阶段①输出目录>"
```

校验不通过（FAIL）时，不得直接交付给用户，必须先修正：

- 总分一致性：`visual.json.summary` vs `competitor_analysis.md` vs `index.html`
- Logo 次数一致性：`visual.json.evidence.logo_mentions` vs HTML 展示值
- `visual.json` BOM 污染（会导致渲染回退）
- HTML 回退痕迹（出现 `content-card` 表示仍在渲染 Markdown 全文）
- 图片可见性：`report.json` 存在且引用真实图片；`metadata.media.gallery_count / aplus_module_count` 非空；`index.html` 不得出现 `class="gallery-main" src=""`；HTML 必须引用 `report.json` 的首张套图和首张 A+ 图片。

多 ASIN 批量交付时，除上述单品校验外，还必须运行 `amazon-multi-asin-data-auditor`。该审计脚本会额外检查 `report.json`、图片相对路径、`metadata.media` 和单品 HTML 图片引用，任何 FAIL 都必须先修复再进入综合看板。

**Sections 顺序合规**（脚本会强制校验，FAIL 时拦截交付 · V2.2）：

- `sections[0]` 是 `verdict-headline`
- `sections[1]` 是 `kv-table`（基础信息卡，**严禁放末三位**）
- `sections[-1]` 是 `action-cards`（章节「八」，行动结论收尾）
- `sections[-2]` 是 `score-cards`（章节「七」，关键评分紧贴 action-cards 之前）
- `sections[-3]` 是 `review-sentiment`（章节「六」，紧贴 score-cards 之前）；当 `metadata.reviews.available=false` 时则降级为 `metric-grid`
- 收尾四联（含 review）必须严格相邻：`metric-grid → review-sentiment → score-cards → action-cards`

> ⚠️ 全部由 `validate_report_consistency.py` 强制校验（V2.2 起），违反任一条即 FAIL。`review-sentiment` 不再位置自由，**章节「六/七/八」三联硬锁定**。

按下方 §4 的标准模板输出 md，按 §4.1 的数据契约（**含 Sections 编排顺序硬约束**）输出 visual.json，最后调用 §4 末尾的 PowerShell 命令渲染 HTML。

## 4. 标准报告模板

输出主文件为 HTML（便于直观阅读），同时保留 Markdown 源文件，**始终中文**（技术字段如 ASIN/HEX/BSR 保留原样）。报告文件保存为：

```
<阶段①输出目录>/index.html
<阶段①输出目录>/competitor_analysis.md
```

模板正文：

```markdown
# 竞品分析 · {{编号}} · {{品牌}} {{品类简称}}

## 〇、问题本质（开门见山 · 强制 30-60 字 · V2 新增）

> {{problem_essence_punchline}}

> ⚠️ 该字段是报告"心脏"：必须在 1-2 句话内点出本 listing 当前**最致命的策略问题**。
> 必须命中以下视角之一（多选）：
> - 卖给谁错位（吸引了不该来的人）
> - 预期管理失败（页面拉高了用户预期，体验跟不上）
> - 体验沟通失误（尺码 / 久穿 / 透视 / 穿脱 等关键体验未化解）
> - 流量与转化脱节（类目流量 vs 页面叙事不对齐）
> - 卖点宽度问题（散点式罗列 vs 一条强主线）
>
> 示例（不必照抄）：
> "页面表达没有把正确用户和正确预期管理到位——卖点打得太宽，预期拉得太高，尺码和体验沟通不够精确。"

## 一、Basic Page Section 基础信息

| 项 | 值 |
|---|---|
| ASIN | {{asin}} |
| 品牌 / 星级 | {{brand}} / {{rating}} ★ ({{rating_count}} 评价) |
| 类目排名 | {{category_rank[0]}} |
| 价格信息 | 主报价：{{price.current}} {{price.currency}}（{{price.main_offer_status}}）；变体起售价：{{price.variant_from_price}} {{price.variant_from_currency}} |
| 变体（色 / 码） | {{variations.colors.count}} 色 / {{variations.sizes.count}} 码 |
| 套图数 / A+ 模块数 | {{gallery_count}} / {{aplus_module_count}}（含视频封面 × {{video_cover_count}}） |

## 二、风格五标签（视觉直觉判断）

| 维度 | 判断 |
|---|---|
| 色彩应用 | {{color_palette_summary}} |
| 模特/受众 | {{model_demographic}} |
| 摄影风格 | {{photo_style}} |
| 整体调性 | {{tone_brief}} |
| 拍摄方式 | {{shooting_method}} |

## 三、内容逻辑（A+ 分层拆解）

> 他们想传达什么？他们怎么做的？

**卖点排序 · 三层递进**：
1. {{中文短标题_1}} → {{一句中文副说明_1}}
2. {{中文短标题_2}} → {{一句中文副说明_2}}
3. {{中文短标题_3}} → {{一句中文副说明_3}}

写法要求：这里不是复制 Amazon bullet。必须把 bullets / 套图 / A+ 中重复出现的卖点合并成 3 条中文决策摘要。每条格式为“短标题 + 副说明”：标题不超过 16 个中文词，副说明不超过 35 个中文词；允许保留 MagSafe、N52/N55、96 LBS、360° 等必要术语，但不得出现整段英文原文。

**信息层级 · A+ 分层拆解**：
- 第一层 · 主体写真 / 视觉风格 → {{A+ 首屏与主视觉在传达什么}}
- 第二层 · 功能与定位展示 → {{核心功能如何被模块化证明}}
- 第三层 · 信任状 / 兼容警告 → {{参数、适配边界、风险说明如何承接}}

写法要求：A+ 模块数 ≥ 3 时必须输出三层拆解，且必须紧跟卖点排序之后。每层是中文“层级名 + 一句说明”，用于回答“用户先看到什么、再被证明什么、最后被提醒什么”。不得把所有 A+ 图信息揉成一段。

## 四、用户视角（消费者关注 vs 卖家诉求）

**关注消费者**没有提到、但他们打开了：
- {{customer_unspoken_1}}
- {{customer_unspoken_2}}

**卖家用了哪些词强化诉求**：
- "{{keyword_1}}" / "{{keyword_2}}" / "{{keyword_3}}" / ...

**用户视角差**：{{customer_seller_gap}}

## 四-X、适合谁 / 不适合谁（V2 新增 · 预期管理视角）

> 这是判断"会不会引来差评"的关键章节。即便页面做得漂亮，吸引了不该来的人也会被打 1-2 星。

**适合人群**（页面应该主动筛选进来的用户特征）：
- {{best_for_1}}
- {{best_for_2}}
- {{best_for_3}}

**应规避人群**（页面应该主动挡掉的高预期错配用户）：
- {{not_for_1}}
- {{not_for_2}}

**当前页面是否在做这个筛选**：{{filtering_done}}（已做 / 部分做 / 未做）

## 四-Y、客户购买行为（5W2H · V4 新增）

> 用 5W2H 拆解"它在卖给谁、卖什么、何时何地、为何买、怎么决策、卖多少钱"。每条尽量挂证据（评论原话 / 变体分布 / bullets 关键词）。

| 维度 | 该维度的发现 | 依据 |
|---|---|---|
| **Who** 谁在买 | {{w_who}} | {{w_who_ev}} |
| **What** 买什么 | {{w_what}} | {{w_what_ev}} |
| **When** 何时买 | {{w_when}} | {{w_when_ev}} |
| **Where** 在哪用 | {{w_where}} | {{w_where_ev}} |
| **Why** 为何买 | {{w_why}} | {{w_why_ev}} |
| **How** 怎么决策 | {{h_how}} | {{h_how_ev}} |
| **How much** 花多少 | {{h_howmuch}} | {{h_howmuch_ev}} |

## 四-Z、客户画像（Persona · V4 新增）

> 从 5W2H + 评论聚类提炼 1-3 个典型买家，有名有姓、可直接代入设计/产品工单。

**画像 1 · {{persona_1_name}}**
- 标签：{{persona_1_tags}}
- 人群画像：{{persona_1_demographic}}
- 典型场景：{{persona_1_scenario}}
- 核心动机：{{persona_1_motivation}}
- 主要顾虑：{{persona_1_pain}}
- 代表原话："{{persona_1_quote}}"

（如有画像 2 / 画像 3，按同结构追加）

## 四-K、客户卡诺模型（Kano）真实需求（V4 新增）

> 把买家需求分到五类，指导"先保命、再拉分、后造爆点"。每条尽量挂评论证据。

**基本型需求（Must-be · 缺失即差评）**：
- {{kano_mustbe_1}}（依据：{{kano_mustbe_1_ev}}）
- {{kano_mustbe_2}}

**期望型需求（One-dimensional · 越好越满意）**：
- {{kano_perf_1}}（依据：{{kano_perf_1_ev}}）
- {{kano_perf_2}}

**兴奋型需求（Attractive · 超预期爆点）**：
- {{kano_attractive_1}}（依据：{{kano_attractive_1_ev}}）

**无差异 / 反向型需求**（有则补，无则省）：
- {{kano_indifferent_or_reverse}}

## 四-D、产品开发注意点（V4 新增）

> 把上面三块洞察收敛成做本品时的可执行清单，带优先级与依据。

- **P0**（必须修复 / 保命，对应 Kano 基本型失守）：{{dev_p0}}（依据：{{dev_p0_ev}}）
- **P1**（拉分项，对应期望型）：{{dev_p1}}（依据：{{dev_p1_ev}}）
- **P2**（差异化爆点，对应兴奋型）：{{dev_p2}}（依据：{{dev_p2_ev}}）

## 五、品牌沉淀

- Logo / 字体 / 主视觉符号出现位置：{{brand_asset_locations}}
- 品牌识别度：{{brand_recognition_grade}}
- 是否有可被记住的视觉锤：{{visual_hammer_status}}

## 六、评论情感解析 · 数据印证（V2.2 起固定为第六节）

> 紧跟「五 · 品牌沉淀」之后、「七 · 关键维度评分」之前。用真实评论数据印证前面所有定性结论，让评分有据可依。`metadata.reviews.available=false` 时本节可省略，否则必出。

> ⚠️ **双口径标注（V3.1 · 强制升级）**：当存在用户完整评论文件或 LinkFox 自动抓取评论样本时，本节必须**分别标注两个口径**，不得混用替代：
> - **① 全局综合评分（主口径）**：取 `reviews_aggregate.json.global`（或 `metadata.reviews`）的页面 global ratings——综合星级（如 4.4★ / 1,126 评价）+ 星级分布（如 5★70% / 1-2 星 6%）。**覆盖全部评论，是产品真实口碑分**。直方图与综合分一律用此口径。
> - **② 抓取样本（抱怨挖掘口径）**：取 `reviews_aggregate.json.sample`，**默认只含 URL 对应的目标 ASIN**（注明来源是用户文件还是 LinkFox 实时样本、共多少条、样本均分、抓取参数、文件内剔除了哪些同系列 ASIN）。用于挖抱怨主题与真实原话。
> - **抽样偏置必须显式写明**：样本按星级配额抓取（每星级上限约 100 条，默认尽量每档拉满），**系统性放大低星占比**，因此样本均分（如 2.5★）会远低于全局综合分（如 4.4★）——这是抽样口径差异，**不代表产品口碑差**。
> - **评分铁律**：综合评分（尤其第六维"预期管理"）**一律以全局主口径为准**；样本均分/低星比**禁止**直接当作产品评分写进报告或用于压分，样本只作"具体抱怨点"的定性佐证。
> - **写法范例**：「该 listing 全局综合 4.4★（1,126 评价，1-2 星仅 6%），口碑稳健；本次抓取的 12 条样本因星级配额偏置均分 2.5★，仅用于定位高频抱怨：水压弱、不出水（详见下方原话），不代表整体评分。」

**星级直方图**：{{review_histogram_summary}}

**好评高频词**：{{positive_keywords}}

**差评高频词**：{{critical_keywords}}

**真实买家声音**（≤ 3 条原话，含变体信息）：
- {{real_voice_1}}
- {{real_voice_2}}

**页面卖点 vs 评论反馈缝隙对照**：
- 页面说 "{{page_says_1}}" → 买家说 "{{review_says_1}}"
- 页面说 "{{page_says_2}}" → 买家说 "{{review_says_2}}"

## 七、关键维度评分（V2 · 6 维）

| 维度 | 权重 | 评分 | 评语 |
|---|---|---|---|
| 视觉一致性 | 0.20 | {{score_visual}} ★ | {{comment_visual}} |
| 信息层级 | 0.15 | {{score_info}} ★ | {{comment_info}} |
| 图文契合度 | 0.15 | {{score_textimg}} ★ | {{comment_textimg}} |
| 连贯叙事效率 | 0.10 | {{score_narrative}} ★ | {{comment_narrative}} |
| 品牌沉淀 | 0.15 | {{score_brand}} ★ | {{comment_brand}} |
| **预期管理 / 用户筛选** | 0.25 | {{score_expectation}} ★ | {{comment_expectation}} |

| 总分 | 值 |
|---|---|
| **加权总分** | **{{total_score}} / 5.0** |

## 八、行动结论（V2.2 合并 · 替代旧的「七-十」四节）

> 收尾必备四块（good / bad / borrow / avoid），渲染时为 `action-cards` 单一 section。

### 八.1 优势亮点 ✓

- {{strength_1}}
- {{strength_2}}
- {{strength_3}}

### 八.2 不足问题 ✗（含「预期管理失误」专项）

> 第 1 条必须是「**预期管理失误**」分类——直接指出页面如何引起预期错配差评。剩余条目按"模块冗余 / 品牌弱 / 类目错位 / 卖点口号化 / 尺码风险后置"等具体类别展开。

- ==预期管理失误==：{{expectation_mismatch}}
- {{weakness_2}}
- {{weakness_3}}

### 八.3 可借鉴点

> ⚠️ 每条建议必须落到**可执行级别**——抽象指令（如"复用 g02 结构"）不算合格。
> 至少 1 条必须给到**文案级**：直接给出 slogan / Best For 4 条 / "部位 + 机制 + 用户感受"三段式 / Look 命名 等可贴进设计师工单的产物。

- ✓ {{actionable_borrow_1}}
- ✓ {{actionable_borrow_2}}
- ✓ {{actionable_borrow_3}}（**至少 1 条文案级**：必须含具体改写文案 / 命名建议 / 三段式拆解）

### 八.4 规避方向

- ✗ {{avoid_1}}
- ✗ {{avoid_2}}
- ✗ {{avoid_3}}

---

> 素材产物：
> - 套图长图：`gallery_vertical.png`
> - A+ 长图：`aplus_vertical.png`
> - 元数据：`metadata.json`
> - 原始抓页：`fetched_page.html`
```

生成 HTML 的标准命令（默认输出到同目录的 `index.html`，无需手写 `--output`）：

```powershell
python ".codex/skills/amazon-competitor-analyzer/scripts/render_report_html.py" `
  --input "<阶段①输出目录>/competitor_analysis.md"
```

> ℹ️ 渲染脚本默认把 HTML 写为 `<阶段①输出目录>/index.html`（历史版本曾为 `competitor_analysis.html`，已统一改名）。若同目录存在 `review_dashboard.html`，渲染时自动注入"📊 交互式评论看板"入口；看板内的"📄 返回竞品分析报告"按钮也固定指向 `index.html`，两者互联不受改名影响。

> ⚠️ **visual.json 渲染避坑（V3.1 · 三处一致 + 字段类型）**：
>
> 1. **加权总分必须三处一致**：`.md` 的「加权总分」、`visual.json` 的 `summary` 总分卡、`score-cards` 五维分的加权和——三者必须算得出同一个数。若 `visual.json` 顶层带了 `evidence.logo_mentions`，渲染器会按五维评分卡**重算总分并覆盖** `summary`，此时若手写总分与重算值不一致,会在 stderr 打印 `[⚠️ 总分护栏覆盖]` 告警。**看到该告警就回头把 .md / visual.json 的总分同步成评分卡加权和**,别让 `validate_report_consistency.py` FAIL。
> 2. `**real_voice[].variation` 类型自由**：渲染器已兼容 `str` / `dict` / `list` 三种写法（旧版只吃 dict，传字符串会 `string indices must be integers` 崩）。推荐直接写字符串（如 `"Color: Grey · Size: L"`）。
> 3. 渲染后**务必跑** `validate_report_consistency.py` 校验 md/visual/html 总分、Logo 提及、章节顺序一致，通过才算交付。

### 4.1 可视化看板自由扩展（visual.json · 强烈推荐）

> **目的**：把"展示什么 / 怎么分组"的决策权从 Python 交回给 AI。Python 不再写死品类逻辑，AI 在每次分析时按品类、按重点自行声明可视化模块。

**约定**：在 `competitor_analysis.md` 同目录写一份 `visual.json`。`render_report_html.py` 会优先读它，按 `type` 派发渲染；未写或解析失败时回退到默认启发式。

**顶层字段**（全部可选）：


| 字段                   | 含义                                                  |
| -------------------- | --------------------------------------------------- |
| `hero`               | `{title, subtitle}` 顶部 banner 文案                    |
| `summary`            | 4-N 个顶部小卡片，每项 `{icon, label, value}`                |
| `summary_notes`      | 顶部宽卡片（如类目排名），格式同 summary                            |
| `sections`           | 按顺序排列的中部可视化模块（核心字段）                                 |
| `hide_full_markdown` | `true` 时**不**渲染底部 Markdown 全文区，整页只剩可视化卡片；默认 `false` |
| `evidence`           | 证据字段（建议）如 `logo_mentions`，用于防止计数拍脑袋                 |


**证据字段推荐**：

```json
{
  "evidence": {
    "logo_mentions": ["g01_04", "g02_01"]
  }
}
```

渲染器会优先以 `evidence.logo_mentions` 回填「Logo 出现位置」并限制品牌沉淀评分上限，避免再次出现“展示值与实际图不一致”。

### ⚠️ Sections 编排顺序硬约束（V2.2 起 · review/评分/结论顺序固定为六/七/八）

> **背景**：visual.json 的 `sections` 数组顺序就是 HTML 报告的章节顺序。AI 容易把 `kv-table`（基础信息）当作"参考资料"放尾部、把 `review-sentiment`（评论情感）当作"补充"放评分后或漏掉。**本节是硬约束**——`verdict-headline / kv-table / metric-grid / review-sentiment / score-cards / action-cards` 的相对位置由校验脚本强制锁定。

#### 推荐 Schema 顺序（按 §4 标准模板章节编号对齐 · V2.2）


| 序号  | 章节                       | 必备 type            | 是否强制出现                 |
| --- | ------------------------ | ------------------ | ---------------------- |
| 1   | 〇 · 问题本质                 | `verdict-headline` | **强制**（V2 心脏）          |
| 2   | 一 · 基础信息卡                | `kv-table`         | **强制**（事实锚点，严禁末三位）     |
| 3   | 二 · 风格五标签 · 视觉摘要         | `tag-cards`        | **强制**（视觉摘要，不可省略）       |
| 4   | 三-1 · 卖点排序 · 三层递进        | `step-ladder`      | **强制**（恰好 3 条中文短标题 + 中文副说明） |
| 5   | 三-2 · 信息层级 · A+ 分层拆解     | `info-layers`      | **强制**（A+ 模块 ≥ 3 时，恰好三层） |
| 5.1 | 三-3 · 关键词架构 · SIF 流量词       | `keyword-arch`     | **有 `keyword_arch.json` 时强制** |
| 5.2 | 三-4 · 流量入口结构 · 自然/广告/推荐   | `traffic-entry`    | **有 `traffic_source.json` 时强制** |
| 6   | 四 · 用户视角 · 卖家话术 vs 消费者关注 | `two-column-list`  | 强制                     |
| 7   | 四-X · 适合谁 / 不适合谁 · 预期管理  | `best-for-grid`    | **强制**（V2 心脏，与第 1 节配对） |
| 7.1 | 四-Y · 客户购买行为 5W2H        | `w5h2-grid`        | **强制**（V4 客户洞察）        |
| 7.2 | 四-Z · 客户画像               | `persona-cards`    | **强制**（V4 客户洞察）        |
| 7.3 | 四-K · 客户卡诺模型（Kano）真实需求   | `kano-model`       | **强制**（V4 客户洞察）        |
| 7.4 | 四-D · 产品开发注意点            | `dev-watchpoints`  | **强制**（V4 客户洞察）        |
| 8   | 五 · 品牌沉淀现状               | `metric-grid`      | 强制                     |


> ⚠️ **V4 客户洞察四块的位置硬约束**：`w5h2-grid` / `persona-cards` / `kano-model` / `dev-watchpoints` 必须整体落在 `**best-for-grid`（#7）之后、`metric-grid`（#8）之前**。它们**不得**插入收尾四联（`metric-grid → review-sentiment → score-cards → action-cards`）中间；校验脚本会强制检查四块是否齐全、位置是否在 `best-for-grid` 与 `metric-grid` 之间，并校验关键字段是否为空。
> | 9 | **六 · 评论情感解析 · 数据印证** | `review-sentiment` | **强制**（V2.2 起固定第六节，紧跟 metric-grid；仅 `metadata.reviews.available=false` 时可省） |
> | 10 | **七 · 关键评分**（V2 六维） | `score-cards` | **强制**（紧跟 review-sentiment） |
> | 11 | **八 · 行动结论**（优势 / 失误 / 借鉴 / 规避四块合一） | `action-cards` | **强制**（落地交付，最后一位） |

> 品类专属可选模块（按需穿插）：`feature-breakdown`（结构解释三段式，建议放在 #5 之后）、`look-suite`（场景图 Look 命名建议，建议放在 #8 之前）、`keyword-cloud`（卖家高频词云，建议合并进 #6）、`custom-html`（自由扩展，按内容主题就近插入）。**注意：可选模块只能穿插在 1–8 节之间，不得插入到 metric-grid → review-sentiment → score-cards → action-cards 这条收尾链条中。**

#### 必须靠前 / 严禁靠后 对照表


| 类型                 | ✅ 必须出现位置                                   | ❌ 严禁位置       | 理由                             |
| ------------------ | ------------------------------------------ | ------------ | ------------------------------ |
| `verdict-headline` | sections[0]（第一位）                           | 任何非首位        | 是「问题本质」punchline，必须开门见山        |
| `kv-table`（基础信息卡）  | sections[1]（紧跟问题本质）                        | 末三位          | 用户没看 ASIN / 品牌 / 星级，看不懂后面所有分析  |
| `metric-grid`      | 倒数第四位（紧贴 review-sentiment）                 | 末位 / 评分卡之后   | 品牌沉淀是评分输入，必须在评分前               |
| `review-sentiment` | **倒数第三位**（紧跟 metric-grid，紧贴 score-cards 前） | 评分卡之后 / 中段散位 | 评论情感是评分依据，必须**紧贴评分前出现**，固定为「六」 |
| `score-cards`      | 倒数第二位（在 action-cards 前）                    | 中部 / 首位      | 评分是"分析的总结"，必须先有事实陈述再打分，固定为「七」  |
| `action-cards`     | 最后一位                                       | 中部 / 首位      | 行动结论是落地交付，固定为「八」收尾             |
| `best-for-grid`    | 中段（用户视角附近）                                 | 首三位 / 末位     | V2 预期管理视角，必须在用户视角段之后承接         |


#### 收尾四联硬序（V2.2 强制 · 校验脚本会拦截）

```
... → metric-grid → review-sentiment → score-cards → action-cards
       (五品牌沉淀)   (六评论印证)         (七关键评分)    (八行动结论)
```

四个 type 必须**严格相邻且按上述顺序**。如果 `review-sentiment` 缺席（评论不可用），则收尾三联为 `metric-grid → score-cards → action-cards`，三者也必须严格相邻。

#### 编排自检清单（提交 visual.json 前必跑）

- [ ] `sections[0].type == "verdict-headline"`
- [ ] `sections[1].type == "kv-table"`（如品类无适用基础信息可改用其他事实锚点 type，但**不得放到末三位**）
- [ ] `sections[2].type == "tag-cards"`，标题为「二 · 风格五标签 · 视觉摘要」；必须恰好 5 张卡：`色彩应用 / 模特/受众 / 摄影风格 / 整体调性 / 拍摄方式`，每张含 `name + pills[] + desc`，色彩应用必须含 `swatches[]`
- [ ] `sections[3].type == "step-ladder"`，标题为「三-1 · 卖点排序 · 三层递进」；必须恰好 3 条，每条 `name` 为中文短标题、`desc` 为一句中文副说明。禁止直接粘贴英文 bullet，禁止超过 90 字长段落。
- [ ] A+ 模块数 ≥ 3 时，`sections[4].type == "info-layers"`，标题为「三-2 · 信息层级 · A+ 分层拆解」；必须恰好三层：`第一层 / 第二层 / 第三层`，每层中文说明。
- [ ] 若目录存在 `keyword_arch.json`，必须紧跟 `info-layers` 输出 `keyword-arch`，标题为「三-3 · 关键词架构 · SIF 流量词」，且 `metrics[]` 与 `keywords[]` 非空。
- [ ] 若目录存在 `traffic_source.json`，必须紧跟 `keyword-arch` 输出 `traffic-entry`，标题为「三-4 · 流量入口结构 · 自然 / 广告 / 推荐」，且 `composition[]` 与 `metrics[]` 非空。
- [ ] `sections[-1].type == "action-cards"`（必须以行动结论收尾，对应「八」）
- [ ] `sections[-2].type == "score-cards"`（紧贴 action-cards 之前，对应「七」）
- [ ] `sections[-3].type == "review-sentiment"`（评论可用时必须紧贴 score-cards 之前，对应「六」）
- [ ] 当 review-sentiment 缺席时，`sections[-3].type == "metric-grid"`（即收尾链条直接接到品牌沉淀）
- [ ] `verdict-headline` 与 `best-for-grid` 都出现（V2 双心脏，缺一即视为退化为 V1 报告）
- [ ] V4 客户洞察四块（`w5h2-grid` / `persona-cards` / `kano-model` / `dev-watchpoints`）都出现，且整体位于 `best-for-grid` 之后、`metric-grid` 之前（评论不可用时这四块仍出，但需注明"仅基于页面定位推断"）
- [ ] 章节标题（`title` 字段）按 V4 编号顺序写：`〇 / 一 / 二 / 三-1 / 三-2 / 四 / 四-X / 四-Y / 四-Z / 四-K / 四-D / 五 / 六 / 七 / 八`，**禁止再使用旧的「七-十」合并标号**
- [ ] ⚠️ **编号唯一性（V4.1 新增）**：每张卡片标题的裸编号必须唯一，**严禁两张相邻卡片用完全相同的裸编号**（如两张都叫「三 ·」）——同一章节拆成多张卡时，必须用子编号区分（`三-1 / 三-2`、`四-X / 四-Y` 等），否则用户会误以为是"标题重复 / 渲染出错"

> **违反任一条** → 校验脚本（`validate_report_consistency.py`）直接 FAIL，不得交付给用户。

---

**已支持的 section type**（按品类自由组合，不需要全用）：


| type                        | 用途                                                                                                                                                                                                                                         | 关键字段                                                                                                                                                              |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tag-cards`                 | **风格五标签 · 视觉摘要**（胶囊 + 色卡 + 描述），单品报告强制作为 `sections[2]` 出现；必须 5 项：色彩应用 / 模特或受众 / 摄影风格 / 整体调性 / 拍摄方式                                                                                                              | `items[{name, pills[], swatches[], desc}]`；`色彩应用` 必须带 `swatches[]`                                                                                           |
| `score-cards`               | 评分 + 进度条                                                                                                                                                                                                                                   | `items[{name, score, value, max, comment}]`                                                                                                                       |
| `action-cards`              | 行动结论（good/bad/borrow/avoid 四色）                                                                                                                                                                                                             | `items[{variant, title, bullets[]}]`                                                                                                                              |
| `kv-table`                  | 简表（基础信息 / 规格）                                                                                                                                                                                                                              | `rows[[k, v], ...]`；可选 `specs_from_metadata: true` 自动追加产品参数子区（取 `metadata.json.specs`，标签自动中译、与手写行去重、无参数则省略），可选 `specs_title` 自定义子区标题                              |
| `info-list`                 | 列表（卖点 / 关键词）                                                                                                                                                                                                                               | `items[]`，可选 `icon`                                                                                                                                               |
| `quote`                     | 高亮引用块                                                                                                                                                                                                                                      | `text`                                                                                                                                                            |
| `step-ladder`               | **三-1 · 卖点排序 · 三层递进**。用于把原始 bullets / 套图 / A+ 归纳成 3 条中文短卖点：每条 `name` 是短标题，`desc` 是一句证据/含义。禁止直接粘贴 Amazon 英文 bullet 长段。                                                                                                    | `items[{name, desc, badge?}]`；单品报告强制恰好 3 条；`name` ≤ 32 字，`desc` ≤ 90 字，必须含中文。                                                                 |
| `info-layers`               | **三-2 · 信息层级 · A+ 分层拆解**。A+ 模块 ≥ 3 时强制，紧跟 `step-ladder` 后，用三层解释“先看见什么、再证明什么、最后用什么信任/边界收口”。                                                                                                                        | `items[{layer, name, desc, color?}]`；强制恰好 3 层，layer 依次为 `第一层 / 第二层 / 第三层`，必须含中文。                                                      |
| `two-column-list`           | 两列并排列表（卖家话术 vs 消费者关注）                                                                                                                                                                                                                      | `columns[{title, variant?, bullets[]}, ...]`，variant 可选 `seller/buyer/default`                                                                                    |
| `metric-grid`               | 指标网格（品牌沉淀现状 / 关键数据）                                                                                                                                                                                                                        | `items[{label, value, hint?, status?}]`，status 可选 `ok/warn/bad/info`                                                                                              |
| `keyword-cloud`             | 关键词胶囊云（卖家高频词 / 关键词）                                                                                                                                                                                                                        | `items[]` 或 `items[{text, level}]`，level=1/2/3 控制权重视觉                                                                                                             |
| `keyword-arch`（关键词架构 · SIF） | 流量词反查：核心指标条 + 流量词表（自然/广告排名、周搜索量、流量占比、展示位/标记）。数据源 `keyword_arch.json`（阶段②.8）。有该 JSON 时强制置于「三-3」，紧跟 `info-layers` 后                                                                                                            | `metrics[{label,value,hint?,status?}]`、`keywords[{kw,kw_zh?,nat_rank?,ad_rank?,search_vol?,traffic_share_pct?,positions[]?,markers[]?}]`、`note?`                  |
| `traffic-entry`（流量入口 · SIF） | ASIN 流量来源构成：自然 vs SP/SB/SBV/推荐位 的 100% 曝光占比条 + 周期新进/退出词。数据源 `traffic_source.json`（阶段②.8）。有该 JSON 时强制置于「三-4」，紧跟 `keyword-arch` 后                                                                                                 | `composition[{label,ratio,color?}]`（ratio 0–1）、`metrics[]?`、`period{total?,in?,out?,prev?}?`、`note?`                                                              |
| `verdict-headline`（V2 新增）   | 报告开门见山「问题本质」大字 punchline 卡                                                                                                                                                                                                                 | `headline`（必填）、`tag`、`accent`（danger/warn/info）                                                                                                                   |
| `best-for-grid`（V2 新增）      | 适合谁 / 不适合谁双列网格（预期管理视角）                                                                                                                                                                                                                     | `best_for[]`、`not_for[]`，元素可为 str 或 `{label, hint}`；可选 `note`                                                                                                     |
| `feature-breakdown`（V2 新增）  | 结构解释三段式（部位 + 机制 + 用户感受）                                                                                                                                                                                                                    | `items[{part, mechanism, feel, en?}]`                                                                                                                             |
| `look-suite`（V2 新增）         | 场景图 Look 命名建议（Jeans Look / Blazer Look 等）                                                                                                                                                                                                  | `items[{name, desc?, en?, accent?}]`                                                                                                                              |
| `review-sentiment`（V2 新增）   | 评论情感解析：星级直方图 + 好/差评关键词云 + 真实买家原话 + ==页面卖点 vs review 抱怨对照表==。`histogram` 默认用 **Amazon 全局评分主口径**（来自 `metadata.reviews`）；若有用户评论文件或 LinkFox 自动抓取样本，则在 `summary` 中补充**目标 ASIN 样本口径**（来自 `reviews_aggregate.json`，默认只含目标 ASIN，并注明样本来源），二者分别标注不混用 | `histogram[{star, percent}]`、`positive_keywords[]`、`critical_keywords[]`、`real_voice[{stars, text, variation?}]`、`gap_table[{page_says, review_says}]`、`summary?` |
| `w5h2-grid`（V4 新增）          | 5W2H 购买行为分析：Who/What/When/Where/Why/How/How much 七张卡，回答竞品"卖给谁、卖什么、何时何地、为何买、怎么决策、花多少"                                                                                                                                                       | `items[{key, zh?/label, q?, finding/value, evidence?, accent?}]`；每项必须有中文标题与正文，key 用英文 Who/What/When/Where/Why/How/How much，渲染器据此自动配色                                                      |
| `persona-cards`（V4 新增）      | 客户画像：1-3 个有名有姓的典型买家卡，含标签 + 人群/场景/动机/顾虑 + 一句代表性买家原话                                                                                                                                                                                         | `items[{name, emoji?, tags[], demographic?, scenario?, motivation?, pain?, quote?}]`                                                                              |
| `kano-model`（V4 新增）         | Kano 模型真实需求：按基本型/期望型/兴奋型/无差异/反向五类分组，每条需求挂评论证据                                                                                                                                                                                              | `groups[{kano, items[]}]`，kano ∈ `must-be`/`one-dimensional`/`attractive`/`indifferent`/`reverse`；items 为 `str` 或 `{need, evidence?}`                             |
| `dev-watchpoints`（V4 新增）    | 产品开发注意点：带优先级（P0/P1/P2）与类型（must-fix/improve/innovate）的可执行清单，每条挂依据                                                                                                                                                                           | `items[{priority, point, rationale?, category?, accent?}]`                                                                                                        |
| `custom-html`               | 终极逃生口，AI 直接给 HTML                                                                                                                                                                                                                          | `html`                                                                                                                                                            |


`**hide_full_markdown` 使用建议**：

- 当 visual.json 的 sections 已经能覆盖报告所有信息时，设为 `true`，全页纯卡片化，更直观
- 当 sections 只是补充看板、报告主体仍要靠 Markdown 时，留 `false`（默认）

#### 重点强化语法（在内容字段中显式加重）

所有"内容字段"（`desc` / `comment` / `text` / `hint` / `bullets[]` / `info-list items[]` / `kv-table` 的 v 列 / `metric-grid` 的 `value`）支持两种 markup：


| 写法         | 渲染效果              | 推荐用法                   |
| ---------- | ----------------- | ---------------------- |
| `**关键词`**  | 加粗 + 深色 + 黄色下划线高亮 | 一句话里最该被一眼抓住的 1-2 个词    |
| `==必须留意==` | 黄底高亮 + 加粗         | 整段警示 / 强调"做错了什么" / 风险点 |


此外渲染器**自动加重**以下"无歧义"信号（写不写 `*`* 都会加重）：


| 自动模式    | 例子                                 | 视觉   |
| ------- | ---------------------------------- | ---- |
| 百分比     | `86%` / `14% Spandex`              | 蓝色加粗 |
| 排名编号    | `#530` / `#243,735`                | 红色加粗 |
| ★ 评分    | `3.0 ★` / `★★★★`                   | 金色胶囊 |
| 评级词 · 差 | `未建立` / `失分` / `失守` / `不通过` / `缺位` | 红色加粗 |
| 评级词 · 中 | `中等偏下` / `中等偏上` / `存在阶层差` / `存在错位` | 黄色加粗 |
| 评级词 · 好 | `已建立` / `完整` / `对齐` / `图文一一对应`     | 绿色加粗 |


**用法准则**：

- 不要全段 `*`* —— 加重失效。一段话 `**` 不超过 2 处
- 不要 `**` 强调短词标签（pills / kw-cloud / label / name）—— 渲染器对这些字段已经做了视觉强化，再 `**` 会过载
- `==` 留给"真正想让用户多看一眼"的句子，每节最多 1 个

示例：

```json
{ "name": "品牌沉淀", "score": "3.0 ★", "value": 3.0, "max": 5,
  "comment": "Logo 仅 **3 次出现**，准买家秀模块 **0 Nebility 视觉符号**——KOL 街拍换上任何品牌名都成立。==视觉锤未建立==。" }
```

渲染结果：`3.0 ★`（金色）、`3 次出现` / `0 Nebility 视觉符号`（加粗深色 + 下划线）、`视觉锤未建立`（黄底）。

**示例**（严格遵循上方「Sections 编排顺序硬约束」的最小骨架，强烈建议直接 fork 本结构填内容）：

```json
{
  "hero": { "title": "📊 Amazon 竞品分析看板", "subtitle": "Nebility · Bodysuit · DTC" },
  "summary": [
    { "icon": "🏷", "label": "品牌", "value": "Nebility" },
    { "icon": "⭐", "label": "星级 / 评价", "value": "4.4 / 142" },
    { "icon": "📉", "label": "加权总分", "value": "3.5 / 5.0" }
  ],
  "evidence": { "logo_mentions": ["g01_04", "g02_01"] },
  "hide_full_markdown": true,
  "sections": [
    {
      "type": "verdict-headline",
      "title": "〇 · 问题本质",
      "accent": "danger",
      "headline": "页面把 X 打得很漂亮，==却用 Y 把预期拉得过高==——3.7★ + 14% 一星即结构性预期错配信号。"
    },
    {
      "type": "kv-table",
      "title": "📋 一 · 基础信息卡",
      "specs_from_metadata": true,
      "specs_title": "产品参数（自 Amazon 参数表自动提取）",
      "rows": [
        ["ASIN", "B0XXXXXXX"],
        ["品牌", "Nebility"],
        ["星级 / 评价", "4.4 ★ / 142 评价"],
        ["类目排名", "#27 in Women's Shapewear Bodysuits"],
        ["主报价", "$32.99"],
        ["变体", "3 色 / 6 码"],
        ["套图数 / A+ 模块数", "7 / 5"]
      ]
    },
    { "type": "tag-cards",      "title": "🎨 二 · 风格五标签 · 视觉摘要",            "items": ["..."] },
    {
      "type": "step-ladder",
      "title": "📌 三-1 · 卖点排序 · 三层递进",
      "items": [
        { "badge": "1", "name": "超强真空吸力 + 手拧锁定", "desc": "96/98 LBS 与「越颠越牢」主打物理吸附上限" },
        { "badge": "2", "name": "N52/N55 强磁 MagSafe 兼容", "desc": "信号/充电友好，18N 磁力固定" },
        { "badge": "3", "name": "360° 三轴稳定 + 多表面适配", "desc": "含胶垫，广泛机型兼容" }
      ]
    },
    {
      "type": "info-layers",
      "title": "🪜 三-2 · 信息层级 · A+ 分层拆解",
      "items": [
        { "layer": "第一层", "name": "主体写真 / 视觉风格", "desc": "首图用车内使用场景 + 产品微距建立专业硬件感" },
        { "layer": "第二层", "name": "功能与定位展示", "desc": "安装位置图 + 180°/360° 旋转 + LBS 锁扣 + 磁铁参数证明核心卖点" },
        { "layer": "第三层", "name": "信任状 / 兼容警告", "desc": "磁环使用要求、手机壳限制和兼容性说明用于降低误用预期" }
      ]
    },
    { "type": "two-column-list","title": "👥 四 · 用户视角 · 卖家话术 vs 消费者关注", "columns": ["..."] },
    { "type": "best-for-grid",  "title": "🎯 四-X · 适合谁 / 不适合谁 · 预期管理",   "best_for": ["..."], "not_for": ["..."] },
    {
      "type": "w5h2-grid",
      "title": "🛒 四-Y · 客户购买行为（5W2H）",
      "items": [
        { "key": "Who",      "zh": "谁在买",   "q": "目标买家是谁？",     "finding": "**产后 & 婚礼修身**为主的 28-42 岁女性", "evidence": "评论高频 'postpartum' / 'for my wedding'" },
        { "key": "What",     "zh": "买什么",   "q": "买产品还是解决方案？", "finding": "买的是「**穿出去显瘦**的确定性」，不是面料" },
        { "key": "When",     "zh": "何时买",   "q": "购买时机？",         "finding": "产后修复期 + 婚礼/聚会前的**节点性需求**" },
        { "key": "Where",    "zh": "在哪用",   "q": "使用场景？",         "finding": "正式场合 + 日常通勤双场景" },
        { "key": "Why",      "zh": "为何买",   "q": "核心动机/痛点？",     "finding": "想要**强塑形但不勒不卷边**", "evidence": "差评集中在 'rolls down'" },
        { "key": "How",      "zh": "怎么决策", "q": "决策路径/顾虑？",     "finding": "反复纠结尺码、担心退货" },
        { "key": "How much", "zh": "花多少",   "q": "价格敏感度？",       "finding": "$30-40 区间觉得**值**，超 $50 嫌贵" }
      ]
    },
    {
      "type": "persona-cards",
      "title": "👤 四-Z · 客户画像",
      "items": [
        {
          "name": "产后修复妈妈 · Maria", "emoji": "🤱",
          "tags": ["30-40岁", "新手妈妈", "中等价格敏感"],
          "demographic": "产后 3-12 个月、急于恢复身形的职场妈妈",
          "scenario": "回归职场 + 接送孩子的日常穿着",
          "motivation": "快速显瘦 + 托腹支撑、重建自信",
          "pain": "怕勒、怕卷边、怕一天下来不舒服",
          "quote": "Wore it postpartum, finally felt confident again — but it rolls down after a few hours."
        }
      ]
    },
    {
      "type": "kano-model",
      "title": "🎯 四-K · 客户卡诺模型（Kano）真实需求",
      "groups": [
        { "kano": "must-be", "items": [
          { "need": "尺码准、不卷边、穿一天不松垮", "evidence": "差评高频 'rolls down' / 'sizing off'" }
        ]},
        { "kano": "one-dimensional", "items": [
          { "need": "塑形力度越强越满意（但需配合舒适）", "evidence": "好评 'firm control' / 差评 'too weak'" }
        ]},
        { "kano": "attractive", "items": [
          { "need": "隐形无痕、外衣穿着看不出", "evidence": "好评惊喜 'invisible under dress'" }
        ]}
      ]
    },
    {
      "type": "dev-watchpoints",
      "title": "🛠 四-D · 产品开发注意点",
      "items": [
        { "priority": "P0", "category": "must-fix", "point": "腰口防卷边硅胶 + 准确尺码表",     "rationale": "卷边/尺码是差评第一来源（Kano 基本型失守）" },
        { "priority": "P1", "category": "improve",  "point": "在保证舒适前提下提升塑形分级",       "rationale": "塑形力度是期望型，越好越拉分" },
        { "priority": "P2", "category": "innovate", "point": "强化「外衣无痕」卖点并在主图证明",     "rationale": "兴奋型爆点，竞品评论惊喜词" }
      ]
    },
    { "type": "metric-grid",    "title": "🏷 五 · 品牌沉淀现状",                    "items": ["..."] },
    {
      "type": "review-sentiment",
      "title": "💬 六 · 评论情感解析 · 数据印证",
      "histogram": [
        { "star": 5, "percent": 62.0 }, { "star": 4, "percent": 18.0 },
        { "star": 3, "percent": 10.0 }, { "star": 2, "percent": 4.0 },
        { "star": 1, "percent": 6.0 }
      ],
      "gap_table": [
        { "page_says": "Firm Tummy Control", "review_says": "**力度不达预期**——中度面料 vs 高承诺语" }
      ],
      "summary": "5★ 62% / 1★ 6% — 头部产品但仍有结构性预期错配空间"
    },
    { "type": "score-cards",    "title": "⭐ 七 · 关键评分（V2 六维 · 加权总分 3.5 / 5.0）", "items": ["..."] },
    {
      "type": "action-cards",
      "title": "✅ 八 · 行动结论 · 优势 / 失误 / 借鉴 / 规避",
      "items": [
        { "variant": "good",   "title": "✓ 优势亮点",   "bullets": ["..."] },
        { "variant": "bad",    "title": "✗ 不足问题",   "bullets": ["..."] },
        { "variant": "borrow", "title": "✓ 可借鉴点",   "bullets": ["..."] },
        { "variant": "avoid",  "title": "✗ 规避方向",   "bullets": ["..."] }
      ]
    }
  ]
}
```

> 上述骨架就是「最小合规」visual.json，对应章节编号 〇 / 一 / 二 / 三 / 四 / 四-X / **四-Y / 四-Z / 四-K / 四-D（V4 客户洞察）** / 五 / 六 / 七 / 八。**收尾四联硬序**（`metric-grid → review-sentiment → score-cards → action-cards`）由校验脚本强制锁定，禁止打乱。V4 客户洞察四块（`w5h2-grid` / `persona-cards` / `kano-model` / `dev-watchpoints`）统一放在 `best-for-grid` 之后、`metric-grid` 之前，作为中段自由模块不进入收尾四联。`review-sentiment` 不再"位置自由"，必须紧贴 `score-cards` 之前出现；只有当 `metadata.reviews.available=false` 时才可省略，此时收尾三联为 `metric-grid → score-cards → action-cards`。新对话直接 fork 本骨架填内容，几乎不可能再排错。

**何时该用 visual.json**：

- 非服饰品类（3C、美妆、家居、食品等），需要不同维度时
- 标准 10 节模板用不上某些章节（例如视频类产品无 A+ 但有口播脚本）
- 想新增"竞争对手对比矩阵"、"价格阶梯图"等专属可视化时
- 即便走标准模板，也建议产出一份对齐的 visual.json，避免 Python 启发式误读

**新 type 拓展**：如需新增 section type，在 `render_report_html.py` 的 `SECTION_RENDERERS` 中添加一个小渲染函数即可，AI 后续可直接使用，不需要再改主流程。

## 5. 多 URL 对比模式

> ⚠️ **本节是硬约束**——上一轮如果只在对话里给口头评分总结，等于违反本节全部要求。
> ⚠️ V2.3 起，本 Skill 的多 URL 模式**只产 N 份单品三件套 + 一次强制询问钩子**，不再自产"对比矩阵三件套"。横向综合可视化沉淀由独立 Skill `amazon-multi-asin-visual-synthesizer` 完成。

### 5.1 必产物清单（缺一即视为未完成交付）

N 个 URL 输入 → 必须在 `生成结果输出/amazon图片提取/_compare_<时间戳>/` 父目录下产出：

```
_compare_<时间戳>/
├─ <ASIN_1>/                              ← SKU #1 完整三件套目录
│  ├─ gallery_vertical.png + aplus_vertical.png + gallery/ + aplus/
│  ├─ fetched_page.html + metadata.json
│  ├─ competitor_analysis.md              ← 必出
│  ├─ visual.json                         ← 必出
│  └─ index.html            ← 必出（且通过 validate_report_consistency.py）
├─ <ASIN_2>/                              ← SKU #2 完整三件套
│  └─ ...（同上 3 件套）
└─ <ASIN_N>/                              ← SKU #N 完整三件套
   └─ ...

（若用户在 §5.4 询问中选 B "对比总结"，则由 amazon-multi-asin-visual-synthesizer 在
 _compare_<时间戳>/ 根目录追加 viz_data.json + index.html，与各 ASIN 子目录平级）
```

### 5.2 单 SKU 三件套（每个 SKU 都要走）

每个 ASIN 子目录内的 `competitor_analysis.md / visual.json / index.html` 严格遵循 §4 / §4.1 全部硬约束（含「八」节 action-cards 收尾、收尾四联硬序、Sections 编排顺序等）。**不允许因为是"多 URL 模式"就跳过 verdict-headline / best-for-grid / review-sentiment 等任一必备 Section**。

### 5.3 ⛔ 已下线：对比矩阵三件套

V2.2 之前的版本要求本 Skill 直接产出 `comparison_matrix.md / .visual.json / .html`，并复用单品渲染脚本 `render_report_html.py`。**用户实测反馈该路径有严重缺陷**：

- 复用单品脚本 → 对比页左侧出现套图缩略图栏 + A+ 模块切换器（"长得像单品页"，与对比定位不符）
- "对比矩阵"在内容深度上停留在"评分罗列 + 几条共性 / 差异 bullet"，没有"行业共性 + 红色结论卡 / 竞品逻辑 → 本品建议逻辑"这种汇报型对比框架

**V2.3 起的处置**：本 Skill 完全不产对比矩阵任何文件。如果用户需要横向综合可视化沉淀，由本 Skill 在 §5.4 的询问钩子中将控制权移交给 `**amazon-multi-asin-visual-synthesizer`**——它自带 ECharts 渲染器，输出自包含 HTML 综合看板，含 4 图：

1. 评论痛点强度热力矩阵（整行偏红 = 全行业共同盲区）
2. 市场定位气泡图（星级 × 评价数体量）
3. 竞品 × 卖点 关系网络图（红海共性 vs 蓝海盲区）
4. Kano 行业级需求聚合（基本型 / 期望型 / 兴奋型）

详见 `.codex/skills/amazon-multi-asin-visual-synthesizer/SKILL.md`。

### 5.4 执行顺序与交接询问钩子（强制）

```
Step 1：对所有 N 个 URL 并发跑阶段 ①素材采集
Step 2：对所有 N 个素材包并发跑阶段 ②元数据抽取
Step 3：FOR each ASIN: 跑阶段 ③④⑤ 产出单品三件套 + 跑 validate_report_consistency.py
        全部通过校验后才能进入 Step 4
Step 4：⚠️ 强制 request_user_input 交接询问（三选一）
        ┌─────────────────────────────────────────────────┐
        │ N 份单品三件套已完成。接下来您想做什么？        │
        │                                                 │
        │ A. 补充内容（针对某个 SKU 的某节做修订/扩写）   │
        │ B. 综合可视化（→ 调用 visual-synthesizer 出看板）│
        │ C. 都不需要（结束本轮）                         │
        └─────────────────────────────────────────────────┘
Step 5：根据用户选择执行：
  A → 在本 Skill 内对指定 SKU 做迭代（接受用户补充意见，重写对应 md + visual.json + 重渲染 html）
  B → 调用 amazon-multi-asin-visual-synthesizer
       输入：_compare_<时间戳>/<ASIN_i>/（i=1..N，详细层三件套）
            + 若本轮存在「简析层」ASIN（只做了评论驱动简版分析、含 brief_analysis.md + metadata + 评论聚合/证据，
              但无 visual.json/六维评分），一并把其目录作为 tier:"rough" 移交——它们会进图⑤价格–口碑性价比矩阵
              与顶部竞品卡片（带"简析"徽标），不进图1-4，保持详细层口径严谨
       追加产出：_compare_<时间戳>/{viz_data.json, index.html}（compare 根目录，与各 ASIN 子目录平级）
  C → 给最终对话回复（≤ 200 字简要总结 + 列出所有单品三件套产物路径）
```

**Step 4 询问的标准实现**：必须使用 `request_user_input` 工具的 Q&A 选项卡（不得只用文字段落追问）。题目示例 JSON：

```jsonc
{
  "title": "竞品分析后续动作",
  "questions": [
    {
      "id": "next_action",
      "prompt": "N 份单品三件套已完成。接下来您想做什么？",
      "options": [
        { "id": "supplement", "label": "A. 补充内容（针对某个 SKU 的某节做修订）" },
        { "id": "synthesize", "label": "B. 综合可视化（生成横向综合可视化看板）" },
        { "id": "done",       "label": "C. 都不需要，结束本轮" }
      ]
    }
  ]
}
```

> ⚠️ **顺序不可乱**：必须先所有单品三件套都落地、都通过 `validate_report_consistency.py`，才能进入 Step 4 询问。理由：综合可视化沉淀的所有评分/数据必须与单品报告**逐字一致**（visual-synthesizer 会从 `<ASIN>/visual.json` + 评论聚合抽取，单品没落地就没有数据源）。

## 6. ❌ 禁止行为

### 6.1 单 SKU 通用禁令

- 跳过阶段 ① 素材采集就开始打分（= 凭印象打分，必然失真）
- 用文字复述 A+ 图内的产品/版式细节（→ 违反 `ref-image-must-include` 的"参考图过度描述陷阱"）
- 评分用语含糊（如"还行"、"一般"）；必须落到刚性评分锚点
- 对消费者实际反馈做无依据的揣测（用户视角段必须从 bullets 文字 + 视觉信号推断，不得编造评论原文）
- ❌ **用户只提供亚马逊链接时跳过评论抓取**——阶段 ② 后必须调用 `linkfox-amazon-reviews` 获取目标 ASIN 评论样本；只有接口失败 / 未授权 / 0 条返回 / 用户明确跳过评论时才可降级，并必须注明原因
- ❌ **只看 LinkFox 预览摘要不读取完整落盘 JSON**——`response_io.py run` 的 preview 不是全量评论，必须把落盘文件路径作为后续 `<评论数据路径>` 传给聚合、看板和证据脚本
- 漏掉品牌沉淀维度（这是最容易被忽视、但最影响"是否被记住"的指标）
- ❌ **默认把同系列其它 ASIN 的评论也混进来分析**——URL 里的 ASIN 才是目标竞品，默认只分析该目标 ASIN 的评论（从 `metadata.json.asin` 自动解析）；仅当用户明确"分析整个系列"时才加 `--all-variants`（详见 §3 阶段 ②.5）
- ❌ **把评论样本的低星比直接当作 Amazon 全局评分分布**——二者口径不同，必须分别标注（详见 §4 模板「六」双口径标注）
- ❌ **把抓取样本的均分/低星比当作产品综合评分写进报告或用于压分**（V3.1 红线）——样本按星级配额抓取（每星级上限约 100 条）会系统性放大低星，样本均分（如 2.5★）≠ 产品口碑。综合评分一律取 `reviews_aggregate.json.global`（如 4.4★），样本仅用于定位具体抱怨点
- ❌ **生成 `review_dashboard.html` 时不传 `--aspects` / `--keywords`**——会导致「智能问题归类」整块隐藏、词云回退英文碎片词；`validate_report_consistency.py` 硬拦截 FAIL。Agent 必须先读评论产出 `aspects.json` + 中文 `keywords.json`，再调用看板脚本
- ❌ **`visual.json` 的 `review-sentiment.positive_keywords / critical_keywords` 写英文**——必须与 `keywords.json` 的 `term` 同步为中文标签（可带 count），否则校验 FAIL
- ❌ **跳过 `extract_review_evidence.py` 就写优缺点**——报告优缺点必须基于全样本证据，禁止抽样拍脑袋
- ❌ **凭空虚构客户画像 / 5W2H / Kano 需求**（V4 红线）——客户洞察四块（四-Y/Z/K/D）必须从 bullets + 页面定位 + `review_evidence.json` 全样本证据推断，每条尽量挂证据；评论样本不可用时降级为"仅基于页面定位推断"并注明，**不得编造买家原话或臆造画像**
- ❌ **跳过客户洞察四块**（V4）——`w5h2-grid` / `persona-cards` / `kano-model` / `dev-watchpoints` 是 V4 强制章节，缺一即视为退化报告（评论不可用时仍出，标注推断口径即可）
- ❌ **5W2H 空心卡**——不得只写 `key` 或只让 HTML 显示 who/what/when；每项必须有中文标题和正文，且渲染后能看到 `w5h2-value` 正文。

### 6.2 多 URL 专项禁令（N ≥ 2 时严查）

- ❌ **只跑阶段 ①+② 就交付**：抓完素材和元数据后，直接在对话里口头给出评分总结，不落地任何 `competitor_analysis.md / visual.json / .html` 文件
- ❌ **只产部分单品三件套**：前 1-2 个 SKU 走完整三件套，剩余 SKU 在对话里口述（参差不齐）
- ❌ **降级为单文件合并报告**：把 N 个 SKU 的内容压缩进一份 md，跳过每家独立的 visual.json + HTML
- ❌ **以 token / 时间预算为由擅自降级**：必须先 `request_user_input` 与用户协商批次方案，**而不是直接给口头总结**
- ❌ **跳过 §5.4 强制询问钩子**：N 份单品三件套出完，不能直接给最终结语就跑路；必须 `request_user_input` 问 A/B/C 三选一（即使预期用户会选 C 也必须问）
- ❌ **自己产出 `comparison_matrix.md / .html` / 任何"对比矩阵"文件**：V2.3 起横向综合可视化沉淀完全交给 `amazon-multi-asin-visual-synthesizer`，本 Skill 不再生产此类产物
- ❌ **用单品渲染脚本 `render_report_html.py` 渲染任何对比报告**：单品脚本带左侧套图栏，渲染出来的对比页"长得像单品页"——这是用户在 V2.2 反馈过的体验缺陷

### 6.3 兜底检查（每次多 URL 任务交付前自检）

提交回复前，AI 必须自检：

- [ ] N 个 URL 是否各自有独立的 `<ASIN>/` 子目录？
- [ ] 每个子目录是否都有 `competitor_analysis.md + visual.json + index.html`？
- [ ] 每个 SKU 都跑过 `validate_report_consistency.py` 并通过？
- [ ] 是否在 N 个单品三件套都通过校验后，按 §5.4 强制使用 `request_user_input` 询问用户后续动作（A 补充 / B 对比总结 / C 结束）？
- [ ] 目录里**不应**出现任何 `comparison_matrix.*` 文件（V2.3 起已下线，由独立 Skill 接管）

任一条不满足 → **不得回复**"分析完成"，必须先把缺的文件补齐 / 把询问钩子补上。

## 7. ✅ 正确行为

- 每个评分维度后给出 1 句**带依据**的评语，不只给星
- "可借鉴点 / 规避方向" 必须给可行动的指令（如"主图 + 副图细节并排呈现" → 可借鉴；"功能信息埋在尾部" → 规避）
- 对照本品（如有）输出"我们如何做得更好"的具体方向
- 报告末尾附素材路径，方便用户回查
- **多 URL 对比时强制产出 N 份单品三件套**——所有 SKU 都必须走完整 Step 1-3 的三件套流程
- **多 URL 流程末尾强制 `request_user_input`** 让用户在 "A 补充内容 / B 对比总结 / C 结束" 三选一
- 用户选 B 时，控制权交给 `amazon-multi-asin-visual-synthesizer`，本 Skill 不再继续产出
- 多 URL 任务的最终对话回复 = **≤ 200 字简要总结 + 列出所有单品三件套产物路径 + 显式问出后续动作**，详细内容让用户去看 HTML 报告（避免对话里堆砌长评分表）
- 只提供 URL 且未提供评论文件时，阶段 ② 后自动抓取评论样本，并把样本来源、样本条数、抓取参数写入第六节双口径说明；抓取失败时明确记录失败原因，不编造评论结论

## 8. 相关脚本与产物路径

> V2.4 起所有脚本由 `工具/amazon_competitor_analyzer/` 与 `工具/amazon_image_extractor/` 迁移到对应 Skill 的 `scripts/` 子目录，遵循 Skill 自包含原则（详见 `.codex/rules/skill-file-structure.mdc`）。

- `.codex/skills/amazon-image-extractor/scripts/extract_and_stitch.py`（素材采集，被本 Skill 调用 · 归属 `amazon-image-extractor` Skill）
- `.codex/skills/amazon-competitor-analyzer/scripts/extract_metadata.py`（元数据抽取，本 Skill 专属配套）
- `.codex/skills/linkfox-amazon-reviews/scripts/amazon_us_reviews.py` / `amazon_reviews.py`（评论自动抓取来源 · 阶段 ②.4 · 用户只提供 URL 且无评论文件时调用；美国站走 US 脚本，非美国站走 domainCode 脚本）
- `.codex/skills/linkfox-amazon-reviews/scripts/response_io.py`（大响应落盘工具 · 阶段 ②.4 推荐调用方式；落盘后的 `reviews_linkfox_raw*.json` 作为后续评论数据路径）
- `.codex/skills/amazon-competitor-analyzer/scripts/review_core.py`（评论分析共享核心 · 被 `aggregate_reviews_json.py` 与 `build_review_dashboard.py` import：归一化 .json/.xlsx 以及 LinkFox `data[]` 原始 JSON、数据驱动关键词抽取、各维度聚合）
- `.codex/skills/amazon-competitor-analyzer/scripts/aggregate_reviews_json.py`（评论聚合 · 阶段 ②.5 · 数据驱动 · 支持 .json/.xlsx/LinkFox raw JSON · **默认只分析目标 ASIN（从 metadata.json 解析），可加 --all-variants 看全系列**）
- `.codex/skills/amazon-competitor-analyzer/scripts/build_review_dashboard.py`（交互式评论看板生成 · 阶段 ②.6 · 用户评论文件或 LinkFox 评论样本均可产出第 4 件套 `review_dashboard.html` + 外链 `reviews_data.js` · 内联 `assets/echarts.min.js` 离线自包含 · 支持 `--aspects` / `--keywords`）
- `.codex/skills/amazon-competitor-analyzer/scripts/extract_review_evidence.py`（按优缺点逐条提取全样本评论证据 · 复用 `review_core` · 产出 `review_evidence.json` · 报告的优缺点综合**必须**基于它，禁止抽样拍脑袋）
- `.codex/skills/amazon-competitor-analyzer/scripts/fetch_keyword_traffic.py`（阶段②.8 · 调 `linkfox-sif-asin-keywords` + `linkfox-sif-asin-summary` 归一化产出 `keyword_arch.json` + `traffic_source.json`（+多URL `kw_traffic_index.json`）· 喂报告「三-3 关键词架构 / 三-4 流量入口」· 需 `LINKFOXAGENT_API_KEY`）
- `.codex/skills/amazon-competitor-analyzer/assets/echarts.min.js`（本地 ECharts 库 · 被 `build_review_dashboard.py` 内联进看板 HTML）
- `.codex/skills/amazon-competitor-analyzer/scripts/render_report_html.py`（**单品**报告渲染脚本 · 含左侧套图栏；**不得**用于横向综合可视化沉淀）
- `.codex/skills/amazon-competitor-analyzer/scripts/validate_report_consistency.py`（一致性校验）
- 默认输出根：`生成结果输出/amazon图片提取/<ASIN>_<时间戳>/`（单 URL）/ `生成结果输出/amazon图片提取/_compare_<时间戳>/`（多 URL）

## 9. 下游协作 Skill

- `**amazon-multi-asin-visual-synthesizer`**：多 URL 模式下用户选 B 时由本 Skill 移交控制权，专做"多 ASIN 综合可视化沉淀"——跨家归并后渲染自包含 HTML 综合看板（痛点热力矩阵 / 市场定位气泡图 / 竞品×卖点关系网络图 / Kano 行业需求聚合 四图 + 竞品主图卡片 + 跳转各 ASIN 报告/看板链接）；该 Skill 自带 ECharts 渲染器与库，**自包含**、不复用本 Skill 的渲染脚本
