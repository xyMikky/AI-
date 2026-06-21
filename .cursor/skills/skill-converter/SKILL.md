---
name: skill-converter
description: Cursor/Claude Agent Skills 的「全生命周期管理」助手——既负责"从零创建"（将项目能力、工作流程转换为标准 SKILL.md），也负责"维护已有 Skill"（为现有 Skill 添加 references 参考资料、scripts 脚本、templates 模板、assets 资源，整理 Skill 文件结构，归档外部资料到 Skill 文件夹内，调整文件命名规范）。**只做**：① 创建新 Skill（模式 A/B/C 信息完整度评估 + 三档模板）② 优化已有 Skill 的 description ③ 维护已有 Skill 的文件结构（模式 D：归档资料 / 调整目录 / 修正引用路径）。**不做**：Skill 的业务功能本身（→ 走对应业务 Skill）、AI 角色创建（→ 走 ai-persona-architect）、系统健康诊断（→ 走 logic-chain-diagnostic）。适用场景：创建新 skill、规范化能力描述、标准化工作流程、为已有 skill 加入资料库、整理 skill 文件夹结构、把桌面 / 外部资料归档进 skill、修正 skill 中错误的文件引用路径、批量创建 skill 库。关键词：Skill 转换、能力标准化、YAML 生成、工作流程、Agent Skills、Cursor Skills、维护已有 skill、添加 references、添加 scripts、添加 templates、归档资料、skill 文件结构、skill 自包含、整理 skill、resource 归档、加入到 skill、skill 资料库。
---

# Skill 转换助手

## 概述

这个 Skill 帮助用户将项目能力、工作流程或专业知识转换为符合 Cursor/Claude Agent Skills 标准的 SKILL.md 文件。通过智能评估输入信息完整度、精准追问补充缺失内容、优化 description 描述，确保生成的 Skill 文件能被 AI Agent 准确识别和使用。

## 使用场景

- **创建新技能**：将项目中的自定义能力转换为标准 Skill 文件
- **规范化已有能力**：将散落的文档、脚本整理为标准格式
- **优化 description**：改进现有 Skill 的描述，提升 Agent 识别准确度
- **维护已有 Skill 文件结构**（模式 D）：为已存在的 Skill 添加 references / scripts / templates / assets，归档外部资料到 Skill 文件夹，修正引用路径
- **学习 Skill 规范**：通过实际转换过程理解 Agent Skills 标准
- **批量创建技能**：系统化地将多个能力转换为 Skill 库

## 模式总览

| 模式 | 触发场景 | 核心动作 | 走哪条流程 |
|---|---|---|---|
| **创建模式** | 用户提出新能力，期望从零生成 Skill | 信息评估 → 类型判断 → 生成 SKILL.md | 步骤 1-7 |
| **优化模式** | 用户提供已有 Skill 的 description 让改进 | description 诊断 + 重写 | 步骤 4 单独使用 |
| **D 维护模式** | 用户说"加入资料到 XX skill / 整理 XX skill 的文件结构 / 归档外部资料" | 必读 STRUCTURE.md → 归档资料 → 更新引用 → 自检 | **跳过步骤 1-5，走「模式 D 专属流程」** |

⚠️ **关键路由**：识别到 D 维护模式时，**不要走信息完整度评估 / 类型判断 / 生成模板**——这些是创建模式的步骤。维护模式有自己的独立 6 步流程，见下文。

## 工作流程

### 步骤 1：接收与评估

接收用户提供的能力描述后，立即进行信息完整度评估。

**评分标准**（满分 100）：

```python
score = 0
score += 20 if has_clear_name else 0        # 能力名称明确
score += 30 if has_function_desc else 0     # 功能描述清晰
score += 25 if has_use_cases else 0         # 使用场景具体
score += 25 if has_workflow else 0          # 工作流程详细
```

**评估要素**：

- ✅ 能力名称（如"PDF处理"、"代码审查"）
- ✅ 核心功能（做什么）
- ✅ 使用场景（什么时候用）
- ✅ 目标用户（谁会用）
- ✅ 输入输出（数据流）
- ✅ 工作流程（怎么做）

**判断规则**：

