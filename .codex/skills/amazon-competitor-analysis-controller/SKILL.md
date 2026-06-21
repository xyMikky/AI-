---
name: amazon-competitor-analysis-controller
description: Amazon 竞品分析主控路由 Skill。凡用户要求分析 Amazon ASIN/商品 URL/竞品、多个 ASIN 横向对比、指定部分 ASIN 详细分析而其他 ASIN 简析、生成竞品报告/综合分析/对比看板/评论痛点/Listing 机会，都必须优先触发本 Skill。默认交付口径是完整竞品分析：单 ASIN 走 amazon-competitor-analyzer，必须产出 competitor_analysis.md + visual.json + index.html，并在有评论样本时产出 review_dashboard.html；多 ASIN 先补齐各 ASIN 单品三件套，再由 amazon-multi-asin-visual-synthesizer 生成 viz_data.json + 综合 index.html。只有用户明确说“快速/简单/只要文字/不要 HTML/不要看板”时才走 amazon-competitor-quick-analyzer。它负责识别单品、批量、多 ASIN 详细/简析、输入缺失时主动补齐数据、仅在用户明确限制本地文件或上游获取失败时降级等场景，并定义合格输出标准。关键词：竞品分析、Amazon竞品、ASIN分析、多个ASIN、详细分析、完整分析、HTML报告、可视化看板、竞品报告、评论痛点、Listing机会、快速分析、简要分析。
---

# Amazon 竞品分析主控

本 Skill 是路由器和验收门，不直接替代下游业务 Skill。只要任务涉及 Amazon 竞品分析，先用本 Skill 判断流程，再加载必要下游 Skill。

## 0. 默认交付口径

除非用户明确使用“快速、简单、粗看、只要文字、不要 HTML、不要看板、不要落地文件”等轻量限制词，否则所有 Amazon 竞品分析默认都是**完整分析**：

- **单 ASIN / 单 URL**：使用 `amazon-competitor-analyzer`，必须落地 `competitor_analysis.md`、`visual.json`、`index.html`；只要评论样本获取成功，还必须落地 `reviews_aggregate.json`、`review_evidence.json`、`review_dashboard.html`。
- **多 ASIN / 多 URL**：先为每个 detail ASIN 补齐单品三件套，再调用 `amazon-multi-asin-visual-synthesizer` 输出 `_compare_<时间戳>/viz_data.json` 与 `_compare_<时间戳>/index.html`。用户没有明确分层时，默认全部按 detail 层处理。
- **“竞品分析一下这个”“看下这个品”“分析这个链接”** 这类普通表达，一律视为完整分析请求，不得自动降级为快速文字结论。
- 快速文字结论只能在用户明确要求轻量输出时使用，且最终回复第一句要标注“这是快速文字分析，不是完整 HTML 报告”。

## 1. 强制触发场景

出现以下任一信号，必须优先进入本 Skill：

- 用户给出一个或多个 Amazon ASIN / 商品 URL，并要求“分析竞品、竞品分析、看下这个品、拆解 Listing、评论痛点、改款机会”。
- 用户给出多个 ASIN，并指定“某些详细分析，其他简要/简析/简单分析”。
- 用户要求“横向对比、综合分析、对比总结、综合可视化、可视化沉淀、看板、热力矩阵、Kano、市场定位”。
- 用户上传或引用 `_compare_<时间戳>` 目录、`visual.json`、`metadata.json`、`reviews_aggregate.json`、`review_evidence.json`、`*_reviews_US.json`。

## 2. 路由优先级

按以下优先级判断，前者覆盖后者：

1. **多 ASIN + 详细/简析分层 / 横向综合 / 看板**  
   使用 `amazon-multi-asin-visual-synthesizer`。生成 `_compare_<时间戳>/viz_data.json` 和 `_compare_<时间戳>/index.html` 才算完成。先用 `amazon-multi-asin-data-auditor` 校验已有 `_compare` 数据是否串号。

2. **多 ASIN，但还没有单品三件套**  
   默认不是降级，而是主动补齐。用 ASIN 生成 Amazon URL 后调度 `amazon-competitor-analyzer` 跑 detail ASIN 的完整单品三件套；rough ASIN 至少补齐 `metadata.json / reviews_aggregate.json / review_evidence.json / brief_analysis.md / review_dashboard.html`。只有用户明确说“只用本地评论文件/不要联网/不要抓页面”，或上游抓取、接口、权限连续失败时，才允许进入“评论驱动降级分析”。

3. **单 ASIN / 单 URL 默认完整分析**  
   使用 `amazon-competitor-analyzer`。必须完成素材采集、页面元数据、评论样本/聚合/证据、单品 `competitor_analysis.md + visual.json + index.html`，并在评论样本可用时生成 `review_dashboard.html`。只有全部必需产物存在并通过可用校验后，才能回复“完整竞品分析完成”。

