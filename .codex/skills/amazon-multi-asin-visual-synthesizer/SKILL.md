---
name: amazon-multi-asin-visual-synthesizer
description: Amazon 多 ASIN 竞品「综合可视化沉淀」专家——在 amazon-competitor-analyzer 完成 N 份单品三件套之后被调用，从 N 份单品 visual.json / metadata.json / 评论聚合中跨家归并，渲染一张离线自包含 HTML 综合看板（内联 ECharts），含至多 7 张非常规图表：① 评论痛点强度热力矩阵（整行偏红=全行业共同盲区）② 市场定位气泡图（星级×评价数体量）③ 竞品 × 卖点 关系网络图（力导向二部图，红海共性卖点 vs 蓝海盲区机会）④ Kano 行业级需求聚合（基本型/期望型/兴奋型，Y 轴信号强度由评论关键词提及量数据驱动派生、可溯源）⑤ 价格–口碑性价比矩阵（X=价格/Y=星级/气泡=评价数，价格中位×口碑中位切四象限）⑥ 流量入口结构对比（曝光来源自然/SP/SB/SBV/推荐位 100% 堆叠，需 traffic_mix）⑦ 关键词架构矩阵（自然流量占比×流量词总数，需 kw_arch）。支持「详细/简析」双层竞品：详细层(完整三件套)驱动图1-4/6/7，简析层(仅元数据+评论、无六维评分)以菱形点专属参与图⑤与顶部卡片。硬触发：只要用户给出多个 ASIN/多个竞品，并指定部分详细分析、其他简要/简析/粗看，或要求横向对比、综合分析、竞品对比、看板，即使没有说“可视化”，也必须优先使用本 Skill，而不是仅用评论 Skill。图⑥⑦ 数据来自 amazon-competitor-analyzer 阶段②.8 的 SIF asinSummary/asinKeywords。顶部附「竞品基础数据对比」转置表格（行=属性 / 列=竞品，含产品主图 base64 内联 + 星级/价格/折扣/变体/吸力/磁力等逐项对比 + 一键跳转各 ASIN 竞品报告 / 评论看板 / 简析）。本 Skill 替代旧的 amazon-competitor-comparison-synthesizer（纯文字红色对比沉淀），改为以可视化为核心的综合分析。适用：跑完 ≥2 个 SKU 竞品分析后做"战略级综合可视化沉淀"、给客户/老板做横向可视化汇报、为本品提炼"红海同质 vs 蓝海机会"。关键词：综合分析、综合可视化、多 ASIN 可视化、多个ASIN、详细分析、简要分析、详细/简析、对比总结、对比沉淀、竞品对比、横向对比、热力矩阵、市场定位气泡图、关系网络图、Kano 需求聚合、行业共性、蓝海机会、可视化看板。
---

# Amazon 多 ASIN 综合可视化沉淀专家

> ⚠️ **本 Skill 不抓取页面、不评分单品**。它是一个**可视化沉淀器**：消费 `amazon-competitor-analyzer` 已经产出的 N 份单品三件套，跨家归并后渲染成一张**自包含 HTML 综合可视化看板**（至多 7 图 + 竞品基础数据对比表格 + 跳转链接）。
>
> ℹ️ 本 Skill 替代了旧的 `amazon-competitor-comparison-synthesizer`（纯文字红色对比沉淀模板）。沉淀的"骨架"从"文字三件套"升级为"4 张非常规图表 + 数据卡片"。

## 1. 何时使用

### 1.1 自动触发（首选）

`amazon-competitor-analyzer` 跑完所有单品三件套后，必须 `request_user_input` 询问用户后续动作；当用户选择 **"对比总结 / 综合分析 / 可视化沉淀 / 横向沉淀"** 分支时，本 Skill 被自动调度。

### 1.2 用户直接触发

用户说出以下任一表述时也直接进入本 Skill：

