---
name: dlt-analysis
description: "大乐透数据分析、可视化与趋势预测。六程序：① 基本走势图(50期) ② 冷热统计 ③ 局部趋势(15期) ④ 偏差值(趋势落点±N回测) ⑤ 空区分析(三分区周期+回测) ⑥ 全局视觉预测。纯趋势精确率约20%须偏差带扩展；严格空区为弱事件(回测验证)。数据内置 assets/lotto_history.json。"
---

# 大乐透分析（DLT Analysis）

超级大乐透数据分析与预测 skill。六程序：**基本走势图** · **统计分析** · **局部趋势** · **偏差值** · **空区分析** · **全局视觉预测**。

> **定号规格（全局统一）**：每次预测**固定输出 7 个前区 + 3 个后区（7+3）**，可自定义码数（如 15+5 宽复式，传 `front_count`/`back_count`）。`local_trend_chart.py` 报告底部的「★ 本期推荐定号」整合 **趋势落点 + 偏差带 + 超期回补 + 空区弱权重 + 重号保护**（上期号保底进池）后输出。此为加权候选池（复式参考），非投注建议。
>
> ⚠️ **诚实声明（harness.py 盲测 300 期）**：前区任何方法长期均**跑不赢随机基线（7+3 模型 0.903 vs 随机 0.999/5，净差 -0.096）**，模型甚至略低；后区仅 +0.034 微弱净差（大概率噪声）。各信号的价值是**让定号逻辑可解释、结构均衡**，**不是提高命中率**。单期高命中属方差，不可外推。彩票每期独立随机，仅供娱乐。复核：`python scripts/harness.py --periods 300 --format both`。
>
> ⚠️ **L2 看图盲测（harness_visual.py）额外声明**：必须用**单期严格隔离**（默认 `--strict`：1 subagent = 1 期 + 答案移出 run）。旧 run `l2-100`（10 期/批 subagent）命中率虚高，**已作废**；权威 100 期结论见 `l2-100-single`（看图法前区/中奖率均**略低于随机**）。编排规范见 [references/VISUAL_HARNESS.md](references/VISUAL_HARNESS.md)。

## 数据文件

数据已内置在 skill 内，**自包含、无需依赖桌面路径**：

| 优先级 | 路径 | 说明 |
|--------|------|------|
| 1（默认） | `.cursor/skills/dlt-analysis/assets/lotto_history.json` | skill 内置，2881 期 |
| 2（备用） | `~/Desktop/lotto-20260101.json` | 用户桌面更新包 |

查看当前数据摘要：

```bash
python ".cursor/skills/dlt-analysis/scripts/trend_chart.py" --info
```

JSON 结构：

```json
{ "issue": "26067", "main": ["06","16","18","19","28"], "bonus": ["07","11"] }
```

| 字段 | 说明 |
|------|------|
| `issue` | 期号（5 位字符串） |
| `main` | 前区 5 个号码（01–35，不重复） |
| `bonus` | 后区 2 个号码（01–12，不重复） |

**当前库**：2881 期 · `07005` — `26067` · 最新开奖 `06 16 18 19 28 + 07 11`

数据按 `issue` 升序处理；走势图窗口内**从旧到新**排列（与官网走势图一致）。

### 更新数据

用户提供新 JSON 时，复制覆盖 `assets/lotto_history.json` 并运行 `--info` 验证期数与最新期号。

---

## 程序一：基本走势图

### 功能

输出指定期号**往前 X 期**（默认 50）的大乐透基本走势图，支持 **PNG 图片**（默认）与 **HTML**：

- 前区 01–35：中奖号红球，未中奖显示**遗漏值**
- 后区 01–12：中奖号蓝球，未中奖显示遗漏值
- 前区按 01–12 / 13–24 / 25–35 三组分隔
- 辅助列「和尾」= 前区 5 个号码之和的个位数

遗漏值计算使用窗口**之前全部历史**，首行遗漏与官网逻辑一致。

