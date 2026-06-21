# Codex Agent Skills 文件结构规范

## 标准结构

```text
my-skill/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   └── process_data.py
├── references/
│   └── API_DOCS.md
└── assets/
    ├── schema.json
    └── templates/
        └── report_template.md
```

只有 `SKILL.md` 是必需文件。`agents/`、`scripts/`、`references/`、`assets/` 都按需创建；空目录不要保留。

## SKILL.md

`SKILL.md` 由 YAML frontmatter 和 Markdown 正文组成。

```yaml
---
name: my-skill
description: 清楚说明这个 Skill 做什么、何时使用、适用范围、边界和关键词。
---
```

要求：

- `name` 使用小写字母、数字和连字符，目录名与 `name` 一致。
- `description` 是触发 Skill 的主要依据，必须包含使用场景和关键词。
- frontmatter 默认只写 `name` 和 `description`。
- 正文写执行流程、资源导航、验证方式；不要堆长篇背景。
- 接近 500 行时拆分到 `references/`。

## agents/openai.yaml

`agents/openai.yaml` 是推荐的 Codex UI 元数据，不参与核心触发判断。

```yaml
interface:
  display_name: "Skill Converter"
  short_description: "Create and maintain Codex skills"
  default_prompt: "Use $skill-converter to convert this workflow into a Codex skill."
```

要求：

- 所有字符串加引号。
- `default_prompt` 必须包含 `$skill-name`。
- 不编造图标、品牌色、外部依赖；有真实资源或用户提供时才写。

## scripts/

放可执行脚本，用于确定性强、重复率高或容易写错的操作。

命名：

- Python：`lower_snake_case.py`
- Shell：`lower_snake_case.sh`
- JavaScript：`lower_snake_case.js`

要求：

- 脚本必须能独立运行或有清楚参数说明。
- 新增或修改脚本后运行代表性测试。
- 不把大段脚本内联塞进 `SKILL.md`。

## references/

放需要按需读取的文档、规范、长示例、API 说明、领域知识。

命名：

- Markdown 参考文档可用 `UPPER_SNAKE_CASE.md`，便于区分资源文件。
- 文件超过 100 行时在开头提供简短目录。

要求：

- `SKILL.md` 必须直接说明何时读取哪个 reference。
- 避免多层引用链。
- 不把用户向说明、安装指南、变更历史作为无关文档塞进来。

## assets/

放输出会用到、但不一定需要载入上下文的资源。

常见类型：

- `assets/schema.json`
- `assets/example_data.csv`
- `assets/logo.png`
- `assets/templates/report_template.md`
- `assets/frontend-template/`

模板文件归入 `assets/templates/`，不要使用顶层 `templates/`。

## 命名规范

| 对象 | 规则 | 示例 |
|---|---|---|
| Skill 目录 | 小写 + 连字符 | `amazon-review-analyzer` |
| 主文件 | 固定大写 | `SKILL.md` |
| agents 配置 | 固定路径 | `agents/openai.yaml` |
| 脚本 | 小写 + 下划线 | `extract_reviews.py` |
| 参考文档 | 大写 + 下划线 | `API_DOCS.md` |
| assets 文件 | 小写 + 下划线 | `review_schema.json` |
| 输出模板 | `assets/templates/` | `assets/templates/report_template.md` |

## 不要包含

- 顶层 `templates/`
- `README.md`
- `CHANGELOG.md`
- `INSTALLATION_GUIDE.md`
- `.codex/` 路径
- Codex Settings / Rules / Agent Decides 验证说明
- 与执行无关的项目说明

## 创建检查清单

- [ ] 目录名与 frontmatter `name` 一致。
- [ ] `description` 写清触发场景和关键词。
- [ ] `SKILL.md` 正文短而可执行。
- [ ] 需要展示元数据时创建 `agents/openai.yaml`。
- [ ] 只创建必要资源目录。
- [ ] 模板在 `assets/templates/`。
- [ ] 所有引用是 Skill 内相对路径。
- [ ] 新增脚本已运行测试。
- [ ] `rg "Codex|Claude|\\.codex|request_user_input|apply_patch|验证脚本|Rules > Agent Decides"` 无不该存在的残留。