4. **单 ASIN 快速文字结论（显式轻量请求才触发）**  
   仅当用户明确说“快速分析、简单分析、粗看、只要文字、不要 HTML、不要看板、先给结论”等轻量限制词时，使用 `amazon-competitor-quick-analyzer`。必须获取页面元数据、套图/A+ 抓取信息、评论样本/聚合摘要后再给文字结论，并说明这不是完整 HTML 报告。

5. **仅要求抓图 / 套图 / A+**  
   使用 `amazon-image-extractor`。

6. **仅要求评论读取、评论筛选、差评/好评分析**  
   使用 `linkfox-amazon-reviews`。它是评论数据源，不是多 ASIN 综合竞品分析的最终输出 Skill。

7. **要求流量、关键词、ABA、标题词频**  
   分别使用 `linkfox-sif-asin-summary`、`linkfox-sif-asin-keywords`、`linkfox-sif-keyword-traffic`、`linkfox-aba-data-explorer`、`linkfox-product-title-analyze`，并将结果并入竞品分析主线。

## 3. 单 ASIN 标准流程

当用户给 1 个 ASIN / Amazon 商品 URL 并要求“竞品分析、看下这个品、分析这个链接、拆解 Listing、评论痛点、改款机会”时，默认执行完整流程：

1. 解析 ASIN，生成或保留标准商品 URL：`https://www.amazon.com/dp/<ASIN>`。
2. 调用 `amazon-competitor-analyzer` 的单 URL 流水线，补齐素材、`metadata.json`、评论样本、评论聚合、评论证据与单品三件套。
3. 必须检查输出目录至少包含：`competitor_analysis.md`、`visual.json`、`index.html`、`metadata.json`、`report.json`。
4. 若评论样本抓取成功，还必须包含：`reviews_aggregate.json`、`review_evidence.json`、`review_dashboard.html`。
5. 若配置了 `LINKFOXAGENT_API_KEY`，必须尝试补齐 `keyword_arch.json` / `traffic_source.json`；成功时必须纳入 `visual.json` 的关键词架构和流量入口结构。
6. HTML 验收必须确认：`index.html` 存在、不是空白页、没有 `class="gallery-main" src=""`，并能引用套图或 A+ 图片；缺失时回到素材采集或报告渲染阶段修复。
7. 最终回复只给核心文件路径和一句导读，不用在对话里复写完整报告。

## 4. 多 ASIN 标准流程

当用户给多个 ASIN 并出现“详细/简析”或“综合分析”时，执行：

1. 解析 ASIN 清单，明确 `detail` 与 `rough` 层级。
2. 查找或创建 `_compare_<时间戳>/` 根目录。
3. 若缺少本地三件套，先根据 ASIN 生成 `https://www.amazon.com/dp/<ASIN>`，主动运行上游采集/分析链路，而不是降级。
4. 对 detail ASIN 检查/补齐：`report.json`、`visual.json`、`metadata.json`、`reviews_aggregate.json`、`review_evidence.json`、`review_dashboard.html`、`index.html`、`gallery/`、`aplus/`。`visual.json.sections` 必须包含 `三-1 · 卖点排序 · 三层递进`（`step-ladder`，恰好 3 条中文短标题 + 中文副说明）和 `三-2 · 信息层级 · A+ 分层拆解`（`info-layers`，A+ ≥ 3 时强制，恰好 第一层/第二层/第三层）。若环境配置 `LINKFOXAGENT_API_KEY`，必须尝试补齐 `keyword_arch.json` / `traffic_source.json`；只要这两个 JSON 存在，单品 `visual.json` 必须出现 `三-3 · 关键词架构`（`keyword-arch`）和 `三-4 · 流量入口结构`（`traffic-entry`），并在综合图 6/7 中纳入。
5. 对 rough ASIN 检查/补齐：`report.json`、`metadata.json`、`reviews_aggregate.json`、`review_evidence.json`、`brief_analysis.md`、`review_dashboard.html`；若已抓图，也必须补齐 `metadata.media`。
6. 执行图片链路验收：若 `gallery/` 或 `aplus/` 有图片，则 `report.json.gallery.files` / `report.json.aplus.groups[].files` 必须引用这些相对路径，`metadata.media.gallery_count / aplus_module_count` 不能为空，单品 `index.html` 不得出现 `class="gallery-main" src=""`，并且必须包含 `gallery/01_` 或 A+ 图片引用。缺一项必须回到 `amazon-competitor-analyzer` / `amazon-image-extractor` 修复后重渲染。
7. 运行/执行 `amazon-multi-asin-data-auditor` 的对齐审计逻辑；只有全部 PASS 才能进入综合沉淀。
8. 调用 `amazon-multi-asin-visual-synthesizer`，填写 `viz_data.json`，再用其 `scripts/build_viz_dashboard.py` 渲染综合 `index.html`。

## 5. 合格输出标准

单 ASIN 完整竞品分析必须至少交付：

