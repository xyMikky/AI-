---
name: amazon-multi-asin-data-auditor
description: Amazon 多 ASIN 竞品分析数据对齐审计工具。用于 amazon-competitor-analyzer 完成多 SKU 输出后，检查每个 ASIN 子目录中的 metadata、Markdown、visual.json、HTML、评论聚合、评论证据和评论看板是否全部指向同一目标 ASIN，防止多 ASIN 批处理时发生目录串号、评论样本串号、看板混入其它变体 ASIN 或报告引用错位。适用于“核对数据是否错位”“多 ASIN 分析数据校验”“评论数据有没有串 ASIN”“批量竞品报告交付前审计”等场景。关键词：多ASIN核对、ASIN对齐、数据错位、评论串号、竞品分析校验、review dashboard、metadata、visual.json、review_evidence、asin alignment。
---

# Amazon 多 ASIN 数据对齐审计

## 概述

这个 Skill 是 `amazon-competitor-analyzer` 的交付后审计工具，专门解决多 ASIN 批量竞品分析最容易出错的问题：**一个 ASIN 的报告、元数据、评论样本或看板误用了另一个 ASIN 的数据**。

它只做只读核对，不做竞品分析本身，不重写报告内容。发现错位后，返回明确的失败项，交给 `amazon-competitor-analyzer` 或相关脚本重跑对应阶段。

## 何时使用

当出现以下任一场景时使用：

- 用户要求“核对多 ASIN 数据是否错位”
- 用户担心“多个 ASIN 分析时数据串了 / 评论串了 / 看板错位”
- `amazon-competitor-analyzer` 完成 `_compare_<timestamp>/` 多 SKU 目录后，交付前做最终 QA
- 修改了 `keywords.json`、`aspects.json`、`reviews_aggregate.json`、`review_dashboard.html` 后，需要确认所有产物仍对齐目标 ASIN
- 多 ASIN 横向综合可视化沉淀前，需要确认单品报告作为数据源没有错位

不接管的场景：

- 抓取 Amazon 套图 / A+ 图 → 走 `amazon-image-extractor`
- 生成单品竞品报告 → 走 `amazon-competitor-analyzer`
- 横向综合可视化沉淀 → 走 `amazon-multi-asin-visual-synthesizer`
- 修复评论分类语义错误 → 回到 `amazon-competitor-analyzer` 重新策展 `keywords.json` / `aspects.json`

## 输入

必填：

- `--compare-dir`：多 ASIN 父目录，通常是：

```powershell
生成结果输出/amazon图片提取/_compare_YYYYMMDD_HHMMSS
```

可选：

- `--asins`：逗号分隔的 ASIN 白名单。不传则自动扫描父目录下的 `B0XXXXXXXX` 子目录。
- `--output`：审计 JSON 输出路径。不传则写入 `<compare-dir>/asin_alignment_audit.json`。
- `--strict-raw`：严格模式。若原始评论文件含非目标 ASIN，直接判 FAIL。默认只要后续过滤产物正确，原始文件混入同系列 ASIN 只作为 WARN。

## 核心审计项

每个 ASIN 子目录会检查：

1. **目录与基础文件**
   - 子目录存在
   - `metadata.json`
   - `visual.json`
   - `competitor_analysis.md`
   - `index.html`（旧名 `competitor_analysis.html` 自动兼容）

2. **元数据对齐**
   - `metadata.json.asin == 子目录名`
   - `metadata.json.source_url` 包含目标 ASIN

3. **主报告对齐**
   - `visual.json` 基础信息卡里的 ASIN 等于目标 ASIN
   - `visual.json` 文本中没有其它 ASIN
   - `competitor_analysis.md` 没有其它 ASIN
   - `index.html`（旧名 `competitor_analysis.html`）没有其它 ASIN

4. **评论链路对齐**
   - 原始评论文件存在，且包含目标 ASIN
   - `reviews_aggregate.json.scope == single_asin:<目标ASIN>`
   - `reviews_aggregate.json.distinct_asin` 只包含目标 ASIN
   - `review_evidence.json.asin == 目标ASIN`
   - `review_evidence.json.scope == single_asin:<目标ASIN>`
   - `review_evidence.json.overall.count` 等于原始评论文件中目标 ASIN 的评论条数
   - `review_dashboard.html` 不包含其它 ASIN

