# AI 设计师助手 · Design Agent Hub

> 一个基于 **Cursor + Claude/GPT + Skill 架构** 构建的、可在本地运行的"设计智能体调控中心"。
> 核心理念：**调控中心 + 专家团队**——主控中心负责识别任务和路由，27 个 Skill 专家分别负责品牌、配色、排版、UI、详情页、AI 生图、视频、竞品分析等垂直能力。
> 当前版本：**V8.0**（Skill 化全量重构版）

---

## 一、这个项目能做什么

它不是一个"全能美工"，而是把日常设计工作流——从需求引导、品牌规范、配色排版、AI 生图、详情页拼装、竞品分析，一直到失败案例反思——拆解为 **27 个可复用的 Skill**，串联成一条**带阶段门、带评分、带数据闭环**的工业化流水线。

主要使用场景：

1. **AI 静态生图**：海报 / Banner / 电商主图 / 模特场景图 / 换背景 / 换装 / 风格转换
2. **AI 视频提示词**：可灵 / Kling / TikTok / 抖音带货分镜 + 口播
3. **详情页 / Amazon A+**：HERO + M2-M7 多模块批量并发生图
4. **品牌从零创建**：Logo / 配色 / 字体 / VI / 应用规范
5. **品牌已有素材学习**：扫描 `品牌规范/[品牌]/00_待学习/`，自动提取色彩/字体/Logo/影像/版式/语气/禁忌
6. **竞品分析**：单 SKU 拆解（套图 + A+ + 视频封面 + 六维评分）+ 多 SKU 横向对比沉淀
7. **设计提案 / 评审**：提案文档、Figma/印刷物料评审、PPT 大纲
8. **个人审美学习**：把日常喜欢/讨厌的图片放入 `参考库/00_待学习/`，引擎自动分类、写入档案、归档原图、更新向量索引
9. **系统自我维护**：可视化关系图谱、12 维健康诊断、AI 角色架构、能力转 Skill

---

## 二、整体架构（V8.0）

### 2.1 三层结构

```
                        ┌────────────────────┐
                        │   主控中心 V8.0     │  ← 任务识别 / 路由 / 阶段门
                        └─────────┬──────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ 业务层 18 Skill   │    │ 工具层 9 Skill    │    │ 强约束 14 Rules   │
│ (M1-M18 → Skill) │    │ (生图/分析/资产)  │    │ (流程/卫生/反馈)  │
└─────────┬────────┘    └─────────┬────────┘    └─────────┬────────┘
          └────────────────────────┼────────────────────────┘
                                   ▼
                  ┌──────────────────────────────────┐
                  │       三轴 + 一库 知识体系        │
                  │  品牌规范 > 场景知识库 > 参考库    │
                  │  + 向量检索系统（787 条切片）      │
                  └──────────────────────────────────┘
```

### 2.2 业务层 Skill · 18 个

| 旧编号 | Skill 名 | 角色 |
|---|---|---|
| M1 | `brand-logo-designer` | 从零创建品牌 VI/Logo |
| M2 | `color-system-designer` | 配色系统（独立 / Step 0 双模式）|
| M3 | `typography-designer` | 排版字体（独立 / Step 0 双模式）|
| M4 | `ui-ux-designer` | UI/APP/Web 界面 |
| M5 | `print-poster-designer` | 印刷物料（独立 / Step 0 双模式）|
| M6 | `non-ai-design-reviewer` | 非 AI 稿评审 |
| M7 | `design-proposal-writer` | 提案与汇报 |
| **M8** | **`ai-image-prompt-builder`** | **AI 静态生图唯一入口** |
| M9 | `ai-image-aesthetic-scorer` | AI 生图审美评分（9 维 + 双轴）|
| M10 | `reference-library-learner` | 参考库素材学习引擎 |
| M11 | `market-platform-analyzer` | 市场 / 平台 / 受众分析 |
| M12 | `design-relation-visualizer` | 交互式 HTML 关系图谱 |
| **M13** | **`design-requirement-guide`** | **强制前置需求引导**（Plan 模式）|
| M14 | `video-prompt-designer` | 视频 / 分镜 / 口播 |
| M15 | `detail-page-designer` | 详情页（中国 / 欧美双市场）|
| **M16** | **`ai-image-logic-checker`** | **生图前后强制门**（Pre-Gen 12 项 + Post-Gen 9 项 + 5 维评分）|
| M17 | `brand-spec-learner` | 品牌素材学习引擎 |
| M18 | `logic-chain-diagnostic` | 系统健康度 12 维只读诊断 |