- "综合分析 / 综合可视化 / 可视化沉淀 / 对比总结 / 对比沉淀 / 横向沉淀"
- "多个 ASIN / 多个竞品 / 这几款竞品"，并指定"详细分析 / 简要分析 / 简析 / 部分详细其他简要"
- "把这几款做一份综合可视化"、"做一个可视化看板"、"做一份战略对比"
- "热力矩阵 / 市场定位气泡图 / 关系网络图 / Kano 行业聚合"中任一图表诉求

> 前提：必须已存在至少 2 份单品三件套（`competitor_analysis.md`(或旧名) / `visual.json` / `competitor_analysis.html`(或 `index.html`)），通常位于 `生成结果输出/amazon图片提取/_compare_<时间戳>/<ASIN>/`。如果还没跑单品三件套，**先回退到 `amazon-competitor-analyzer`，不要从零开始**。

### 1.3 路由硬规则

- 当用户给多个 ASIN 并区分"详细层 / 简析层"时，本 Skill 优先级高于 `linkfox-amazon-reviews`；评论 Skill 只能作为数据源，不能作为最终交付。
- 如果输入只有裸 `*_reviews_US.json`，不得直接降级；必须先回到 `amazon-competitor-analysis-controller` / `amazon-competitor-analyzer`，根据 ASIN 主动补齐 `metadata.json / visual.json / reviews_aggregate.json / review_evidence.json / gallery` 等标准输入。只有用户明确限制“只用本地评论文件/不要联网/不要抓页面”，或上游连续失败时，才允许评论驱动降级分析。
- 若存在 `_compare_<时间戳>/`，必须优先读取该目录及各 ASIN 子目录，而不是从零手写看板。

## 2. 输入

| 项 | 必填 | 说明 |
|---|---|---|
| 详细层单品三件套目录 | 必填 | `_compare_<时间戳>/` 下 N 个详细 ASIN 子目录（每个含 visual.json + 报告 html + gallery/）。驱动图1-4 + Kano + 图5 + 卡片 |
| 简析层 ASIN 目录 | 可选 | `_compare_<时间戳>/` 下做过"评论驱动简版分析"的 ASIN 子目录（含 metadata.json + reviews_aggregate.json + review_evidence.json + brief_analysis.md + review_dashboard.html，但**无 visual.json / 六维评分**）。仅参与**图5 价格–口碑性价比矩阵**与顶部竞品卡片，不进图1-4，保持详细层口径严谨 |
| 品类描述 | 可选 | 例如 "车载磁吸手机支架"；缺省时从 metadata.title 自动推断 |
| 关注维度 | 可选 | 用户特别想强调的角度（如视觉策略 / 痛点缺口 / Kano / 价格定位） |

> ℹ️ **双层竞品模型（V1.1 新增）**：契约 `competitors[]` 每项可声明 `tier`——`detail`（默认，完整三件套）或 `rough`（简析层）。简析层 ASIN 凭 `metadata.json`(star/rc/bsr/price) + `reviews_aggregate.json`(sample) + `review_evidence.json`(crit/pos 命中量) 即可入图5 与卡片，`dims`/`total` 可省略（渲染器不读 dims，total 缺失显示"—"）。卡片自动打"简析"徽标、报告按钮指向 `brief_analysis.md`。

## 3. 工作流（4 步）

```
① 加载详细层 N 份单品 visual.json / metadata.json / 评论聚合 → 抽取评分六维、好评/差评关键词命中量、品牌星级评价数 BSR 价格
   （如有简析层 ASIN：仅读 metadata.json + reviews_aggregate.json + review_evidence.json，抽 star/rc/bsr/price/sample/crit/pos）
   （如有 SIF 数据：读各 ASIN 的 keyword_arch.json / traffic_source.json（analyzer 阶段②.8 产出），抽 traffic_mix + kw_arch → 图⑥⑦）
② 跨家归并 → 痛点矩阵(行=痛点列=竞品) / 定位坐标 / 共性卖点&盲区节点&边 / Kano 派生（均仅用详细层）
   + 价格–口碑性价比坐标（详细 + 简析 全员，X=price / Y=star / 体量=rc）
③ 填写数据契约 viz_data.json（结构见 §4 + templates/viz_data_template.json；简析层标 tier:"rough"）
④ 调用 build_viz_dashboard.py → 渲染自包含 HTML 综合看板（含图5）
```