- **≥ 80分**：信息充足 → 直接进入生成模式
- **50-79分**：信息不足 → 引导补充模式（3-5个精准追问）
- **< 50分**：信息严重不足 → 结构化探索模式（分阶段引导）

### 步骤 2：信息补全（评分 < 80 时）

⚠️ **强制先判断 Skill 类型，再按类型走不同的追问清单**。不要对所有 Skill 都问同一组通用问题。

#### 2.1 类型判断（必须先做）

使用 `AskQuestion` 让用户在三类之间选择：

| 类型 | 特征 | 典型例子 |
|---|---|---|
| **A. 工具脚本类**（Tool） | 接收明确输入 → 产生明确输出，可被其他 Skill 调用 | PDF 合并、CSV 解析、API 调用封装、图片格式转换 |
| **B. 业务流程类**（Workflow） | 多步骤、有用户交互、有上下游依赖、可能含分支决策 | 详情页设计流程、需求引导、竞品分析 |
| **C. 系统配置类**（System） | 不直接产出业务结果，而是改变系统行为或元数据 | 系统巡检、注册表更新、规则评审、配置同步 |

#### 2.2 按类型走差异化追问

**A. 工具脚本类追问清单**（关注 I/O 和依赖）：

1. **输入**：需要哪些参数？（文件路径 / URL / 字符串 / 结构化对象？是否支持多个？）
2. **输出**：产物形式？（文件 / JSON / 控制台打印 / 修改原文件）
3. **外部依赖**：依赖什么命令行工具、Python 包、API、网络？
4. **错误场景**：输入缺失 / 格式错误 / 网络失败 时如何处理？（报错 / 静默 / 降级）
5. **副作用**：是否会写入文件、调用付费 API、修改系统状态？

**B. 业务流程类追问清单**（关注上下游和分支）：

1. **触发场景**：用户用什么话 / 在什么阶段会激活这个 Skill？
2. **上下游**：执行前需要哪些前置 Skill 产物？执行后下游 Skill 如何接力？
3. **核心步骤**：大致几个阶段？每个阶段产出什么（交接卡 / 报告 / 文件）？
4. **分支与异常**：哪些情况会进入迭代回路？哪些情况会终止流程？
5. **与现有 Skill 的边界**：做什么 / 不做什么（明确说出"不做 X（→ 走 Y Skill）"）？

**C. 系统配置类追问清单**（关注作用域和回滚）：

1. **作用范围**：扫描 / 修改哪些目录或文件？是只读还是会写入？
2. **触发频率**：用户主动触发 / 周期性 / 事件驱动？
3. **幂等性**：重复执行多次结果是否一致？
4. **回滚机制**：如果改坏了，如何撤销？
5. **影响面**：对其他 Skill / Rule / 用户工作流有什么连带影响？

#### 2.3 追问原则

- 一次只问该类型必需的 3-5 题，不要把三类问题全列出
- 优先用 `AskQuestion` 选项卡形式，选项里必须含"其他（自定义）"兜底
- 用户回答简略时主动补全合理默认值，不要二次追问轰炸
- 仍然遵守：举例说明、避免术语、用通俗语言

### 步骤 3：结构化转换

将收集到的信息映射到 Skill 标准结构。

**信息映射表**：

| 用户输入 | Skill 要素 | 输出位置 |
|---------|-----------|---------|
| 能力名称 | `name` | YAML Front Matter |
| 功能描述 + 场景 + 关键词 | `description` | YAML Front Matter |
| 核心目的 | 概述 | 正文第一段 |
| 使用场景（具体例子） | 使用场景 | 正文列表 |
| 工作流程（步骤） | 工作流程 | 正文分步骤说明 |
| 输入输出 | 使用方法 | 正文包含输入要求和输出格式 |
| 特殊要求 | 注意事项 | 正文列出约束条件 |

**Name 格式规则**：

```python
# 转换规则
"PDF处理" → "pdf-handler"
"API代码解析" → "api-code-parser"
"并发任务管理" → "concurrent-task-manager"

# 格式要求
- 全小写
- 使用连字符（-）分隔单词
- 不含特殊字符
- 简洁且有辨识度
```

