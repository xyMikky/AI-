# L2 Visual Harness · 子 Agent 看图盲测协议（单期严格隔离）

## 目标

在**不含后视偏差**的前提下，评测「人类/AI 看图定号」是否跑赢随机基线，并与 L1 算法同台对比。

## ⚠️ 污染事故教训（必读）

2026-06 对 100 期盲测 `l2-100` 曾出现**虚高命中率**（7+3 前区净差 +0.558 vs 随机，中奖率 +18.61%），主因：

| 风险 | 说明 |
|---|---|
| **10 期/批 subagent** | 同一 subagent 连续处理多期，批内上下文可能带入后验 |
| **答案留在 run 目录** | `answers_sealed.json` 可被误读 |
| **父 agent 已知 score** | 编排者在预测阶段已看过历史计分/对话 |
| **transcript 批量 ingest** | `record-batch` 落盘不能证明逐期看图 |

**严格重跑 `l2-100-single`（1 期 = 1 subagent + 答案移出 run）** 后结论反转：

| 格式 | 指标 | 严格单期 | vs 随机 |
|---|---|---:|---:|
| 7+3 | 前区/5 | 0.860 | **-0.142** |
| 7+3 | 中奖率 | 15.0% | **-2.39%** |
| 15+5 | 前区/5 | 2.020 | **-0.118** |
| 15+5 | 中奖率 | 63.0% | **-2.02%** |

> **`l2-100` 已列入污染名单**，`score` 时会拒绝计分。权威范例：`l2-100-single`。

---

## 与 L1 的分工

| 层 | 脚本 | 谁做预测 | 速度 | 盲测保证 |
|---|---|---|---|---|
| L1 | `harness.py` | `build_final_recommendation` | 秒级 × 数百期 | walk-forward 截断 |
| L2 | `harness_visual.py` | **空白子 agent 读 PNG** | 慢（**每期 1 subagent**） | 单期隔离 + 答案外置 |

---

## 单期严格隔离（默认 `--strict`，不可跳过编排规范）

### 硬性规则

1. **1 subagent = 1 期** — 禁止「10 期一批」「5 期一批」在同一 subagent 内连续预测
2. **prepare 后答案立即移出** — `answers_sealed.json` → `assets/visual_runs/_sealed_{run_id}.json`
3. **预测阶段禁止读取** — 封存答案、全库 JSON、其他 `periods/*`、父会话 score
4. **禁止 record-batch** — 除非 `--unsafe-allow-batch` 调试；不得用 transcript 批量 ingest 替代看图
5. **禁止复制其他 run 的 prediction** — `validate` 会检测多期完全相同指纹
6. **score 前必须 validate** — 污染 run 直接拒绝

### 目录结构（strict run）

```
assets/visual_runs/
├── _sealed_{run_id}.json      # 预测阶段答案在此（不在 run 内）
└── {run_id}/
    ├── manifest.json          # isolation.mode = single-period-strict
    ├── .strict_run            # 标记文件
    ├── README.txt
    ├── score_report.json      # score 后产出（含 validation）
    └── periods/{target_issue}/
        ├── meta.json
        ├── trend-50.png
        ├── local-trend-15.png
        ├── stats.txt
        ├── agent_prompt.md
        └── prediction.json    # record 后写入
```

计分瞬间：`restore-answers` 将 `_sealed_*.json` 临时移回 run 内供计分，之后可保留。

---

## 标准工作流（父 Agent 编排）

### 1. 准备 bundle（默认 strict）

```powershell
cd .cursor/skills/dlt-analysis
python scripts/harness_visual.py prepare --run-id my100 --periods 100 --format both
# 等价于 --strict（默认）；legacy 才用 --no-strict
```

prepare 完成后：**不得**读取 `_sealed_my100.json`。

### 2. 逐期派子 agent（关键 · 每期独立）

```powershell
python scripts/harness_visual.py next --run-id my100
```

对返回的 **单个** `pending`：

- 使用 **Task · generalPurpose · readonly=true**
- **仅**传入该 `period_dir` 内 4 文件：`agent_prompt.md`、`trend-50.png`、`local-trend-15.png`、`stats.txt`
- **禁止**：读取 `_sealed_*.json`、`answers_sealed.json`、全库 JSON、其他 period 目录、对话历史、批量处理多期
- 子 agent **只输出**单期 JSON

```json
{
  "target_issue": "26058",
  "method": "visual",
  "dispatch": { "isolation": "single", "issues_count": 1 },
  "predictions": {
    "7+3": {
      "front": [3, 8, 12, 19, 24, 28, 33],
      "back": [2, 5, 9],
      "reasoning": "15期小图 19 号趋势延长落点；50期大图 03 区偏冷回补…"
    },
    "15+5": { "front": [...], "back": [...], "reasoning": "..." }
  },
  "reviewed_charts": ["trend-50.png", "local-trend-15.png"]
}
```

**完成一期 → record → 再 next 下一期。** 不可循环「pending 10 期 → 一个 subagent 全做」。

### 3. 落盘预测（单期）