### Step 1：加载与抽取（Agent 判断，不靠脚本解析）

对每个 `<ASIN>/visual.json` 与 `metadata.json` 按需读取：

- `summary` 加权总分、`sections.score-cards` 六维细分
- `metadata`：品牌、星级 star、评价数 rc、类目 BSR、价格（常缺失）
- 评论聚合 / `review-sentiment`：好评关键词命中量、差评关键词命中量（按你统一的痛点/好评分类聚合）
- **`basics`（竞品基础数据对比表格）**：从各 `metadata.json` 直取 `price.current/list`（→ `deal_price/list_price`，并算 `discount_pct`）、`variations.colors.count/sizes.count`（→ `color_variants/size_variants`）；从 `bullets[]`/`specs[]` 解析品类专属规格（如吸力 `78 LBS`、磁力 `2400 gf`、旋转 `360°`、承重、兼容机型等），写入各家 `basics{}`，并在顶层 `basics_rows` 声明这些专属行的标签与顺序。`monthly_sales/launch_date` 当前无数据源、统一填 `"—"`。

> 关键：**痛点清单（pains）、好评关键词（pos_kw）、各家命中量（crit / pos_matrix）、Kano 归类（kano_def）由 Agent 阅读后判断填写**——脚本不解析 visual.json（结构多变、需要语义判断）。痛点/好评分类务必跨家统一口径，否则热力矩阵与 Kano 会失真。

### Step 2：跨家归并

| 产出 | 来源 | 用途 |
|---|---|---|
| **痛点矩阵** | 各家差评命中量 ÷ 样本量 | 图① 热力矩阵（整行偏红=共同盲区） |
| **定位坐标** | 星级 × 评价数（价格缺失时） | 图② 气泡图 |
| **共性卖点 / 盲区节点** | 各家普遍强调点 / 普遍没讲透点 | 图③ 关系网络图（红海 vs 蓝海） |
| **Kano 派生** | 好评/差评关键词提及量按规则映射 | 图④ Kano 行业聚合 |

### Step 3：填写数据契约

复制 `templates/viz_data_template.json`，按真实数据填写到 `_compare_<时间戳>/viz_data.json`（直接放在 compare 根目录，与各 ASIN 子目录平级）。字段速查见 §4。

### Step 4：调用渲染脚本（强制）

```powershell
python ".codex/skills/amazon-multi-asin-visual-synthesizer/scripts/build_viz_dashboard.py" `
  --data "生成结果输出/amazon图片提取/_compare_<时间戳>/viz_data.json" `
  --compare-dir "生成结果输出/amazon图片提取/_compare_<时间戳>"
```

完成标准：必须在 compare 根目录生成 `viz_data.json` 和自包含 `index.html`。如果只输出 Markdown、评论摘要、手写 HTML、或没有调用本 Skill 的 `build_viz_dashboard.py`，则多 ASIN 综合可视化任务未完成。

默认输出 `_compare_<时间戳>/index.html`（直接落在 compare 根目录，与各 ASIN 子目录平级）。脚本自动：从各 `<ASIN>/gallery/01_*` 取主图缩略并 base64 内联、探测各 ASIN 的竞品报告 / 评论看板 / 简析报告生成相对跳转链接、内联本 skill `assets/echarts.min.js`。