### 步骤 4：Description 优化

Description 是 Agent 识别使用场景的**唯一依据**，必须精雕细琢。

**优秀 Description 的必备要素**：

1. **核心功能**（动词 + 名词）：
   - ✅ "从 Python 代码中提取 API 配置"
   - ❌ "处理代码"

2. **适用范围**（支持什么）：
   - ✅ "支持 PDF/Word/Excel 格式"
   - ❌ "处理文档"

3. **触发场景**（何时使用）：
   - ✅ "适用于快速配置 API 参数、从文档复制示例代码的场景"
   - ❌ "当需要时使用"

4. **关键词列表**（帮助匹配）：
   - ✅ "关键词：代码解析、API配置、参数提取、模板生成"
   - ❌ 无关键词

**Description 模板**：

```markdown
[核心功能描述]。[适用范围说明]。适用于[使用场景1]、[使用场景2]、[使用场景3]的场景。关键词：[词1]、[词2]、[词3]、[词4]。
```

**反例避免**：

- ❌ 过于简短："处理文件"（缺少细节）
- ❌ 过于泛化："帮助用户完成任务"（太宽泛）
- ❌ 缺少场景："数据分析工具"（不知道何时用）
- ❌ 无关键词："一个很有用的功能"（无法匹配）

**长度要求（按 Skill 类型分档）**：

| Skill 类型 | 推荐字数（中文）| 说明 |
|---|---|---|
| 工具脚本类 | 150-300 字 | 输入输出明确，描述可较紧凑 |
| 业务流程类 | 300-600 字 | 必须容纳"做什么 / 不做什么（→ 别的 Skill） / 触发关键词"三段 |
| 系统配置类 | 200-400 字 | 重点写作用范围、触发条件、影响面 |

⚠️ **关键认知**：description 是 Agent 决定是否激活 Skill 的唯一依据。过短（< 150 字）的 description 普遍会让 Agent 错过该 Skill 的适用场景；过长（> 800 字）则稀释关键词权重。**绝大多数 Skill 不应少于 200 字**——把 50 字当上限是常见误区。

### 步骤 5：生成 SKILL.md 内容

根据步骤 2.1 判定的 Skill 类型，**选择对应深度的模板**生成内容。不要把所有 9 个 section 都当作必需——简单的工具 Skill 强行套全模板会显得冗余，复杂的业务 Skill 套通用模板又会丢失关键架构。

#### 三档模板选择

| 类型 | 必需 section | 可选 section | 整体长度 |
|---|---|---|---|
| **A. 工具脚本类** | 概述、调用方式、参数说明、返回值/产物 | 错误处理、示例、依赖说明 | 短（80-200 行） |
| **B. 业务流程类** | 概述、定位与边界、工作流程（分步）、上下游对接、输入/输出契约 | 示例、注意事项、与其他 Skill 协同、迭代回路 | 长（300-800 行） |
| **C. 系统配置类** | 概述、作用范围、执行方式、输出报告格式、回滚机制 | 影响面、定时建议 | 中（150-400 行） |

#### A 档模板（工具脚本类）

```markdown
---
name: [skill-name]
description: [核心功能 + 输入输出 + 触发场景 + 关键词]，150-300 字。
---

# [能力标题]

## 概述
[一句话说明：输入什么、输出什么、谁会调用]

## 调用方式

### 命令行
```bash
python xxx.py --param value
```

### 被其他 Skill 调用
[说明常被哪些业务 Skill 调用，传入什么参数]

## 参数说明
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|---|---|---|---|---|

## 返回值 / 产物
[文件路径 / JSON 结构 / stdout 格式]

## 错误处理
[输入缺失、网络失败、依赖缺失 时的行为]
```

#### B 档模板（业务流程类）