```powershell
python scripts/harness_visual.py record --run-id my100 --issue 26058 --file path/to/prediction.json
```

strict 模式下：若 `answers_sealed.json` 仍在 run 内，`record` 会拒绝。

### 4. 校验 + 计分

```powershell
python scripts/harness_visual.py validate --run-id my100
python scripts/harness_visual.py score --run-id my100 --compare-algo
```

`score` 自动执行 validate（可用 `--skip-validation` 仅调试污染 run）。

### 5. 进度查看

```powershell
python scripts/harness_visual.py status --run-id my100
```

---

## 父 Agent 派发模板（复制即用 · 单期）

```
你是空白上下文的看图分析子 agent（readonly）。
⚠️ 只处理 {target_issue} 这一期，禁止预测其他期号。

工作目录：{period_dir}
1. 读 agent_prompt.md
2. Read trend-50.png 与 local-trend-15.png
3. 读 stats.txt 作辅助
4. 按 manifest 格式输出严格 JSON（仅 JSON，无 markdown 包裹）
5. JSON 含 "dispatch": {"isolation": "single", "issues_count": 1}

禁止：_sealed_*.json、answers_sealed.json、lotto_history.json、
      其他期号目录、历史对话、批量多期预测
```

---

## 诚实性规则

1. **prepare 之后、score 之前**：编排者（父 agent）也不得读取封存答案
2. 子 agent 必须 **readonly**，避免误改 bundle
3. 单期高命中不可外推；以 `score` 聚合净差为准
4. L2 样本通常远小于 L1，净差波动更大；**必须 strict 单期隔离**才有可比性
5. 看图法长期**跑不赢随机**是正常结论（见 `l2-100-single`），不是失败

---

## 禁止行为清单

| 行为 | 后果 |
|---|---|
| 单 subagent 连续处理 2+ 期 | 批内上下文污染 → 虚高 |
| 父 agent 在 record 前读 `_sealed_*.json` | 后视偏差 |
| 用 `local_trend_chart.py` stdout 作素材 | 泄露算法 `final_recommendation` |
| `harness_visual_batch.py record-batch` 无 unsafe 标志 | 脚本拒绝 |
| `pending --limit 10` 无 unsafe 标志 | 脚本拒绝 |
| 引用 `l2-100` 作为有效证据 | 污染 run，score 拒绝 |
| 跳过 record 直接 score | 报错 |
| 从旧 run 复制 prediction.json | validate 指纹重复警告 |

---

## L2 + L1 融合修正（L2 为主 · L1 辅助）

看图定号（L2）完成后，可用 L1 算法（趋势+偏差带+超期+重号+空区）对号池做**有限替换修正**，不替代看图流程。

### 融合逻辑

```
合分 = L1归一化×1.0 + L2锚定×0.5 + 共识加成×0.4
共识 = L2 号 ∩ L1 前 2N 强候选 → 强制保留
替换 = 相对 L2 原号最多 ceil(N×35%) 个（7+3→2，15+5→5）
结构 = L1 三分区 ≥2 校验
```

### 命令

```powershell
# 单期或全 run 生成 prediction_fused.json
python scripts/harness_visual.py refine-l1 --run-id my100
python scripts/harness_visual.py refine-l1 --run-id my100 --issue 26067

# 计分时三轨对比：L2 / L1 / L2+L1 融合
python scripts/harness_visual.py score --run-id my100 --fuse-l1 --compare-algo
```

### 100 期 strict 实测（`l2-100-single`）

| 格式 | 轨 | 前区/5 | vs随机 | 中奖率 | vs随机 |
|---|---|---:|---:|---:|---:|
| 7+3 | L2 看图 | 0.860 | -0.138 | 15.0% | -2.17% |
| 7+3 | **L2+L1 融合** | 0.870 | -0.128 | 17.0% | -0.17% |
| 7+3 | L1 算法 | 0.920 | — | 14.0% | — |
| 15+5 | L2 看图 | 2.020 | -0.121 | 63.0% | -2.29% |
| 15+5 | **L2+L1 融合** | 2.090 | -0.051 | 61.0% | -4.29% |

融合可**略改善前区命中**（7+3 +0.01，15+5 +0.07），但**仍未稳定跑赢随机**；7+3 中奖率接近随机（-0.17%），15+5 中奖率反而略降。结论：L1 适合作结构/偏差修正，不是提概率银弹。

---

## 相关脚本

| 脚本 | 职责 |
|---|---|
| `harness_visual.py` | prepare / next / record / validate / score / seal-out |
| `harness_isolation.py` | 防泄漏校验、答案外置/恢复、污染名单 |
| `harness_visual_batch.py` | 辅助（默认 limit=1，batch 需 unsafe） |
| `harness_common.py` | 共用计分 |
| `harness.py` | L1 algo |

## 与「未来盲测」的关系

- 对**已开奖历史期**：L2 walk-forward 回测（本 harness，strict 单期）
- 对**未开奖未来期**：手动 seal 预测 → 开奖后单期对照，不走批量 score
