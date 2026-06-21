# 多 ASIN 数据对齐审计清单

## 核心原则

多 ASIN 竞品分析的风险不在于“原始文件里是否出现其它 ASIN”，而在于**实际用于报告、证据和看板的样本是否被正确过滤到目标 ASIN**。

因此审计分两层：

1. **原始层**：LinkFox 原始评论文件是否包含目标 ASIN，是否混入其它 ASIN。
2. **分析层**：`reviews_aggregate.json`、`review_evidence.json`、`review_dashboard.html` 是否只使用目标 ASIN。

默认只要分析层完全对齐，原始层混入同系列/变体 ASIN 记为 WARN，不判 FAIL。

## 必查文件

每个 ASIN 子目录至少检查：

- `metadata.json`
- `visual.json`
- `competitor_analysis.md`
- `index.html`（旧名 `competitor_analysis.html` 自动兼容）
- `reviews_aggregate.json`
- `review_evidence.json`
- `review_dashboard.html`
- `*reviews_linkfox_raw*.json`

## PASS 条件

- `metadata.json.asin` 等于目录名。
- `metadata.json.source_url` 包含目录 ASIN。
- `visual.json` 基础信息卡 ASIN 等于目录名。
- `visual.json`、Markdown、HTML 不含其它 ASIN。
- `reviews_aggregate.json.scope` 为 `single_asin:<目录ASIN>`。
- `reviews_aggregate.json.distinct_asin` 只含目录 ASIN。
- `review_evidence.json.asin` 等于目录 ASIN。
- `review_evidence.json.scope` 为 `single_asin:<目录ASIN>`。
- `review_evidence.json.overall.count` 等于原始评论文件中目标 ASIN 的条数。
- `review_dashboard.html` 不含其它 ASIN。

## WARN 条件

- 原始评论文件包含其它 ASIN，但目标 ASIN 存在，且分析层全部过滤正确。
- 原始评论文件没有逐条 ASIN 字段，但分析层 scope 明确是单 ASIN。
- 某个 ASIN 没有评论看板，且报告明确记录评论抓取失败原因。

## FAIL 条件

- 任一主产物引用了其它 ASIN。
- `metadata.json` 与目录名不一致。
- `review_evidence` 的 ASIN 或 scope 与目录名不一致。
- `review_evidence.overall.count` 与原始文件目标 ASIN 条数不一致。
- `review_dashboard.html` 混入其它 ASIN。
- `reviews_aggregate.distinct_asin` 顶层包含其它 ASIN，说明聚合输出没有明确表达实际分析样本。

## 交付前建议顺序

1. 跑 `amazon-competitor-analyzer` 完成 N 份单品报告。
2. 跑 `amazon-multi-asin-data-auditor`。
3. 若 FAIL，回到对应 ASIN 目录重跑失败阶段。
4. 全部 PASS 后，再询问用户是否进入 `amazon-multi-asin-visual-synthesizer`。