```markdown
---
name: [skill-name]
description: [核心定位] —— [核心功能]。**只做 X**，**不做 Y（→ 走 Z Skill）**。适用于：[场景 1]、[场景 2]、[场景 3]。关键词：[6-10 个]。
---

# [能力标题]

## 定位与边界

| 维度 | 内容 |
|---|---|
| 做什么 | … |
| 不做什么 | … （→ 走 XX Skill） |
| 上游依赖 | … |
| 下游对接 | … |

## 触发条件
- 关键词：…
- 场景：…
- 不触发：…

## 工作流程

### 阶段 1：[名称]
[输入 / 处理 / 输出]

### 阶段 2：…

### 阶段 3：…

## 输入 / 输出契约
- 输入：…
- 输出（交接卡 / 报告 / 文件）：…

## 与其他 Skill 协同
[列出常见协同链路与触发条件]

## 注意事项 / 迭代回路
…
```

#### C 档模板（系统配置类）

```markdown
---
name: [skill-name]
description: [作用域] + [核心动作] + [典型触发场景]，200-400 字。关键词：…。
---

# [能力标题]

## 概述
[扫描/修改的范围、读写性质、谁会触发]

## 作用范围
- 目录：…
- 文件类型：…
- 是否写入：是 / 否

## 执行方式
[命令 / 用户触发词 / 周期]

## 输出报告格式
[结构化报告样例]

## 回滚机制
[若改坏了如何撤销]

## 影响面
[对其他 Skill / Rule / 用户工作流的连带影响]
```

#### 输出前自检

无论选哪一档，生成后须人工再过一遍：
- 必需 section 是否齐全？
- 可选 section 是否真的有内容可写？没有就删掉，不要留空壳
- description 长度是否符合该档区间？（A: 150-300，B: 300-600，C: 200-400）

### 步骤 6：创建文件

#### 6.1 命名冲突预检（强制前置，禁止跳过）

⚠️ **创建前必须先做重名检查**。否则可能静默覆盖已有 Skill，或因目录已存在而崩溃。

1. 使用 `Glob` 列出现有所有 Skill 目录：
   ```
   .cursor/skills/*/SKILL.md
   ```
2. 提取所有现有 `name` 字段值，与本次拟用 name 做精确匹配 + 模糊近似匹配（含 Levenshtein 距离 ≤ 2 的近名警告）。
3. 命中处理：

| 情况 | 处理方式 |
|---|---|
| 完全重名（同 name） | 用 `AskQuestion` 让用户三选一：**A 覆盖现有 Skill** / **B 重命名为 [建议名]** / **C 中止创建** |
| 近似重名（如 `pdf-merge` vs `pdf-merger`） | 警告用户并展示已存在的近名 Skill 的 description，让用户确认是否仍要新建 |
| 触发关键词冲突（与现有 Skill 关键词重叠 ≥ 3 个） | 警告并询问是否调整本次关键词 / 合并到现有 Skill |
| 完全无冲突 | 直接进入 6.2 |

4. **未经用户明确确认，不得覆盖**。

#### 6.2 实际创建

**Windows + 中文路径环境（如本项目 `f:\AI设计师助手\`）**：直接用 `Write` 工具创建文件，路径用相对路径 `.cursor/skills/[skill-name]/SKILL.md`，避免 `subprocess` + 中文路径的编码坑。

**通用环境（Unix / 跨平台脚本场景）**：可调用 `scripts/create_skill.py`：

```bash
python .cursor/skills/skill-converter/scripts/create_skill.py \
  --json '{"name": "my-skill", "content": "..."}'
```

**脚本功能**：
- 验证 skill_name 格式（小写-连字符）
- 创建 `.cursor/skills/[skill-name]/` 目录
- 写入 `SKILL.md` 文件
- 返回 JSON 格式结果

⚠️ 调用脚本前确认目标目录不存在或用户已明确同意覆盖（见 6.1）。

### 步骤 7：质量检查与说明

生成完成后，向用户说明如何使用和验证。

**质量检查清单**：

- ✅ YAML Front Matter 格式正确
- ✅ description 长度落在对应档区间内（A: 150-300 / B: 300-600 / C: 200-400 字）
- ✅ description 含"做什么 / 不做什么（→ 别的 Skill） / 触发关键词"三段（B 档强制）
- ✅ 必需 section 齐全（按 A/B/C 档清单核对）
- ✅ 可选 section 没有空壳留白
- ✅ 包含至少 1 个完整示例
- ✅ 无模糊表述（"尽量"、"可能"、"也许"）

**用户说明模板**：

```markdown
✅ Skill 文件已创建成功！