> ⚠️ 渲染脚本必须从**工作区根目录**执行，输出 HTML 留在 `_compare_<时间戳>/` 根目录——卡片里的 `<ASIN>/...` 相对链接（如 `<ASIN>/index.html`、`<ASIN>/review_dashboard.html`、`<ASIN>/brief_analysis.md`）才能正确指向各单品报告 / 看板 / 简析。注意：综合看板自身是 compare 根目录的 `index.html`，各单品报告是 `<ASIN>/index.html`，同名但分属不同目录、互不冲突。

## 4. 数据契约 viz_data.json 字段速查

| 字段 | 必填 | 说明 |
|---|---|---|
| `title` | 可选 | 看板标题 |
| `category` | 建议 | 品类描述，写进 Hero 与摘要卡 |
| `pains` | 必填 | 差评痛点维度清单（行 = 热力矩阵行 / Kano c 类指向） |
| `pos_kw` | 必填 | 好评关键词清单（Kano p 类指向） |
| `p_label` / `c_label` | 可选 | Kano 构成明细的显示名（缺省自动用 "好评·xx" / "差评·xx"） |
| `competitors[]` | 必填 | 每家：`name / asin / star / rc / bsr / sample / crit[]（对应 pains） / pos_matrix[]（对应 pos_kw）`；可选 `tier`("detail"默认 / "rough"简析层) / `price`(USD 数值，图5 X 轴用) / `total` / `dims[6]`（简析层可省略，渲染器不读 dims、total 缺失显示"—"） |
| `price` | 建议 | 每家 USD 价格，驱动图5 价格–口碑性价比矩阵；详细层也应补上，全员有价才能切四象限 |
| `traffic_mix` | 可选 | 仅详细层 · `{nat,sp,sb,sbv,rec}` 曝光占比(0–1)，来自 SIF asinSummary（`amazon-competitor-analyzer` 阶段②.8 的 `traffic_source.json`），驱动**图⑥ 流量入口结构对比** |
| `kw_arch` | 可选 | 仅详细层 · `{organic_share,paid_share,nf_count,ad_count,total_kw,top_kw_sv}`，来自 SIF asinKeywords/asinSummary（`keyword_arch.json`），驱动**图⑦ 关键词架构矩阵** |
| `basics` | 可选 | detail/rough 均可填 · 「竞品基础数据对比」表格逐家数据。通用键 `deal_price/list_price/discount_pct/monthly_sales/launch_date/color_variants/size_variants`（星级/评价数/BSR/现价缺失时回退顶层 `star/rc/bsr/price`）+ 品类专属键（如 `suction_power/magnetic_force/rotation/compatibility`，由顶层 `basics_rows` 声明标签与顺序）。来源：各 ASIN `metadata.json` 的 `price/variations` 直取 + `bullets[]/specs[]` 解析。值缺失填 `"—"` 或省略；整行所有竞品都缺则该行不渲染。`monthly_sales/launch_date` 当前 metadata 无数据源、统一填 `"—"` |
| `basics_rows` | 可选 | 顶层字段（非 competitors 内）· `[{key,label}]`，声明对比表格中**品类专属属性行**的键、显示标签与顺序（key 对应各家 `basics` 内的键）；通用商业行由脚本内置无需声明 |
| `common_sells[]` | 必填 | 共性卖点（红海节点，每个连向全部竞品） |
| `gap_nodes[]` | 可选 | 盲区机会（蓝海节点，挂在 hub 上） |
| `hub_name` | 可选 | 本品切入枢纽名（默认"本品机会切入"） |
| `kano_def[]` | 必填 | 每项：`band(1/2/3) / name / hit(命中家数→气泡大小) / comps([["c"或"p", 关键词下标, 权重], ...])` |
| `kano_band_labels` | 可选 | 三档显示名 |
| `palette` | 可选 | 竞品配色 |
| `summary_cards` | 可选 | 顶部摘要卡；不填脚本自动派生（竞品数 / 龙头 / 口碑带 / 共同盲区） |