依赖：`Pillow`（`pip install pillow`），Windows 下使用系统微软雅黑字体渲染中文标题。

### 执行方式

```bash
python ".cursor/skills/dlt-analysis/scripts/trend_chart.py" [选项]
```

### 参数

| 参数 | 简写 | 默认 | 说明 |
|------|------|------|------|
| `--issue` | `-i` | 最新期 | 基准期号 |
| `--count` | `-n` | `50` | 往前期数 |
| `--data` | `-d` | skill 内置 JSON | 自定义数据文件 |
| `--output` | `-o` | 自动 | 输出路径（扩展名 `.png` / `.html` 可覆盖格式） |
| `--format` | `-f` | `png` | 输出格式：`png` / `html` / `both` |
| `--scale` | `-s` | `2` | PNG 清晰度倍率（2≈高清，3≈超清，范围 0.5–6） |
| `--info` | — | — | 仅输出数据文件摘要 |

### 示例

```bash
# 查看数据摘要
python ".cursor/skills/dlt-analysis/scripts/trend_chart.py" --info

# 最新 50 期 PNG（默认）
python ".cursor/skills/dlt-analysis/scripts/trend_chart.py"

# 26067 期往前 50 期 PNG
python ".cursor/skills/dlt-analysis/scripts/trend_chart.py" -i 26067 -n 50

# 同时输出 PNG + HTML
python ".cursor/skills/dlt-analysis/scripts/trend_chart.py" -i 26067 -n 50 -f both
```

### 输出

- 默认目录：`~/Desktop/lotto-charts/`
- 默认文件名：`trend-{期号}-n{实际期数}.png`
- stdout 打印 JSON 摘要（含 `outputs` 路径列表）

---

## 程序二：统计分析（冷热号 / 和值 / 区间）

### 功能

在指定窗口内输出结构化统计，供 Agent 快速定位冷热号与结构偏差，**可配合程序三使用**（统计先行 → 看图验证）：

- 前区/后区热号 Top 榜、冷号 Bottom 榜
- 超期冷号（前区遗漏 ≥ 12、后区遗漏 ≥ 10）
- 和值 min/max/avg、三区间累计、奇偶比、大小比
- 最新一期开奖号码

### 执行方式

```bash
python ".cursor/skills/dlt-analysis/scripts/stats_report.py" [选项]
```

### 参数

| 参数 | 简写 | 默认 | 说明 |
|------|------|------|------|
| `--issue` | `-i` | 最新期 | 基准期号 |
| `--count` | `-n` | `50` | 统计窗口期数 |
| `--data` | `-d` | skill 内置 JSON | 自定义数据文件 |
| `--json` | — | — | 仅输出 JSON（无中文报告正文） |

### 示例

```bash
# 默认 50 期统计（中文报告 + JSON）
python ".cursor/skills/dlt-analysis/scripts/stats_report.py"

# 仅 JSON，供程序化处理
python ".cursor/skills/dlt-analysis/scripts/stats_report.py" -n 50 --json
```

### 触发词

- "冷热号分析 / 统计走势 / 遗漏分析 / 和值分布 / 超期冷号"

---

---

## 程序三：局部趋势图（近 15 期 · 第二分析角度）

### 功能

聚焦**最近 15 期**短窗口，自动识别并绘制局部运动轨迹（对应参考图中绿色箭头逻辑）：

- **↘ / ↙ 斜向趋势线**：相邻行间步长一致的 ≥3 期连线
- **↓ 纵向热柱**：同号码在短窗内反复出现
- **汇聚枢纽**：多条趋势线虚线延长落在同一号码
- **虚线延长落点**：外推下一期候选列
- 底部「预测」行标注延长目标

与 50 期全局图互补：全局看「欠账/均衡」，局部看「动势/方向」。

### 执行方式

```bash
python ".cursor/skills/dlt-analysis/scripts/local_trend_chart.py" [选项]
```

### 参数