📁 文件位置：`.cursor/skills/[skill-name]/SKILL.md`

🔍 如何验证：
1. 打开 Cursor Settings（Mac: Cmd+Shift+J，Win/Linux: Ctrl+Shift+J）
2. 导航到 **Rules**
3. 在 **Agent Decides** 部分查看新技能

💡 使用方法：
- 向 Agent 描述相关任务，Agent 会自动识别并使用这个 Skill
- 或直接在提示中提及："使用 [skill-name] 处理..."

📝 下一步优化：
- [建议1]
- [建议2]
```

## 模式 D：已有 Skill 维护流程（强制独立流程）

### 适用范围

凡满足以下任一条件，**立即进入模式 D 流程，不走创建模式步骤 1-7**：

- 用户说"把 XX 资料加入到 [skill-name] skill 中"
- 用户说"为 [skill-name] 添加 references / 脚本 / 模板 / assets"
- 用户说"整理 [skill-name] 的文件结构 / 归档资料 / 修正引用"
- 用户提供外部资料文件路径（桌面 / 用户目录），要求归档到某个 Skill

### 强制约束

本模式由全局 Rule `.cursor/rules/skill-file-structure.mdc`（alwaysApply）兜底约束。本流程是 Rule 的具体落地步骤。

### D 模式 6 步流程

#### D-1：必读 STRUCTURE.md

**第一步动作**（不可省略）：

```
Read: .cursor/skills/skill-converter/references/STRUCTURE.md
```

确认目录命名规范、文件命名规范、子目录用途。

#### D-2：识别目标 Skill + 输出任务摘要

输出 1 行任务识别摘要：

```
[Skill 维护任务] 目标：[skill-name] · 操作：[添加 references / 添加 scripts / 整理结构 / 修正引用] · 已读 STRUCTURE.md：✅
```

确认目标 Skill 存在：

```
Glob: .cursor/skills/[skill-name]/SKILL.md
```

不存在 → 改走「创建模式」（步骤 1-7）。

#### D-3：分类资料并路由到子目录

按 STRUCTURE.md 的资料类型路由表分类：

| 资料类型 | 路由到 | 命名规范 |
|---|---|---|
| 知识文档 / 写作指南 / 案例集 / 参考资料 | `references/` | `UPPER_SNAKE_CASE.md` |
| Python / Shell / JS 脚本 | `scripts/` | `lower_snake_case.py` |
| 配置模板 / 输出模板 / 报告模板 | `templates/` | `lower_snake_case_template.{md,json,html}` |
| JSON Schema / 图片 / 数据文件 | `assets/` | `lower_snake_case.{json,png,csv}` |

类型不清晰 → 用 `AskQuestion` 让用户在四类之间选择，附"其他（自定义）"兜底。

#### D-4：归档执行

**子目录不存在则创建，原文件复制进 Skill 文件夹**。

Windows + 中文路径环境：

```powershell
$skill = "g:\AI设计师助手\.cursor\skills\[skill-name]"
$refDir = [System.IO.Path]::Combine($skill, "references")
[System.IO.Directory]::CreateDirectory($refDir) | Out-Null
[System.IO.File]::Copy($source, [System.IO.Path]::Combine($refDir, "新文件名.md"), $true)
```

⚠️ 必须用 `[System.IO.File]::Copy()` / `[System.IO.Directory]::CreateDirectory()`（详见 `ai-designer-assistant.mdc` 中文路径技术约束）。

如果归档前用户把资料先平铺到了 Skill 根目录（如本次教训），同步把根目录的错放文件删除：

```powershell
$wrong = [System.IO.Path]::Combine($skill, "错放的文件名.txt")
if ([System.IO.File]::Exists($wrong)) { [System.IO.File]::Delete($wrong) }
```

#### D-5：更新 SKILL.md 引用

用 `StrReplace` 把 `SKILL.md` 中对该资料的所有引用改为 **Skill 内相对路径**：

- ✅ `references/MASTER_SHOTS_CAMERA_BLOCKING.md`
- ❌ `c:\Users\Administrator\Desktop\...`（外部绝对路径）
- ❌ `大师100镜头调度.txt`（根目录平铺）
- ❌ `../../其他skill/references/...`（跨 Skill 引用）

如果 `SKILL.md` 还没有引用该资料，应在合适章节（如"参考资料"、"知识库"、"工作流程"中相关步骤）追加引用句。

#### D-6：自检 + 输出归档清单

执行：

```
Glob: .cursor/skills/[skill-name]/**/*
ReadLints: .cursor/skills/[skill-name]/SKILL.md
```

输出归档完成确认：

```
✅ Skill 维护完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 目标 Skill：[skill-name]
• 归档资料：
  - 源文件：[原始路径]
  - 目标位置：.cursor/skills/[skill-name]/[references/scripts/templates/assets]/[规范文件名]