### 2.3 工具层 Skill · 9 个

| Skill 名 | 角色 |
|---|---|
| `rh-image-pro-img2img` | RunningHub 图生图 API 调用 |
| `rh-image-pro-txt2img` | RunningHub 文生图 API 调用 |
| `nano-banana-prompt-guide` | Nano Banana / Gemini 写作知识库 |
| `layout-reference-analyzer` | 多模块版式参考图分析 |
| `brand-asset-sheet` | 品牌资产合成图（Logo + 字体 + 色卡）|
| `color-palette-generator` | 色卡 PNG 渲染 |
| `ai-persona-architect` | AI 角色架构师（创建 / 优化模块）|
| `skill-converter` | 能力描述转标准 SKILL.md |
| `amazon-image-extractor` / `amazon-competitor-analyzer` / `amazon-competitor-comparison-synthesizer` | Amazon 单 SKU 抓取 / 单品分析 / 多 SKU 横向对比 |

### 2.4 强约束 Rules · 14 条（位于 `.cursor/rules/`）

**全局执行规则**（所有任务自动应用）：

- `ai-designer-assistant.mdc` —— 默认中文输出、中文路径用 .NET IO、V7.9→V8.0 兼容映射
- `design-must-use-main-control.mdc` —— 所有设计任务必须先经主控中心
- `mandatory-requirement-guidance.mdc` —— 强制前置需求引导
- `skill-file-structure.mdc` —— Skill 文件结构强制规范（写入 / 移动 / 改名前必读 STRUCTURE.md）
- `image-logic-check.mdc` —— Pre-Gen 12 项 + Post-Gen 9 项 + 5 维评分（自动激活）
- `prompt-hygiene-no-internal-ids.mdc` —— Prompt 卫生四铁律（禁内部标识 / 禁 IMAGE ROLES 目录块 / 禁文字重命名图中已有视觉属性 / 优先正向表述）
- `ref-image-must-include.mdc` —— 参考图必须实际引用 + 5 Phase 流程
- `batch-image-concurrent.mdc` —— 组图任务必须用 Shell 后台并发（禁 Task 子代理）
- `vector-search-integration.mdc` —— 向量检索 Vector-First 集成
- `color-palette-authority.mdc` —— 色卡角色隔离 + 产品色独立性
- `user-color-preferences.mdc` —— 默认白底 + 明亮基调
- `p-domain-save.mdc` —— 成功案例三轨入库（P 域 + 品牌设计案例 + 向量索引）
- `x-domain-save.mdc` —— 失败案例三轨入库（X 域 + 规则联动 + 向量索引）

**Skill 内部专属规范**（不属于全局 rule，仅在对应 Skill 调度时按需读取）：

- `video-prompt-designer/references/KLING_PROMPT_FORMAT.md` —— 可灵 / Kling 视频提示词规范（原全局 rule `kling-prompt-output-format.mdc`，V8.x 起按 Skill 自包含原则迁入）

---

## 三、目录结构