| 参数 | 简写 | 默认 | 说明 |
|------|------|------|------|
| `--issue` | `-i` | 最新期 | 基准期号 |
| `--count` | `-n` | **`15`** | 局部窗口期数 |
| `--data` | `-d` | skill 内置 JSON | 自定义数据文件 |
| `--output` | `-o` | 自动 | PNG 输出路径 |
| `--scale` | `-s` | `2` | PNG 倍率 |
| `--no-chart` | — | — | 仅文字/JSON，不生成 PNG |
| `--json` | — | — | 仅输出 JSON |

### 示例

```bash
# 默认近 15 期局部趋势图 + 分析报告
python ".cursor/skills/dlt-analysis/scripts/local_trend_chart.py"

# 指定期号、20 期窗口
python ".cursor/skills/dlt-analysis/scripts/local_trend_chart.py" -i 26067 -n 20

# 仅 JSON 分析
python ".cursor/skills/dlt-analysis/scripts/local_trend_chart.py" --json --no-chart
```

### 输出

- 默认 PNG：`~/Desktop/lotto-charts/local-trend-{期号}-n15.png`
- stdout：中文趋势报告 + JSON（含 `chains` / `convergence_hubs` / `next_candidates`）

### 触发词

- "局部趋势 / 15 期趋势 / 近15期分析 / 连线趋势 / 局部走势 / 绿色趋势线"

### 方法论

详见 [references/LOCAL_TREND_ANALYSIS.md](references/LOCAL_TREND_ANALYSIS.md)。

### 推荐组合工作流

```
local_trend_chart.py（15 期动势）
  + stats_report.py（50 期冷热）
  → 取「局部落点 ∩ 全局冷号」交集加权定号
  → 程序四：对落点做 ±N 偏差带扩展（勿只押纯落点）
```

---

## 程序四：偏差值（趋势落点 ±N · 第四分析角度）

### 核心观点

**纯趋势线延长落点的精确命中率约 20%**（球级）。多数实际开奖会在趋势方向上产生 **1–N 列的偏移**。因此：

- 趋势（程序三）回答「往哪走」
- 偏差（程序四）回答「偏几格、扩展多宽」

偏差量**不能拍脑袋**，须通过 `deviation_backtest.py` 对历史大量滚动验证，结果写入 `assets/deviation_profile.json`，随样本扩大持续更新。

### 执行方式

```bash
# 回测最近 300 期并更新偏差档案
python ".cursor/skills/dlt-analysis/scripts/deviation_backtest.py"

# 扩大样本（推荐定期执行）
python ".cursor/skills/dlt-analysis/scripts/deviation_backtest.py" -t 800

# 回测 + 当前期偏差带预览
python ".cursor/skills/dlt-analysis/scripts/deviation_backtest.py" --preview-adjust
```

### 参数

| 参数 | 简写 | 默认 | 说明 |
|------|------|------|------|
| `--window` | `-n` | `15` | 局部趋势窗口 |
| `--test-issues` | `-t` | `300` | 回测最近 N 期 |
| `--save` | — | `assets/deviation_profile.json` | 档案输出路径 |
| `--preview-adjust` | — | — | 用新档案预览当前期扩展候选 |
| `--json` | — | — | 仅 JSON |

### 档案产出

`assets/deviation_profile.json` 含：

- `front.exact_hit_rate` — 纯落点精确率（验证 ~20% 假设）
- `front.band_hit_rate` — ±0…±7 命中率曲线
- `front.recommended_band` — 推荐扩展列数 N（≥80% 覆盖）
- `front.signed_histogram` — 左偏/右偏分布

`local_trend_chart.py` 会自动读取档案，在报告中输出**偏差带扩展候选**。

### 触发词

- "偏差值 / 趋势偏差 / 落点偏移 / 偏差带 / 回测趋势 / 验证命中率"

### 方法论

详见 [references/DEVIATION_VALUE.md](references/DEVIATION_VALUE.md)。

### 验证迭代（持续进行）

