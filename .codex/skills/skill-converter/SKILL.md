---
name: skill-converter
description: Codex Agent Skills 全生命周期维护助手。用于把项目能力、流程、脚本、资料沉淀为 Codex 规范的 Skill，或维护已有 Skill 的 SKILL.md、agents/openai.yaml、scripts、references、assets 结构。适用于创建新 skill、优化 description、迁移 Codex/Claude 旧 skill、归档外部资料、整理资源目录、修复引用路径、批量规范化 skill 库。只处理 Skill 的包装、结构、触发说明和资源组织，不替代具体业务 Skill。关键词：Skill 转换、Codex Skills、SKILL.md、agents/openai.yaml、description 优化、references、scripts、assets、资源归档、skill 迁移。
---

# Skill 转换助手

## 定位

本 Skill 用来创建、迁移、整理和维护 Codex Agent Skills。它负责把一项能力包装成可触发、可复用、可验证的 Skill 文件夹；不负责替代该能力本身的业务执行。

写新 Skill 或大改旧 Skill 时，先用 `skill-creator` 的当前规范校准；本 Skill 负责把规范落到本项目的 Skill 文件结构、迁移检查和资源归档动作里。

## Codex 规范底线

- `SKILL.md` 必须存在，YAML frontmatter 至少包含 `name` 和 `description`。除非用户明确要求兼容额外平台字段，否则不要添加其他 frontmatter 字段。
- `description` 是触发 Skill 的主要依据，必须写清楚“做什么、何时使用、输入/输出或适用范围、边界、关键词”。不要把触发条件只放在正文里。
- 正文只保留执行流程和资源导航，默认控制在 500 行以内；详细说明放入 `references/`，并从 `SKILL.md` 直接引用。
- 推荐创建 `agents/openai.yaml`，只写 `interface.display_name`、`interface.short_description`、`interface.default_prompt` 等已知字段；字符串统一加引号。
- 标准资源目录是 `scripts/`、`references/`、`assets/`。模板属于输出资源时放到 `assets/templates/`，不要新建顶层 `templates/`。
- 不创建无关文档，如 `README.md`、`CHANGELOG.md`、`INSTALLATION_GUIDE.md`。这些内容若对执行有用，合并进 `SKILL.md` 或 `references/`。
- 所有引用使用 Skill 内相对路径，例如 `references/STRUCTURE.md`、`assets/templates/skill_template.md`。

## 模式选择

| 模式 | 用户意图 | 主要动作 |
|---|---|---|
| A 新建 Skill | “创建/写一个 Skill” | 明确能力例子，规划资源，生成 `SKILL.md` 和可选 `agents/openai.yaml` |
| B 优化描述 | “优化 description / 触发不准” | 重写 frontmatter description，必要时同步 `agents/openai.yaml` |
| C 迁移旧 Skill | “Codex/Claude 规范转 Codex” | 替换平台路径和工具名，调整资源目录，清理旧验证说明 |
| D 维护资源 | “把资料/脚本加入某个 Skill” | 归档到 `references/`、`scripts/` 或 `assets/`，更新相对引用 |

识别到模式 C 或 D 时，跳过新建评分模板，直接读取目标 Skill 和 `references/STRUCTURE.md` 后操作。

## 新建流程

1. 明确目标能力
   - 问清名称、核心任务、典型用户话术、输入输出、成功标准、边界。
   - 信息已足够时直接推进；缺关键边界时最多问 3 个问题。
   - 在 Plan 模式且 `request_user_input` 可用时可用选项卡；否则用简短文字追问。

2. 规划资源
   - 可重复、易错、需要确定性的逻辑放入 `scripts/`。
   - 长篇规范、案例、API 说明、领域知识放入 `references/`。
   - 模板、图片、字体、示例数据、JSON schema 放入 `assets/`；输出模板放 `assets/templates/`。
   - 简单 Skill 只保留 `SKILL.md`，不要为了显得完整而造目录。

3. 生成结构
   - 目标路径优先使用用户指定位置。
   - 若当前工作区已有 `.codex/skills/`，默认放到 `.codex/skills/[skill-name]/`。
   - 否则默认放到 `$CODEX_HOME/skills`；未设置时用 `~/.codex/skills`。
   - 创建前检查同名目录、相近名称和关键词冲突；未获明确同意不要覆盖。

