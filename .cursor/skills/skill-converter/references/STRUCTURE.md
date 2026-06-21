# Cursor Agent Skills 标准文件结构规范

## 概述

每个 Cursor Agent Skill 都应遵循统一的文件结构，以确保 Agent 能够正确识别和使用。

## 标准文件结构

```
my-skill/
├── SKILL.md              # 主文件（必需）
├── scripts/              # 可执行脚本（可选）
│   ├── process.py
│   └── validate.sh
├── references/           # 参考文档（可选）
│   ├── API_DOCS.md
│   └── EXAMPLES.md
├── templates/            # 模板文件（可选）
│   └── output_template.md
└── assets/               # 其他资源（可选）
    └── schema.json
```

## 目录说明

### SKILL.md（必需）

主文件，包含完整的技能描述和使用说明。

**必需内容**：
- YAML Front Matter（name + description）
- 概述
- 使用场景
- 工作流程
- 使用方法
- 示例
- 注意事项

**YAML Front Matter 格式**：
```yaml
---
name: skill-name
description: 详细描述，包含功能、范围、场景、关键词
---
```

### scripts/（可选）

存放可执行脚本，如 Python、Shell、Node.js 等。

**命名规范**：
- 使用小写字母和下划线
- 文件名应清晰表达功能
- 添加适当的文件扩展名

**常见用途**：
- 数据处理脚本
- 验证工具
- 转换工具
- API 调用封装

**示例**：
- `process_data.py` - 数据处理
- `validate_input.sh` - 输入验证
- `generate_report.js` - 报告生成

### references/（可选）

存放参考文档，如 API 文档、使用示例、技术说明等。

**命名规范**：
- 使用大写字母和下划线（Markdown 文件）
- 文件名应清晰表达内容

**常见文档**：
- `API_DOCS.md` - API 接口文档
- `EXAMPLES.md` - 使用示例集合
- `TECH_NOTES.md` - 技术说明
- `CHANGELOG.md` - 变更日志

### templates/（可选）

存放模板文件，如配置模板、输出模板等。

**命名规范**：
- 使用小写字母和下划线
- 后缀使用 `_template` 或 `.template`

**常见模板**：
- `config_template.json` - 配置文件模板
- `output_template.md` - 输出格式模板
- `report_template.html` - 报告模板

### assets/（可选）

存放其他资源文件，如 JSON schema、图片、数据文件等。

**命名规范**：
- 使用小写字母和下划线
- 根据文件类型使用适当的扩展名

**常见资源**：
- `schema.json` - JSON Schema 定义
- `config.yaml` - 配置文件
- `data.csv` - 数据文件
- `icon.png` - 图标文件

## 文件命名规范

### 通用规则

1. **Skill 目录名**：小写字母 + 连字符
   - ✅ `my-skill`、`api-parser`、`data-processor`
   - ❌ `MySkill`、`my_skill`、`My-Skill`

2. **SKILL.md**：必须全大写
   - ✅ `SKILL.md`
   - ❌ `skill.md`、`Skill.md`

3. **脚本文件**：小写字母 + 下划线 + 扩展名
   - ✅ `process_data.py`、`validate.sh`
   - ❌ `ProcessData.py`、`validate`

4. **文档文件**：大写字母 + 下划线 + `.md`
   - ✅ `API_DOCS.md`、`EXAMPLES.md`
   - ❌ `api_docs.md`、`examples.MD`

5. **模板文件**：小写字母 + 下划线 + `_template` + 扩展名
   - ✅ `output_template.md`、`config_template.json`
   - ❌ `OutputTemplate.md`、`template-config.json`

6. **资源文件**：小写字母 + 下划线 + 扩展名
   - ✅ `schema.json`、`user_data.csv`
   - ❌ `Schema.JSON`、`userData.csv`

## 最小化结构

最简单的 Skill 只需要一个文件：

```
my-skill/
└── SKILL.md
```

## 完整结构示例

### 示例 1：数据处理 Skill

```
data-processor/
├── SKILL.md
├── scripts/
│   ├── process.py
│   ├── validate.py
│   └── export.sh
├── references/
│   ├── API_DOCS.md
│   └── DATA_FORMAT.md
├── templates/
│   └── output_template.json
└── assets/
    └── schema.json
```

### 示例 2：代码审查 Skill

```
code-review/
├── SKILL.md
├── scripts/
│   ├── lint.py
│   ├── security_scan.py
│   └── complexity.py
├── references/
│   ├── SECURITY_RULES.md
│   └── STYLE_GUIDE.md
└── templates/
    └── review_report.md
```

### 示例 3：简单工具 Skill

```
text-formatter/
├── SKILL.md
└── scripts/
    └── format.py
```

## 注意事项

1. **SKILL.md 是必需的**，其他目录都是可选的
2. **不要添加多余的文件**，如 README.md（内容应该在 SKILL.md 中）
3. **遵循命名规范**，确保文件名清晰且一致
4. **目录结构扁平化**，不要创建过深的嵌套
5. **文件组织清晰**，相同类型的文件放在同一目录

## 创建新 Skill 的步骤

1. 创建 Skill 目录（小写-连字符格式）
2. 创建 `SKILL.md` 文件（必需）
3. 根据需要创建可选目录：
   - 有脚本？创建 `scripts/`
   - 有文档？创建 `references/`
   - 有模板？创建 `templates/`
   - 有资源？创建 `assets/`
4. 在 Cursor 中验证（Settings > Rules > Agent Decides）

## 验证清单

创建 Skill 后，检查：

- [ ] Skill 目录名使用小写-连字符格式
- [ ] `SKILL.md` 文件存在且全大写
- [ ] YAML Front Matter 格式正确
- [ ] Description 长度 50-200 字
- [ ] 脚本文件使用小写_下划线格式
- [ ] 文档文件使用大写_下划线格式
- [ ] 没有多余的 README.md 等文件
- [ ] 目录结构清晰且必要

---

**版本**: v1.0  
**更新日期**: 2026-01-18  
**适用于**: Cursor Nightly
