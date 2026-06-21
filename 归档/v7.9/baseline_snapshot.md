# V7.9 基线快照

> 阶段 1 产出物
> 生成时间：2026-04-27 15:10:34
> 用途：阶段 5 回归测试对比基准

---

## 一、诊断快照（logic-chain-diagnostic）

| 指标 | 数值 |
|---|---|
| 系统健康度 | **95.4% · 优秀** |
| 通过项 | 186 |
| 警告项 | 8 |
| 失败项 | 1 |
| 总检查项 | 195 |

### 维度细分

| 维度 | 通过 | 警告 | 失败 |
|---|---|---|---|
| D1 核心文件 | 2 | 0 | 0 |
| D2 模块注册 | 18 | 0 | 0 |
| D3 规则文件 | 13 | 5 | 1 |
| D4 Skill 完整性 | 15 | 0 | 0 |
| D5 参考库 | 22 | 3 | 0 |
| D6 品牌规范 | 全通过 | 0 | 0 |
| D7 场景知识库 | 5 | 0 | 0 |
| D8 人物/场景库 | 9 | 0 | 0 |
| D9 主流程链路 | 13 | 0 | 0 |
| D10 交叉引用 | 16 | 0 | 0 |
| D11 触发词路由 | 18 | 0 | 0 |
| D12 原始素材归档 | 5 | 0 | 0 |

### 已知问题清单

**致命 1 项（D3）**
- `archive-naming-enforcement.mdc` 在诊断配置中注册，但实际不存在
- 处理：诊断配置修复任务，非业务问题，V8.0 可清理

**警告 8 项**
- D3 5 条 Rule 未注册（`color-palette-authority` / `user-color-preferences` / `vector-search-integration` / `x-domain-save` / `prompt-hygiene-no-internal-ids`）→ V8.0 阶段 4 重新注册
- D5 3 个域无索引（A/I/Z）→ 设计上不需要，可忽略

---

## 二、阶段 1 备份清单

| 文件类别 | 数量 | 归档位置 |
|---|---|---|
| 主控中心.txt | 1 | `归档/v7.9/主控中心.txt` |
| AS-AI角色架构师.txt | 1 | `归档/v7.9/AS-AI角色架构师.txt` |
| 能力模块（M1-M18） | 18 | `归档/v7.9/能力模块/` |
| Rules（.mdc） | 18 | `归档/v7.9/rules/` |
| 诊断报告 | 1 | `归档/v7.9/baseline_diagnostic.txt` |

---

## 三、E2E 测试用例清单（Dry-Run · 不真的发起生图调用）

阶段 5 时按以下用例对照 V7.9 与 V8.0 的"调度链路输出"：

### 用例 1：NEBILITY 男士塑身衣促销 Banner

**用户语义**："帮 NEBILITY 做一张男士塑身背心的 BOGO 促销 Banner"

**V7.9 期望调度链路**：
```
M13 Express 引导 → M11 场景分析 → M2/M3/M5 Step 0 协同 →
M8 Prompt 构造 → M16 Pre-Gen → 生图 API → M16 Post-Gen → M9 评估
```

**V8.0 期望调度链路**：
```
design-requirement-guide(Express) → market-platform-analyzer →
color-system-designer(Step0) + typography-designer(Step0) + print-poster-designer(Step0) →
ai-image-prompt-builder → ai-image-logic-checker(Pre) → 生图 →
ai-image-logic-checker(Post) → ai-image-aesthetic-scorer
```

**回归对比检查点**：
- 阶段门触发数量是否一致
- 协同卡 D/E/F 是否齐全
- M16 Pre-Gen L0-L12 检查项是否完整
- P 域复用查询是否触发

### 用例 2：NEBILITY 详情页 Hero + 5 模块

**用户语义**："设计一份 Amazon 美国站的 NEBILITY 男士塑身衣详情页，HERO + 5 个模块"

**V8.0 期望调度链路**：
```
design-requirement-guide(Standard) → market-platform-analyzer(K1美国+K2 Amazon+K4详情页) →
detail-page-designer → ai-image-prompt-builder(批量) →
batch-image-concurrent 规则触发 → ai-image-logic-checker × 6 → ai-image-aesthetic-scorer
```

### 用例 3：P 域案例复用

**用户语义**："基于 P-001 改一版冬季限定的 BOGO Banner"

**V8.0 期望调度链路**：
```
design-requirement-guide(Express) → P域复用查询(向量检索 --type P_CASE) →
读取 P-001/prompt.txt → ai-image-prompt-builder(基于 P-001 改写) →
ai-image-logic-checker → 生图 → ai-image-aesthetic-scorer
```

### 用例 4：参考素材学习

**用户语义**："开始学习"（00_待学习/ 中放有 5 张图）

**V8.0 期望调度链路**：
```
reference-library-learner(M13 豁免) →
Phase 0.5 预细分清理 → Phase 1 列文件 → Phase 2 分析 →
Phase 3 写入子文件(同步细分) → Phase 4 归档原始素材 →
Phase 5 同步索引 → 向量增量更新
```

### 用例 5：系统诊断触发

**用户语义**："检查系统"

**V8.0 期望调度链路**：
```
logic-chain-diagnostic(M13 豁免) →
执行 D1-D12 → 输出健康度报告
```

---

## 四、边界测试用例清单

| 边界 | 触发语 | 期望行为 |
|---|---|---|
| M13 豁免 | "跳过引导，直接帮我换背景为白色" | design-requirement-guide 不触发，直接进入 ai-image-prompt-builder |
| M2 双模式仲裁 - 独立 | "帮我做一套品牌配色方案" | color-system-designer 独立模式，产规范文档 |
| M2 双模式仲裁 - 协同 | "帮我做一张海报" | color-system-designer Step 0 模式，产卡 D |
| X 域反向查询 | M16 评分 < 40 时 | 主动输出【X 域入库建议】 |
| 向量检索召回 | 任一生图任务 | search.py --type P_CASE 调用 |
| M16 自动激活 | 用户主动说"逻辑检查这张图" | 不应触发，告知用户 M16 仅自动激活 |

---

## 五、回归对比模板

阶段 5 完成测试后，按以下表格对比：

| 指标 | V7.9 基线 | V8.0 实测 | 是否回归 |
|---|---|---|---|
| 系统健康度 | 95.4% | ? | 应 ≥ 95% |
| 通过项数 | 186 | ? | 应 ≥ 200（含新 Skill） |
| 失败项数 | 1（已知） | ? | 应 = 0 |
| 主控中心行数 | 1380 | ? | 应 ~250 |
| Rules 数量 | 18 | ? | 应 ~12 |
| 业务 Skill 数 | 0 | ? | 应 = 18 |
| 总 Skill 数 | 9 | ? | 应 = 27 |
| 用例 1 链路完整度 | 完整 | ? | 应一致 |
| 用例 2 链路完整度 | 完整 | ? | 应一致 |
| 用例 3 链路完整度 | 完整 | ? | 应一致 |
| 用例 4 链路完整度 | 完整 | ? | 应一致 |
| 用例 5 链路完整度 | 完整 | ? | 应一致 |