5. **原始评论变体风险**
   - LinkFox 原始评论文件可能混入同系列/变体 ASIN，这是常见现象。
   - 默认模式下，只要聚合、证据和看板均已过滤到目标 ASIN，就标记为 WARN 而不是 FAIL。
   - `--strict-raw` 模式下，原始文件混入其它 ASIN 也会判 FAIL。

## 标准命令

```powershell
$env:PYTHONIOENCODING="utf-8"
python ".cursor/skills/amazon-multi-asin-data-auditor/scripts/audit_asin_alignment.py" `
  --compare-dir "生成结果输出/amazon图片提取/_compare_20260608_113643"
```

指定 ASIN：

```powershell
python ".cursor/skills/amazon-multi-asin-data-auditor/scripts/audit_asin_alignment.py" `
  --compare-dir "生成结果输出/amazon图片提取/_compare_20260608_113643" `
  --asins "B0DN1S1YLV,B0DRPCD2GZ"
```

严格模式：

```powershell
python ".cursor/skills/amazon-multi-asin-data-auditor/scripts/audit_asin_alignment.py" `
  --compare-dir "生成结果输出/amazon图片提取/_compare_20260608_113643" `
  --strict-raw
```

## 输出

控制台会输出每个 ASIN 的 PASS / FAIL 和逐项检查结果。

同时写入：

```text
<compare-dir>/asin_alignment_audit.json
```

输出结构：

```json
[
  {
    "asin": "B0DN1S1YLV",
    "status": "PASS",
    "checks": [
      {
        "name": "metadata_asin_matches_dir",
        "ok": true,
        "detail": "metadata.asin=B0DN1S1YLV"
      }
    ],
    "warnings": [
      "Raw review file contains non-target ASINs..."
    ]
  }
]
```

## 通过标准

只有以下条件全部满足，才可认为多 ASIN 数据没有错位：

- 所有 ASIN `status == PASS`
- `metadata` / `source_url` / `visual` / `md` / `html` 均只指向各自目标 ASIN
- 评论聚合和证据均为 `single_asin:<目标ASIN>`
- `review_evidence.overall.count` 与原始文件中目标 ASIN 评论数一致
- `review_dashboard.html` 不混入其它 ASIN

允许存在的 WARN：

- 原始 LinkFox 文件里包含少量同系列/变体 ASIN，但后续 `reviews_aggregate`、`review_evidence`、`review_dashboard` 均已过滤到目标 ASIN。

## 失败处理

常见失败与处理方式：

| 失败项 | 含义 | 处理 |
|---|---|---|
| `metadata_asin_matches_dir` FAIL | 目录和 metadata 串号 | 重新跑该 ASIN 的素材采集 / metadata 抽取 |
| `visual_contains_no_other_asins` FAIL | `visual.json` 引用了其它 ASIN | 修正 `visual.json` 后重渲染 HTML |
| `aggregate_scope_matches_target` FAIL | 评论聚合没有按目标 ASIN 过滤 | 重跑 `aggregate_reviews_json.py --meta <metadata.json>` |
| `evidence_count_matches_raw_target_count` FAIL | 证据样本数和目标 ASIN 原始评论数不一致 | 重跑 `extract_review_evidence.py`，确认使用目标 ASIN 的 metadata |
| `dashboard_contains_no_other_asins` FAIL | 看板 HTML 混入其它 ASIN | 重跑 `build_review_dashboard.py --meta <metadata.json>` |

失败时不要继续做横向综合可视化沉淀，因为它会继承单品报告的数据错误。

## 与其它 Skill 的关系

- 上游：`amazon-competitor-analyzer`
  - 多 ASIN 分析完成后调用本 Skill 做交付前审计。
- 下游：`amazon-multi-asin-visual-synthesizer`
  - 只有本 Skill 全部 PASS 后，才建议进入横向综合可视化沉淀。
- 同级工具：`linkfox-amazon-reviews`
  - 原始评论文件可包含同系列 ASIN，本 Skill 负责确认后续产物是否正确过滤。

## 注意事项

- 本 Skill 只读，不修改文件。
- 路径含中文时，执行前设置 `$env:PYTHONIOENCODING="utf-8"`。
- 不要把原始评论文件混入其它 ASIN 直接等同于分析错位；关键看 `reviews_aggregate`、`review_evidence` 和 `review_dashboard` 是否已按目标 ASIN 过滤。
- 多 ASIN 对比总结前必须先跑本 Skill，否则评分和评论结论可能继承串号数据。