- `<ASIN>_<时间戳>/competitor_analysis.md`
- `<ASIN>_<时间戳>/visual.json`
- `<ASIN>_<时间戳>/index.html`
- `<ASIN>_<时间戳>/metadata.json`
- `<ASIN>_<时间戳>/report.json`
- 若评论样本可用：`reviews_aggregate.json`、`review_evidence.json`、`review_dashboard.html`

只输出 Markdown、纯文字结论、评论摘要，或没有 `visual.json + index.html` 的结果，不能称为“单 ASIN 完整竞品分析完成”。

多 ASIN 综合竞品分析必须至少交付：

- `_compare_<时间戳>/viz_data.json`
- `_compare_<时间戳>/index.html`
- detail ASIN 的单品报告必须能显示套图与 A+：`report.json` 存在、图片相对路径可访问、`metadata.media` 计数非空、`index.html` 无空图 `src=""`。
- detail ASIN 的单品报告必须保留内容结构：`三-1 · 卖点排序 · 三层递进` 只能是 3 条中文摘要，禁止直接粘贴 Amazon 英文 bullet 长段；`三-2 · 信息层级 · A+ 分层拆解` 在 A+ 模块 ≥ 3 时必须出现，按主体写真/功能定位/信任状或兼容警告三层拆开。
- detail ASIN 的 SIF 结构必须保留：有 `keyword_arch.json` 时必须输出 `三-3 · 关键词架构`；有 `traffic_source.json` 时必须输出 `三-4 · 流量入口结构`。配置了 `LINKFOXAGENT_API_KEY` 却未生成两类 JSON 时，必须记录接口失败/无数据原因，不能静默省略。
- 顶部竞品基础数据对比表：主图、星级、评价数、价格、折扣、变体、BSR、吸力/磁力/旋转/兼容等可得规格。
- 详细层图表：评论痛点热力矩阵、市场定位气泡图、竞品 × 卖点关系网络、Kano 行业需求聚合。
- 全员图表：价格–口碑性价比矩阵，rough ASIN 以简析层参与。
- 可选图表：有 `traffic_mix` 时输出流量入口结构；有 `kw_arch` 时输出关键词架构。
- 每个 ASIN 卡片/表头可跳转到单品报告、评论看板或简析报告。

只输出 Markdown、手写简易 HTML、纯评论表格、或没有 `viz_data.json + index.html` 的结果，不能称为“多 ASIN 综合竞品分析完成”。

## 6. 降级规则

降级是最后兜底，不是默认路径。只有以下情况才允许降级：

- 用户明确要求“只用本地评论 JSON / 不联网 / 不抓页面 / 不生成看板 / 不生成 HTML / 只要文字”。
- 上游页面抓取、元数据抽取、评论/API 获取或脚本执行失败，且已尝试合理兜底后仍无法补齐。

发生降级时：

- 明确说明“当前只能做评论驱动降级分析，不是完整竞品综合看板”。
- 可输出评论痛点、好评驱动、改款机会、详细/简析文字报告。
- 不得伪装成 `amazon-multi-asin-visual-synthesizer` 的标准结果。
- 如用户要求标准结果，必须继续补齐 metadata、visual、评论聚合、图片/单品报告等输入。

## 7. 禁止行为

- 不得把“竞品分析一下这个 / 看下这个品 / 分析这个链接”默认路由到 `amazon-competitor-quick-analyzer`；这些普通表达默认是完整 HTML 分析。
- 不得在未生成 `index.html` 的情况下回复“完整分析完成”。
- 不得因为输入文件是 `*_reviews_US.json` 就直接把任务降级成评论分析；如果用户给了 ASIN 并要求竞品分析，必须先主动尝试补齐页面、图片、metadata、评论聚合和单品报告。
- 不得让 `linkfox-amazon-reviews` 单独承担“多个 ASIN + 详细/简析 + 综合分析”的最终交付。
- 不得绕过 `amazon-multi-asin-visual-synthesizer` 自带渲染器手写低保真综合看板。
- 不得在缺少完整输入时默默降级；必须显式标注降级原因和缺失项。
- 不得把“`gallery/` 目录里有图片”误判为单品报告图片链路可用；单品 HTML 渲染器读取的是 `report.json`，缺失或为空会导致左侧套图栏 `src=""`。
- 不得把 Amazon 原始英文 bullet 直接作为卖点排序正文；卖点排序是给中文决策者看的“三层递进摘要”，每条必须压缩为“中文短标题 + 一句中文证据/含义”。
- 不得把关键词架构、流量入口结构当作可有可无的装饰模块；详细报告具备 SIF 数据源时必须产出三-3/三-4，否则会造成用户看到的报告缺少流量侧判断。

## 8. 用户回复要求

交付时保持简短，给出核心文件路径和一句图表导读。若发生降级或快速文字分析，第一句说明“这是降级/快速文字分析，不是完整 HTML 报告”，并列出缺失的标准输入或用户指定的轻量限制。