4. 写 `SKILL.md`
   - `name` 用小写字母、数字和连字符，最长 64 字符。
   - `description` 不套旧的 50-200 字硬限制；以触发准确为准，通常中文 120-500 字较稳。
   - 正文用命令式流程，少讲概念，多写“读什么、做什么、何时加载哪些资源、如何验证”。

5. 写 `agents/openai.yaml`
   - 只在能确定展示信息时创建。
   - `default_prompt` 必须显式提到 `$skill-name`。
   - 不编造图标、品牌色、依赖工具；用户提供或 Skill 自带资源时才写。

6. 验证
   - 若系统 `skill-creator/scripts/quick_validate.py` 可用，运行它检查目标 Skill。
   - 脚本型 Skill 必须实际运行代表性脚本。
   - 用 `rg` 搜索旧平台词和绝对路径：`Codex|Claude|\.codex|request_user_input|apply_patch|验证脚本|Glob|Write|Rules > Agent Decides`。

## Description 写法

优秀的 `description` 包含：

- 核心动作：动词 + 对象，例如“分析 Amazon 评论并提炼痛点”。
- 范围：支持哪些文件、平台、数据源、任务类型。
- 触发场景：用户会怎么说、什么时候该用。
- 边界：只做什么，不做什么；必要时指向其他 Skill。
- 关键词：中英文或行业常用说法，避免空泛词。

避免：

- “处理文件”“帮助用户完成任务”这类泛词。
- 把所有细节塞进正文而让 description 很短。
- 为了堆关键词写成不可读的长串。
- 继续沿用 Codex/Claude 专属词，除非是在迁移说明中引用旧状态。

## 迁移旧 Skill

迁移 Codex/Claude 旧 Skill 到 Codex 时按此清单执行：

1. 平台路径
   - `.codex/skills/` 改为 `.codex/skills/` 或用户指定的 Codex skill 根目录。
   - `.codex/rules/`、Codex Settings、Rules、Agent Decides 等验证说明删除或改成 Codex 当前可验证动作。

2. 工具名
   - `request_user_input` 改成 `request_user_input`（仅在可用模式）或普通简短追问。
   - `Write`、`apply_patch` 改成“使用 `apply_patch` 编辑文件”。
   - `Glob`、`验证脚本` 改成“用 `rg --files` / `rg` / 验证脚本检查”。

3. 目录结构
   - 顶层 `templates/` 迁到 `assets/templates/`。
   - 需要展示元数据时新增 `agents/openai.yaml`。
   - 参考资料留在 `references/`，可执行逻辑留在 `scripts/`。

4. 内容风格
   - 删除“Codex Nightly”“重启 Codex”等旧说明。
   - 删除版本历史、安装说明、README 式叙述。
   - 将长示例移入 `references/EXAMPLES.md`，主文件保留导航。

5. 自检
   - 搜索旧词残留。
   - 检查所有路径都能从 Skill 根目录解析。
   - 运行可用验证脚本。

## 维护资源

维护已有 Skill 时，第一步读取 `references/STRUCTURE.md`。然后：

1. 确认目标 Skill 存在：`.codex/skills/[skill-name]/SKILL.md` 或用户给定路径。
2. 判断资源类型：
   - 知识文档、规范、案例、API 说明：`references/`
   - Python、Shell、JS 等可执行脚本：`scripts/`
   - 模板、schema、图片、字体、示例数据：`assets/`
   - 输出模板：`assets/templates/`
3. 复制或移动资源前确认来源路径和目标路径；避免覆盖同名文件。
4. 更新 `SKILL.md` 中的资源引用为相对路径。
5. 搜索外部绝对路径和旧文件名残留。

## 可用资源

- `references/STRUCTURE.md`：Codex Skill 文件结构和命名规范。
- `references/EXAMPLES.md`：完整转换示例。只在需要示例时读取。
- `scripts/create_skill.py`：轻量创建脚本。优先用于已完成碰撞检查、且需要自动创建目录和写入 `SKILL.md` 的场景。
- `assets/templates/skill_template.md`：新建 Skill 的基础模板。

## 输出要求

完成后向用户说明：

- 创建或修改了哪些文件。
- 是否从 Codex/Claude 旧规范迁移到了 Codex 规范。
- 跑了哪些验证，结果如何。
- 是否还有无法自动确认的残留风险。