| 阶段 | 动作 |
|------|------|
| 初版 | 300 期回测，建立 baseline |
| 加深 | 800 → 全量期回测，观察 N 是否收敛 |
| 细分 | 分链型 / 分窗口 / 分前后期对比偏差 |
| 应用 | 预测时**禁止只押纯落点**，必须 ±N 扩展 |

---

## 程序五：空区分析（三分区空区 · 第五分析角度）

### 概念

**空区** = 单期内一段**连续号码完全未开出**（参考图中的绿色横条）。两种定义：

- **最宽空号段**（绿框）：单期最长连续空号区间，几乎总存在 → 描述「缺口在哪」
- **严格三等分区空**：01-12 / 13-24 / 25-35 某整区 0 球 → 用于「排除整区」

### ⚠️ 回测验证结论（诚实数据 · 800 期）

直觉是「空区每 N 期规律出现且可预测，能大幅排除号码」。**回测修正了这一假设**：

| 指标 | 实测 |
|------|------|
| 任一区有空区的期占比 | ~37%（多数期三区都有球） |
| 各区边际空区率 | 01-12 ~10.5% / 13-24 ~10.9% / **25-35 ~16%** |
| `due`(越久没空越该空)命中率 | ~10.6% **↓ 低于随机，已弃用** |
| 修正法(结构性偏冷区)命中率 | ~12.5%（≈基线） |
| 押 2 个最冷区命中率 | ~25.8%（覆盖宽） |

**结论**：严格整区为空是 ~10-16%/区 的**弱事件**，动态预测难超随机基线。本模块作**描述 + 结构性弱信号**用，**不做高确定性整区排除**（强排除会高频误杀）。

### 执行方式

```bash
# 近 30 期空区分析 + 绿框 PNG + 下期预测
python ".cursor/skills/dlt-analysis/scripts/empty_zone.py" -n 30

# 回测空区预测命中率（验证假设）
python ".cursor/skills/dlt-analysis/scripts/empty_zone.py" --backtest -t 800

# 仅 JSON
python ".cursor/skills/dlt-analysis/scripts/empty_zone.py" --json --no-chart
```

### 参数

| 参数 | 简写 | 默认 | 说明 |
|------|------|------|------|
| `--count` | `-n` | `30` | 窗口期数 |
| `--min-run` | — | `6` | 空区最小连续空号数 |
| `--backtest` | — | — | 回测预测命中率 |
| `--test-issues` | `-t` | `500` | 回测期数 |
| `--no-chart` / `--json` | — | — | 控制输出 |

### 正确用法（弱信号）

```
不要因"预测空区"就把一整区完全排除（整区全空仅 ~13%，会误杀）
→ 偏向最热活跃区多分配号码，对结构性偏冷区适度收敛号数
```

### 触发词

- "空区 / 空挡 / 空区分析 / 哪个区会空 / 排除区间 / 分区冷热"

### 方法论

详见 [references/EMPTY_ZONE_ANALYSIS.md](references/EMPTY_ZONE_ANALYSIS.md)。

---

## 程序六：全局趋势线预测（50 期 · 视觉分析）

### 原理

每期号码随机产生，但每个号码出现概率相等，长期趋向**均态分布**；短期偏离后会**向均值回归**。以 50 期走势图为标准窗口，用**模型的视觉能力**观察图中的趋势线（连线），捕捉「偏离 → 回归」的运动方向，预测下一期号码。

> ⚠️ 本程序**必须调用视觉能力读取走势图 PNG**，禁止不看图、仅凭 JSON 数字臆测。彩票随机，预测仅供娱乐参考。

### 强制工作流

```
① （推荐）运行 stats_report.py 获取冷热号/超期号数字摘要
   ↓
② 用程序一生成基准期往前 50 期走势图 PNG（默认 -n 50 -s 2）
   ↓
③ 读取该 PNG（Read 工具）→ 用视觉能力观察
   ↓
④ 严格按 references/trend-line-prediction.md 的「五步观察协议」逐步分析：
   A 总览带状 → B 纵向冷热 → C 斜向趋势线(连线) → D 区间均衡 → E 形态辅助
   （每步先用文字描述图上实际所见，再下结论；与 stats 数字交叉验证）
   ↓
⑤ 综合定号：**固定输出 前区 7 码 + 后区 3 码（7+3）**（每号须有观察理由）
   ↓
⑥ 按模板输出预测，并附随机性 / 娱乐声明
```