• SKILL.md 引用更新：✅ 已改为相对路径
• 根目录清理：✅ 无平铺残留
• Lint 检查：✅ 无报错
• 当前 Skill 目录结构：
  .cursor/skills/[skill-name]/
  ├── SKILL.md
  ├── references/
  │   └── [新归档文件]
  └── ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### D 模式常见错误（必须主动规避）

| 错误 | 后果 | 正确做法 |
|---|---|---|
| 直接修改 `SKILL.md` 文本，不动文件 | Skill 引用外部路径，不自包含 | 先 D-4 归档再 D-5 改引用 |
| 把资料平铺到 Skill 根目录 | 违反 STRUCTURE.md | 按 D-3 路由到 `references/` 等子目录 |
| 用错误命名规范（如 `references/` 下用小写文件名） | 违反命名约定 | 按 D-3 表格的命名规范 |
| 跳过 D-1 不读 STRUCTURE.md，凭印象操作 | 大概率出错 | D-1 是硬性第一步 |
| D-4 用 `Copy-Item` 处理中文路径 | 编码失败 / 文件丢失 | 用 `[System.IO.File]::Copy()` |
| D-6 不自检直接收尾 | 错误不可见 | 必须 `Glob` + `ReadLints` |

## 使用方法

### 基础用法：转换单个能力

**输入**（信息充足）：

```markdown
我想创建一个 Skill，用于从日志文件中提取错误信息。

功能：解析应用日志，提取 ERROR 和 CRITICAL 级别的错误，生成结构化报告。
支持格式：.log、.txt
使用场景：
- 快速诊断生产环境问题
- 生成错误统计报告
- 集成到 CI/CD 自动检查

工作流程：
1. 读取日志文件
2. 正则匹配 ERROR/CRITICAL 行
3. 提取时间戳、模块名、错误信息
4. 生成 JSON/Markdown 报告
```

**输出**：

```markdown
✅ 信息完整度评分：95/100

正在生成 Skill...

📁 已创建：`.cursor/skills/log-error-extractor/SKILL.md`

[展示生成的文件内容]

🔍 验证方法：
打开 Cursor Settings > Rules > Agent Decides 查看

💡 使用示例：
"分析 app.log 中的错误信息"
```

### 进阶用法：信息不足时的引导

**输入**（信息不足）：

```markdown
我想创建一个处理图片的 Skill
```

**输出**（引导追问）：

```markdown
## 📋 信息补充

我已理解您要转换的能力大致是：一个图片处理相关的功能

信息完整度评分：30/100

为了生成高质量的 SKILL.md，请补充以下信息：

1. **核心目的**：这个能力主要用来解决什么问题？
   - 选项：图片格式转换 / 图片压缩 / 图片识别 / 其他

2. **使用场景**：在什么情况下会用到它？（举1-2个具体例子）
   - 例如："当需要批量转换图片格式时" 或 "分析图片中的文字内容"

3. **工作流程**：大致分几个步骤完成任务？
   - 例如："1. 读取图片 2. 调整尺寸 3. 保存结果"

4. **输入输出**：需要什么输入？产出什么结果？
   - 输入：图片文件路径 / URL / base64？
   - 输出：处理后的图片 / JSON数据 / 文本？

5. **特殊要求**：是否有特定的格式、工具或约束？
   - 例如：支持的图片格式、是否需要外部依赖、性能要求等

您可以简要回答，我会据此生成专业的 Skill 文件。
```