> Kano Y 轴（行业信号强度）= Σ(comps 指向关键词的**全行业提及量** × 权重)，再归一到 1.5–9.5。规则：基本型→相关差评量，兴奋型→相关好评量，期望型→好评+相关差评合计。悬停看构成明细，可溯源到具体评论计数。

## 5. 标准产物

```
_compare_<时间戳>/                ← 与各 ASIN 子目录平级，直接落在 compare 根目录
├─ <ASIN_1>/ … <ASIN_N>/      ← 各单品三件套 / 简析目录
├─ viz_data.json              ← 数据契约（人类可读存档，可复跑）
└─ index.html                 ← 自包含 HTML 综合看板（内联 ECharts + base64 主图）
```

看板结构（从上到下）：Hero 标题 → 4 张摘要 KPI 卡 → **竞品基础数据对比表格**（转置：行=属性 / 列=竞品；左列属性名固定吸附、横向滚动浏览全部竞品；列头含主图 + 品牌 + ASIN + 跳转竞品报告/评论看板按钮，简析层列头带"简析"徽标 + 指向 `brief_analysis.md` 的"简析报告"按钮；行含星级/评价数/BSR/现价/原价/折扣/月销/上架/变体等通用行 + `basics_rows` 声明的吸力/磁力/旋转/兼容等品类专属行，整行全缺自动跳过）→ **图① 评论痛点强度热力矩阵**（仅详细层）→ **图② 市场定位气泡图**（仅详细层）→ **图③ 竞品 × 卖点 关系网络图**（仅详细层）→ **图④ Kano 行业级需求聚合**（仅详细层）→ **图⑤ 价格–口碑性价比矩阵**（详细 + 简析 全员；X=价格$ / Y=全局星级 / 气泡=评价数；价格中位×口碑中位切四象限：性价比甜区/溢价品质/低质走量/危险区；简析点用菱形虚边区分）→ **图⑥ 流量入口结构对比**（详细层 · 带 `traffic_mix` 时；曝光来源 100% 堆叠条）→ **图⑦ 关键词架构矩阵**（详细层 · 带 `kw_arch` 时；自然流量占比×流量词总数）→ 数据适配说明 footer。

> 图⑤ 是简析层 ASIN 的**专属参与角度**：它只依赖详细与简析共有的 price/star/rc，不依赖六维页面评分，因此简析款能以一等公民身份进入，并以价格跨度补全行业定价分布，帮本品找定价空位。

**图⑥ 流量入口结构对比（详细层 · 可选）**：当详细层竞品带 `traffic_mix` 时渲染——各竞品曝光来源 100% 堆叠条（自然搜索/SP/品牌/视频/推荐位），一眼看出"谁靠自然吃饭、谁在烧广告"。

**图⑦ 关键词架构矩阵（详细层 · 可选）**：当详细层竞品带 `kw_arch` 时渲染——散点 X=自然流量占比% / Y=流量词总数 / 气泡=头部词周搜索量，50% 处虚线为"自然 vs 广告驱动"分界，据此判断本品关键词布局（右上=自然且词广=健康，左下=词窄靠广告=脆弱）。

> 图⑥⑦ 数据来自 `amazon-competitor-analyzer` 阶段②.8（SIF asinSummary/asinKeywords）。仅详细层参与，保持与图1-4 同口径严谨；简析层不带这两字段时自动不进这两图。

## 6. ❌ 禁止行为

- ❌ **让脚本去解析 visual.json**：痛点/好评分类与 Kano 归类需要语义判断，必须由 Agent 抽取后填契约
- ❌ **痛点 / 好评分类各家口径不一致**：热力矩阵与 Kano 会因口径错位而失真
- ❌ **把 viz_data 数值"凭印象"编造**：每个 crit / pos_matrix 数字必须能在对应单品报告 / 评论聚合中找到来源
- ❌ **把输出 HTML 挪出 `_compare_<时间戳>/` 根目录**：会导致 `<ASIN>/...` 跳转链接失效（链接是相对 compare 根目录的）
- ❌ **跨家总分浮夸**：摘要里出现的总分必须等于对应单品 `visual.json.summary` 的总分
- ❌ **复用单品渲染脚本 `render_report_html.py`**：本 Skill 自带 ECharts 渲染器，不走单品模板