详细方法论见 [references/trend-line-prediction.md](references/trend-line-prediction.md)，执行预测前**必读**。

### 触发词

- "预测下一期 / 预测大乐透 / 趋势线预测 / 帮我分析走势 / 看图预测 / 下期出什么"

### 关键约束（摘要）

- 50 期窗口基准期望：前区单号约 7 期出一次（遗漏 > 12 为超期冷号）；后区约 6 期一次。
- 趋势线至少串联 **3 期及以上**的球才算有效，优先连最近 8–12 期。
- 冷号回补与热号延续要平衡，核心号不可全冷或全热。
- 结构校验：三区间不空区、大小/奇偶不极端、和值落 70–110。

---

## Agent 工作流速查

| 用户意图 | 执行脚本 |
|----------|----------|
| 看走势图（50 期） | `trend_chart.py` |
| 冷热号 / 和值 / 遗漏 | `stats_report.py` |
| **局部趋势（15 期）** | `local_trend_chart.py` |
| **偏差值回测 / 档案更新** | `deviation_backtest.py` |
| **空区分析 / 分区冷热** | **`empty_zone.py`** |
| 全局预测下一期 | `stats_report.py` → `trend_chart.py` → Read PNG → 按 reference 输出 |
| **完整组合预测** | `local_trend_chart.py` + `deviation_backtest` 档案 + `empty_zone.py` + `stats_report.py` |
| **评测方法是否跑赢随机** | `harness.py --periods 300 --format both`（L1 算法盲测） |
| **看图法盲测（子 agent · 严格单期）** | `harness_visual.py prepare → next（逐期）→ record → validate → score`（见 [references/VISUAL_HARNESS.md](references/VISUAL_HARNESS.md)） |
| **L2 看图 + L1 融合修正** | `refine-l1` → `score --fuse-l1`（见 VISUAL_HARNESS.md） |
| 更新数据 | 覆盖 `assets/lotto_history.json` → `--info` 验证 |

## 脚本清单

| 脚本 | 职责 |
|------|------|
| `scripts/dlt_data.py` | 数据加载、校验、遗漏/窗口/统计/局部趋势/偏差/空区算法 |
| `scripts/trend_chart.py` | 基本走势图 PNG/HTML（50 期） |
| `scripts/stats_report.py` | 冷热号与和值统计报告 |
| `scripts/local_trend_chart.py` | 局部趋势图 PNG + 15 期连线分析 |
| `scripts/deviation_backtest.py` | 偏差值回测 + deviation_profile.json |
| `scripts/empty_zone.py` | **空区分析 PNG（绿框）+ 三分区周期 + 回测** |
| `scripts/harness.py` | **L1 预测评测（算法盲测 walk-forward）** |
| `scripts/harness_visual.py` | **L2 预测评测（子 agent 看图盲测 · prepare/next/record/validate/score · 默认 strict）** |
| `scripts/harness_visual_batch.py` | L2 辅助（默认单期 limit=1；batch 需 `--unsafe-allow-batch`） |
| `scripts/harness_fusion.py` | L2+L1 融合定号（L2 锚定 + L1 有限替换修正） |
| `scripts/harness_common.py` | harness 共用计分与格式校验 |
| `assets/deviation_profile.json` | 偏差档案（回测产出，预测时读取） |

## 扩展规划（待实现）

- [ ] 后区独立走势图
- [ ] 号码组合过滤与选号辅助
- [ ] 分链型 / 分窗口偏差细分回测
- [ ] 全量 2800+ 期偏差收敛报告

新增程序时保持：`scripts/{功能名}.py` + 在本 SKILL.md 登记。