### 高级用法：批量转换

```python
# 准备多个能力描述
skills_to_convert = [
    {"name": "pdf-merger", "description": "..."},
    {"name": "csv-analyzer", "description": "..."},
    {"name": "email-sender", "description": "..."}
]

# 依次转换
for skill_input in skills_to_convert:
    # 调用 Skill 转换流程
    convert_to_skill(skill_input)
```

## 示例

### 示例 1：完整转换流程

**输入**：

```markdown
我想创建一个 Skill，用于自动生成 Git 提交信息。

功能：分析 git diff，理解代码变更，生成符合 Conventional Commits 规范的提交信息。
使用场景：
- 提交代码时自动生成描述
- 统一团队提交信息风格
- 快速总结代码变更

工作流程：
1. 执行 git diff 获取变更
2. 识别变更类型（feat/fix/docs/refactor）
3. 提取关键变更内容
4. 生成格式化提交信息
5. 可选：交互式确认

输入：git diff 输出
输出：Conventional Commits 格式的提交信息

特殊要求：
- 支持中英文
- 可配置提交信息模板
- 支持多文件变更
```

**输出**：

```markdown
✅ 信息完整度评分：100/100

正在生成 Skill 文件...

---
name: git-commit-generator
description: 分析 git diff 自动生成符合 Conventional Commits 规范的提交信息。支持识别变更类型（feat/fix/docs/refactor）、提取关键内容、格式化输出。适用于提交代码时自动生成描述、统一团队提交风格、快速总结代码变更的场景。关键词：Git、提交信息、Conventional Commits、自动生成、代码分析、变更总结。
---

# Git 提交信息生成器

## 概述

这个 Skill 通过分析 git diff 输出，自动理解代码变更内容，生成符合 Conventional Commits 规范的提交信息，帮助开发者快速创建高质量、格式统一的提交记录。

[... 完整内容 ...]

✅ 文件已创建：`.cursor/skills/git-commit-generator/SKILL.md`

🔍 验证方法：
1. 打开 Cursor Settings（Ctrl+Shift+J）
2. 导航到 Rules > Agent Decides
3. 查看 "git-commit-generator" 技能

💡 使用示例：
"分析当前的代码变更，生成提交信息"
"根据 git diff 创建符合规范的 commit message"
```

### 示例 2：优化现有 Description

**输入**：

```markdown
我有一个 Skill 的 description 需要优化：
"处理文件的工具"

实际功能：批量重命名文件，支持正则替换、序号添加、大小写转换
```

**输出**：

```markdown
📝 Description 优化建议

**原始版本**（不推荐）：
"处理文件的工具"

问题：
- ❌ 过于简短（仅6字）
- ❌ 过于泛化（"处理"太宽泛）
- ❌ 缺少使用场景
- ❌ 无关键词

**优化版本**（推荐）：
"批量重命名文件工具，支持正则表达式替换、序号自动添加、大小写转换。适用于批量整理文件名、统一命名规范、添加序号前缀的场景。关键词：文件重命名、批量处理、正则替换、序号、大小写转换、文件管理。"

改进点：
✅ 明确核心功能（批量重命名）
✅ 列出支持的操作（正则/序号/大小写）
✅ 说明使用场景（3个具体场景）
✅ 包含关键词（6个相关词）
✅ 长度适中（96字）

💡 更新方法：
修改 `.cursor/skills/[skill-name]/SKILL.md` 的 YAML Front Matter
```

## 注意事项

### 1. 信息完整度优先

- 评分 < 80 时，**必须追问**，不要臆测或补充信息
- 宁可多问一句，也不生成低质量文件
- 追问要精准（3-5个问题），避免问题轰炸

### 2. Description 是识别关键

- Description 是 Agent 识别使用场景的**唯一依据**
- 必须包含：功能 + 范围 + 场景 + 关键词；业务流程类还须含"做什么 / 不做什么（→ 走 Y Skill）"边界
- 长度按 Skill 类型分档（A: 150-300 / B: 300-600 / C: 200-400 字），过短（< 150）会让 Agent 错过适用场景
- 避免模糊词汇（"尽量"、"可能"、"也许"）