## 7. ✅ 正确行为

- 先把 N 家的痛点/好评分类统一为同一套 `pains` / `pos_kw`，再逐家填命中量
- Kano `kano_def` 的每条 `comps` 都明确指向 pains/pos_kw 下标，使 Y 轴可溯源
- 价格普遍缺失时坦诚用"星级 × 评价数"定位，并在 footer 说明（脚本已内置该说明）
- 渲染后在浏览器（或本地 http 服务）抽检：各图渲染正常、对比表格左列吸附 + 横向滚动正常、表格列头主图与跳转链接可点、Kano 气泡不被裁切
- 交付回复 ≤ 200 字，给出 HTML 路径 + 4 图一句话导读，不在对话里堆砌数据表

## 8. 输出后对话回复（≤ 200 字）

```
✅ 多 ASIN 综合可视化沉淀已生成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 index.html（自包含，内联 ECharts + 产品主图）
📂 生成结果输出/amazon图片提取/_compare_<时间戳>/

含至多 7 图：痛点强度热力矩阵（找共同盲区）/ 市场定位气泡图（看口碑×体量）/
竞品×卖点关系网络图（红海同质 vs 蓝海机会）/ Kano 行业需求聚合（基本-期望-兴奋）/
价格–口碑性价比矩阵（含简析层，看定价空位）/ 流量入口结构对比（自然 vs 广告，需 traffic_mix）/
关键词架构矩阵（自然占比×词库宽度，需 kw_arch）。
顶部「竞品基础数据对比表格」逐项对比各家规格，列头可点击跳转各 ASIN 竞品报告 / 评论看板（简析层带"简析"徽标 + brief 链接）。
```

## 9. 相关脚本与产物路径

- `.codex/skills/amazon-multi-asin-visual-synthesizer/scripts/build_viz_dashboard.py`（**本 Skill 唯一渲染器** · 数据契约 → 自包含 HTML）
- `.codex/skills/amazon-multi-asin-visual-synthesizer/templates/viz_data_template.json`（数据契约模板兼可运行样例）
- `.codex/skills/amazon-multi-asin-visual-synthesizer/assets/echarts.min.js`（本地 ECharts 库 · 被渲染脚本内联进 HTML）
- 单品三件套来源：`生成结果输出/amazon图片提取/_compare_<时间戳>/<ASIN>/`
- 本 Skill 输出：`生成结果输出/amazon图片提取/_compare_<时间戳>/`（根目录下的 `viz_data.json` + `index.html`）

> 本 Skill **自包含**（自带渲染脚本 + ECharts 库），不依赖其它 Skill 的脚本。

## 10. 与 amazon-competitor-analyzer 的协作关系

```
amazon-competitor-analyzer
   ├─ Step 1-4  抓取 + 元数据 + 评分 + 单品三件套（每个 SKU 各一份）
   └─ Step 5    request_user_input 询问用户：
                  A. 补充内容（继续在 analyzer 内修订）
                  B. 综合可视化沉淀  ← 触发本 Skill
                  C. 都不需要
                       ↓
                       amazon-multi-asin-visual-synthesizer
                          └─ 输出 _compare_<时间戳>/{viz_data.json, index.html}
```

本 Skill **不重复** analyzer 的工作（不再抓页面、不再算六维评分），只做"基于已有评分 + 评论聚合的跨家可视化归并"。建议在 `amazon-multi-asin-data-auditor` 全部 PASS 后再进入本 Skill，确保单品数据源未错位。