```
AI设计师助手/
├── 主控中心.txt                           ← V8.0 调度中枢
├── README.md                              ← 本文件
├── .gitignore                             ← 敏感配置和大产物的忽略规则
├── AI设计师助手_架构图.html               ← 架构可视化
├── AI设计师助手_知识图谱架构_V7.2.html    ← 知识图谱可视化
├── AI自动化产品拍摄流程展示.html          ← 产品拍摄流程演示
│
├── .cursor/                               ← Cursor 智能体配置
│   ├── rules/                             ← 14 条强约束 Rule (.mdc)
│   └── skills/                            ← 27 个 Skill 目录（每个含 SKILL.md + 资源）
│
├── 参考库/                                ← 个人审美 + 通识原则 + 案例库
│   ├── 参考库主控助手.txt
│   ├── 参考索引.txt                       ← 一站式导航
│   ├── 使用说明.txt
│   ├── 00_待学习/                         ← 投入新素材的入口
│   ├── 00_通识原则/                       ← P1-P7 跨域底层逻辑 + 设计 DNA
│   ├── A_品牌与Logo/  B_配色系统/  C_排版字体/  D_UI界面/
│   ├── E_平面与海报/  F_摄影风格/  G_插画与图形/  H_3D与渲染/
│   ├── I_动效与视频/  J_空间与产品/  L_口播文案库/  N_详情页设计/
│   ├── V_视频脚本库/  Z_禁忌案例/
│   ├── 人物库/                            ← 已学习的模特身份参考图
│   ├── 场景库/                            ← 已学习的场景环境参考图
│   ├── P_生图成功案例库/                  ← 成功案例 + 完整 Prompt（可复用）
│   └── X_生图失败案例库/                  ← 失败案例 + 根因分析（反面教材）
│
├── 品牌规范/                              ← 多品牌硬约束（最高优先级）
│   ├── 品牌规范主控.txt
│   ├── _品牌目录模板/                     ← 新建品牌时复制此模板
│   └── NEBILITY/                          ← 已注册品牌示例
│       ├── 00_待学习/
│       ├── 品牌档案.txt                   ← always-load 核心档案 (<3KB)
│       ├── 品牌索引.txt
│       ├── 视觉系统/                      ← 7 个结构化规范文件
│       │   ├── 色彩系统.txt   字体系统.txt   Logo系统.txt
│       │   ├── 影像风格.txt   版式规范.txt   品牌语气.txt   禁忌清单.txt
│       │   └── 模特动作规范.txt（NEBILITY 扩展）
│       ├── 设计案例/
│       └── 原始素材/
│
├── 场景知识库/                            ← 场景正确性约束
│   ├── 场景知识库主控.txt
│   ├── K1_地域市场/                       ← 不同文化圈的审美差异
│   ├── K2_电商与平台/                     ← 平台规范、转化要素
│   ├── K3_受众画像/                       ← 受众视觉偏好
│   └── K4_内容类型/                       ← 不同内容形式的设计目标
│
├── 工具/                                  ← 跨 skill 共享基础设施（仅放被多方共用、无法归属单一 skill 的工具）
│   └── 向量检索/                          ← 787 条切片的语义检索系统（被多个 skill + 规则 + 主控中心共用）
│       ├── chunking.py    scan_archives.py    embedder.py
│       ├── reranker.py    build_index.py      update_index.py
│       ├── query_rewriter.py    search.py
│       ├── vector_index/                  ← 索引产物（已 .gitignore）
│       └── README.md
│
├── config/                                ← API Key 配置
│   ├── .env.example                       ← 配置模板
│   ├── .env                               ← 真实 Key（已 .gitignore）
│   └── runninghub-error-codes.md
│
├── 输入图片/                              ← 用户提供的原始素材
├── 生成结果输出/                          ← AI 生图结果（已 .gitignore *.png/*.jpg）
│   ├── prompts/                           ← 每次生图的完整 Prompt 留档
│   └── amazon图片提取/                    ← Amazon 抓取产物
└── 归档/                                  ← 历史版本快照（v7.9 等）
```

---

## 四、第一次使用：环境准备

### 4.1 系统依赖

- **OS**：Windows 10+（PowerShell 7+），macOS / Linux 也可（路径分隔符自适应）
- **Python**：3.10+
- **Cursor IDE**：用于读取 `.cursor/rules/` 和 `.cursor/skills/`，并由 Claude/GPT 模型担任主控中心