### 3. 文件位置固定

- **必须输出到** `.cursor/skills/[skill-name]/SKILL.md`
- 文件名**必须是** `SKILL.md`（全大写）
- 文件夹名使用小写字母和连字符
- 不要输出到其他位置（如 `skill/` 或根目录）

### 4. 格式严格要求

- YAML Front Matter 必须用三短横线包裹
- YAML 中冒号后必须有空格
- Markdown 正文使用标准格式
- 代码块必须指定语言

### 5. 质量保证

生成前自动检查：
- ✅ YAML 格式符合标准
- ✅ description 长度落在对应档区间（A: 150-300 / B: 300-600 / C: 200-400 字）
- ✅ B 档 description 含"做什么 / 不做什么（→ 别的 Skill） / 触发关键词"
- ✅ 必需 section 齐全（按所选档清单核对）
- ✅ 包含至少 1 个完整示例
- ✅ 无模糊表述

### 6. 版本要求

- 需要 **Cursor Nightly 版本** 或更高版本
- Agent Skills 功能在正式版中可能不可用
- 验证方法：Settings > Rules 中应该有 "Agent Decides" 部分

## 文件结构

本 Skill 采用标准文件结构：

```
skill-converter/
├── SKILL.md              # 主文件（本文件）
├── scripts/              # 辅助脚本
│   └── create_skill.py   # 创建 Skill 目录和文件
├── references/           # 参考文档
│   ├── STRUCTURE.md      # 标准文件结构说明
│   └── EXAMPLES.md       # 完整示例
└── templates/            # 模板文件
    └── skill_template.md # SKILL.md 标准模板
```

### scripts/create_skill.py

创建 Skill 目录和文件的 Python 脚本。

**功能**：
- 验证 skill 名称格式（小写-连字符）
- 验证 SKILL.md 内容格式（YAML + Markdown）
- 创建标准目录结构（SKILL.md + 可选的 scripts/references/templates/assets/）
- 返回 JSON 格式结果

**调用方式**：
```bash
# 方式 1：仅创建基础文件
python scripts/create_skill.py --name my-skill --content "..."

# 方式 2：JSON 输入（Agent 使用）
python scripts/create_skill.py --json '{"name": "my-skill", "content": "..."}'

# 方式 3：创建完整目录结构
python scripts/create_skill.py --name my-skill --file template.md --full-structure
```

### references/

参考文档目录，包含：
- **STRUCTURE.md**：标准 Skill 文件结构规范
- **EXAMPLES.md**：各种场景的完整示例

### templates/

模板文件目录，包含：
- **skill_template.md**：标准 SKILL.md 模板

## 故障排除

### 问题 1：生成的 Skill 在 Cursor 中不可见

**原因**：文件位置或名称不正确

**解决**：
1. 检查文件是否在 `.cursor/skills/[skill-name]/SKILL.md`
2. 确认文件名是 `SKILL.md`（全大写）
3. 重启 Cursor（有时需要重新加载）

### 问题 2：Agent 无法识别使用场景

**原因**：description 不够详细或缺少关键词

**解决**：
1. 检查 description 是否包含使用场景
2. 添加更多关键词
3. 描述要具体，避免泛化表述

### 问题 3：create_skill.py 执行失败

**原因**：Python 环境问题或参数错误

**解决**：
```bash
# 检查 Python 版本
python --version  # 需要 Python 3.7+

# 检查脚本权限
chmod +x .cursor/skills/skill-converter/scripts/create_skill.py

# 查看详细错误
python .cursor/skills/skill-converter/scripts/create_skill.py --name test --content "test" -v
```

### 问题 4：YAML 解析错误

**原因**：YAML 格式不正确

**常见错误**：
```yaml
# ❌ 错误：冒号后无空格
name:skill-converter

# ✅ 正确：冒号后有空格
name: skill-converter

# ❌ 错误：description 包含未转义的冒号
description: 处理文件: 支持多种格式

# ✅ 正确：使用引号包裹
description: "处理文件: 支持多种格式"
```