### 4.2 Python 依赖安装

```powershell
# 向量检索系统
pip install numpy pandas pyarrow requests python-dotenv

# Amazon 竞品分析
pip install -r .cursor/skills/amazon-image-extractor/scripts/requirements.txt
```

### 4.3 配置 API Key

```powershell
# 复制模板
Copy-Item config\.env.example config\.env

# 编辑 config\.env，填入：
# - RH_API_KEY        （RunningHub 生图，必填）
# - SILICONFLOW_API_KEY（向量检索 + Rerank，必填）
```

获取 Key：
- [RunningHub](https://www.runninghub.cn/) → 控制台 → API 管理
- [SiliconFlow](https://siliconflow.cn/) → API 密钥

### 4.4 首次构建向量索引（可选但强烈推荐）

```powershell
# 先扫描看规模和成本（不调 API）
python 工具/向量检索/scan_archives.py

# 全量构建（首次约 7 分钟 / ¥0.4 左右）
python 工具/向量检索/build_index.py --force

# 之后每次入库后用增量更新（典型 < ¥0.005 / 5-15 秒）
python 工具/向量检索/update_index.py
```

向量索引让主控中心在生成【参考精炼摘要 B】、P 域案例复用、品牌条款抽取时拥有**语义召回**能力，而不是线性阅读整个子文件。

---

## 五、上手：5 个最常用的工作流

### 工作流 ① · AI 海报 / Banner / 电商主图

直接对 AI 说：

> "帮我设计一张 NEBILITY 男士塑身背心的促销 Banner，主打 BOGO 优惠，9:16 尺寸"

主控中心会自动走完：

```
① 调控中心决策块（识别任务 + 路由 + 协同声明）
② design-requirement-guide（Plan 模式 Q&A 选项卡）
③ 品牌约束加载（NEBILITY 视觉系统）
④ market-platform-analyzer（如声明场景）→ 卡 A
⑤ M2/M3/M5 Step 0 协同 → 卡 D / E / F
⑥ ai-image-prompt-builder
   ├─ 参考精炼摘要 B（向量检索召回）
   ├─ 姿势设计七要素 + 场景互动
   ├─ 人物库 / 场景库优先调用
   ├─ 色卡门 + 版式分析门
   └─ 品牌资产合成图
⑦ ai-image-logic-checker Pre-Gen 12 项门
⑧ rh-image-pro-img2img（Shell 后台并发）
⑨ ai-image-logic-checker Post-Gen V1-V9 + Q1-Q5 评分
⑩ ai-image-aesthetic-scorer 双轴评分 → 通过 / 迭代
```

最终图片自动落到 `生成结果输出/`，对应 Prompt 落到 `生成结果输出/prompts/`。

### 工作流 ② · 详情页（Amazon A+ / 中国宝贝详情）

> "帮我做一份这个产品的 Amazon A+ 详情页，9 个模块"

`detail-page-designer` 接管，生成 HERO + M2-M9 模块结构，调用 `ai-image-prompt-builder` 批量并发生图，单批 ≤ 5 张避免 API 限流。

### 工作流 ③ · Amazon 竞品分析

> "分析这 3 个竞品：[3 个 Amazon URL]"

```
amazon-image-extractor      → 抓取套图 / A+ / 视频封面 / 元数据
   ↓
amazon-competitor-analyzer  → 每个 SKU 出三件套（md + visual.json + html）
   ↓ 强制 AskQuestion 三选一
   ↓
amazon-competitor-comparison-synthesizer  → 多 SKU 横向对比沉淀
```

### 工作流 ④ · 学习一张参考图

把图片丢进 `参考库/00_待学习/`，对 AI 说：

> "开始学习"

`reference-library-learner` 自动：
- 判断领域（A-Z 域）
- 按域分析（不同维度框架）
- 写入对应子文件
- 归档原图到 `[域]/原始素材/`
- 更新三层索引
- **增量更新向量索引**（让下次检索能命中）

### 工作流 ⑤ · 学习一个新品牌

```powershell
# 1. 从模板复制
Copy-Item -Recurse 品牌规范\_品牌目录模板 品牌规范\新品牌名

# 2. 把品牌素材（Logo / VI 手册 / 设计案例）放进
#    品牌规范\新品牌名\00_待学习\

# 3. 对 AI 说：
"学习品牌 新品牌名"
```

`brand-spec-learner` 自动解析图片 / PDF / 文本 / 字体，写入视觉系统 7 个文件，更新品牌注册表。

---

## 六、数据闭环：成功案例 + 失败案例

V8.0 的核心创新之一是 **P/X 双案例库 + 三轨入库**——让模型在失败和成功中都能进化。

### P 域（成功案例）

触发词：`保存这次生成` / `存入案例库` / `P 域入库`

```
轨道 A：在 参考库/P_生图成功案例库/ 创建 P-XXX 文件夹
        含 prompt.txt（完整原文）+ meta.txt + 所有参考图 + result.jpg
轨道 B：如品牌激活，复制到 品牌规范/[品牌]/设计案例/
轨道 C：python 工具/向量检索/update_index.py（让下次能检索到）
```

下次同类任务时，主控中心通过 `search.py --type P_CASE` **语义召回该案例的 prompt.txt** 作为起点。

### X 域（失败案例）

触发词：`失败入库` / `这张翻车了` / `X 域入库`，
或自动提示：M16 Post-Gen 加权总分 < 40 时主动询问

```
轨道 A：在 参考库/X_生图失败案例库/ 创建 X-XXX 文件夹
        含完整失败 Prompt + 根因分析（对照 X1-X7 分类）+ 改进建议
轨道 B：严重案例（🔴）联动更新对应 Rule 的"常见陷阱案例库"
轨道 C：增量更新向量索引
```

下次同类任务前，主控中心自动执行 **X 域反向查询**，把历史教训作为 `[陷阱规避清单]` 写入新 Prompt。

---

## 七、Cursor Rules 速读（开发者向）

如果你修改了规则或新增 Skill，需要理解 14 条 `.mdc` 之间的关系：

| 类型 | Rule | 关键约束 |
|---|---|---|
| **流程入口** | `design-must-use-main-control` | 设计任务必先经主控中心 |
| **流程入口** | `mandatory-requirement-guidance` | 强制前置 design-requirement-guide |
| **质检阶段门** | `image-logic-check` | Pre-Gen 12 项 + Post-Gen 9 项 + 5 维评分 |
| **Prompt 卫生** | `prompt-hygiene-no-internal-ids` | 4 铁律：禁内部标识 / 禁目录块 / 禁文字重命名 / 优先正向 |
| **Prompt 卫生** | `ref-image-must-include` | image N 必须显式引用 + 5 Phase |
| **Prompt 卫生** | `color-palette-authority` | 色卡角色隔离 + 产品色独立 |
| **Prompt 卫生** | `user-color-preferences` | 默认白底 + 明亮基调 |
| **执行优化** | `batch-image-concurrent` | 组图必须 Shell 后台并发 |
| **执行优化** | `vector-search-integration` | Vector-First 召回 |
| **数据闭环** | `p-domain-save` | 成功案例三轨入库 |
| **数据闭环** | `x-domain-save` | 失败案例三轨入库 |
| **全局基础** | `ai-designer-assistant` | 中文输出、中文路径 .NET IO |

> ⚠️ **PowerShell 中文路径必须用 .NET IO**：`Get-ChildItem` 在含中文路径下会返回空，所有文件操作改用 `[System.IO.Directory]::GetFiles(...)` / `[System.IO.File]::Copy(...)`。

---

## 八、关键设计决策（FAQ）

**Q1：为什么主控中心瘦身到 ~280 行？**
V8.0 把所有模块的"内部流程细节"全部下沉到对应 Skill 的 `SKILL.md`。主控中心只负责**识别 + 路由 + 阶段门管控**，避免上下文爆炸。

**Q2：参考库 / 品牌规范 / 场景知识库的优先级？**
`品牌规范 > 场景知识库 > 参考库 > 通识原则`。品牌主色和场景正确性属于硬约束；参考库和通识原则属于偏好。

**Q3：业务 Skill 和工具 Skill 的区别？**
- **业务 Skill**：直接面向用户意图（"做一张海报"→ `print-poster-designer` 或 `ai-image-prompt-builder`）
- **工具 Skill**：被业务 Skill 内部调用（业务说"我需要色卡 PNG"→ 调 `color-palette-generator`）

**Q4：M2/M3/M5 双模式什么意思？**
- **独立模式**：用户主动说"配色方案 / 字体规范 / 印刷海报" → 走完整流程出完整文档
- **Step 0 协同模式**：被 AI 生图任务声明协同时 → 轻量产出【决策卡 D / E / F】喂给生图

**Q5：生图为什么不用 Task 子代理？**
RunningHub API 单次 60-600 秒，远超 Task 子代理 30 秒窗口。Task 超时后底层进程是否存活不可预测。**强制使用 Shell + `block_until_ms: 0` 后台化** + 终端文件轮询。

**Q6：默认输出语言？**
**中文**。但以下技术锚点必须保留原样：
`image N` 编号、HEX 色号、API 参数（`--aspect-ratio`）、文件路径、品牌名、`BACKGROUND ONLY` / `PRODUCT ONLY` 等硬约束词。
例外：可灵视频提示词遵循 `video-prompt-designer` Skill 的 `references/KLING_PROMPT_FORMAT.md` 独立规范。

---

## 九、扩展与维护

### 9.1 新增一个业务 Skill

1. 用 `skill-converter` 把能力描述标准化为 SKILL.md
2. 在 `.cursor/skills/[skill-name]/SKILL.md` 落地
3. 更新 `主控中心.txt` 第二节 Skill 注册表
4. 更新 `.cursor/rules/ai-designer-assistant.mdc` 路由表

### 9.2 新增一条 Rule

参考 Cursor 内置 `create-rule` Skill 的 SKILL.md（位于 `~/.cursor/skills-cursor/create-rule/`）。

### 9.3 系统健康检查

```
对 AI 说："检查系统"
```

`logic-chain-diagnostic` 自动巡检 12 维：
文件存在性 / 注册一致性 / 调用链路连通性 / 交叉引用完整性 / 索引同步等，输出健康度百分比报告。

### 9.4 可视化系统结构

```
对 AI 说："可视化设计关系"
```

`design-relation-visualizer` 生成 D3.js 力导向图（单文件 HTML），支持 7 项交互：单击三级高亮、双击聚焦、右键追问、搜索过滤、布局切换、画布缩放、清除高亮。

---

## 十、版本历史

- **V8.0**（当前）：18 个能力模块全面 Skill 化，主控中心从 1380 行瘦身到 ~280 行，新增 X 域失败案例库 + 三轨数据闭环，向量检索集成 Rerank 精排
- **V7.9**：M2/M3/M5 双模式触发矩阵版（已归档至 `归档/v7.9/`）
- **V7.7**：能力模块 / 场景知识库扩展加入向量索引
- **V7.2**：知识图谱架构成型（见 `AI设计师助手_知识图谱架构_V7.2.html`）

---

## 十一、贡献与反馈

这个项目是**单人工作流定制版**，不接受外部 PR。如果你 fork 后想自己用：

1. 替换 `品牌规范/NEBILITY/` 为你自己的品牌
2. 清空 `参考库/[各域]/` 中的喜爱记录，从你自己的素材重新学起
3. 删掉 `参考库/P_生图成功案例库/` 和 `X_生图失败案例库/` 中的历史案例
4. 重新 `python 工具/向量检索/build_index.py --force` 构建你的私人知识库

---

## 十二、许可

仅供个人学习与自用。所引用的第三方资源（参考图、品牌素材、参考案例）版权归原作者所有，请勿商用分发。
