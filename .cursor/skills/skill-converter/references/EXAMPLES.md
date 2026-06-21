# Skill 转换示例集

本文档提供各种场景下的完整 Skill 转换示例。

## 示例 1：日志错误提取器

### 用户输入

```
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

### 生成的 SKILL.md

```markdown
---
name: log-error-extractor
description: 从应用日志中提取 ERROR 和 CRITICAL 级别的错误信息，生成结构化报告。支持 .log 和 .txt 格式。适用于快速诊断生产环境问题、生成错误统计报告、集成到 CI/CD 自动检查的场景。关键词：日志分析、错误提取、ERROR、CRITICAL、日志解析、故障诊断、报告生成。
---

# 日志错误提取器

## 概述

这个 Skill 帮助开发者快速从应用日志中提取关键错误信息，自动识别 ERROR 和 CRITICAL 级别的日志条目，并生成易于阅读的结构化报告，加速问题诊断和分析过程。

## 使用场景

- **生产环境故障诊断**：快速定位生产环境中的错误根因
- **错误统计分析**：生成错误类型分布和频率统计
- **CI/CD 自动检查**：集成到持续集成流程，自动检测新错误
- **日志清理**：从大量日志中筛选出需要关注的错误
- **团队协作**：生成标准化的错误报告便于团队讨论

## 工作流程

### 步骤 1：读取日志文件

支持多种日志文件格式：
- `.log` - 标准日志文件
- `.txt` - 纯文本日志

```python
def read_log_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.readlines()
```

### 步骤 2：匹配错误行

使用正则表达式匹配 ERROR 和 CRITICAL 级别的日志：

```python
import re

ERROR_PATTERN = r'\b(ERROR|CRITICAL)\b'

def extract_errors(lines):
    errors = []
    for line in lines:
        if re.search(ERROR_PATTERN, line, re.IGNORECASE):
            errors.append(line)
    return errors
```

### 步骤 3：提取关键信息

从每一行中提取：
- 时间戳
- 日志级别
- 模块名
- 错误信息

```python
def parse_error_line(line):
    # 示例格式: 2024-01-18 10:30:45 ERROR [ModuleName] Error message
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(ERROR|CRITICAL)\s+\[([^\]]+)\]\s+(.+)'
    match = re.match(pattern, line)
    
    if match:
        return {
            'timestamp': match.group(1),
            'level': match.group(2),
            'module': match.group(3),
            'message': match.group(4)
        }
    return None
```

### 步骤 4：生成报告

支持两种输出格式：

**JSON 格式**：
```json
{
  "total_errors": 15,
  "by_level": {
    "ERROR": 12,
    "CRITICAL": 3
  },
  "errors": [
    {
      "timestamp": "2024-01-18 10:30:45",
      "level": "ERROR",
      "module": "DatabaseHandler",
      "message": "Connection timeout"
    }
  ]
}
```

**Markdown 格式**：
```markdown
# 错误报告

## 总结
- 总错误数：15
- ERROR: 12
- CRITICAL: 3

## 详细列表

### 2024-01-18 10:30:45 - ERROR
**模块**: DatabaseHandler
**信息**: Connection timeout
```

## 使用方法

**输入要求**：
- 日志文件路径（.log 或 .txt）
- 可选：指定时间范围
- 可选：指定模块过滤

**输出格式**：
- JSON 格式的结构化数据
- Markdown 格式的可读报告

**调用示例**：
```bash
python scripts/extract_errors.py --file app.log --format json
python scripts/extract_errors.py --file app.log --format markdown --module DatabaseHandler
```

## 示例

### 示例 1：提取所有错误

**输入**：
```bash
extract_errors.py --file application.log
```

**输出**（JSON）：
```json
{
  "total_errors": 5,
  "errors": [
    {"timestamp": "2024-01-18 10:00:00", "level": "ERROR", "module": "Auth", "message": "Login failed"},
    {"timestamp": "2024-01-18 10:05:00", "level": "CRITICAL", "module": "DB", "message": "Connection lost"}
  ]
}
```

### 示例 2：按模块过滤

**输入**：
```bash
extract_errors.py --file application.log --module DatabaseHandler
```

**输出**（Markdown）：
```markdown
# 错误报告 - DatabaseHandler

## 总错误数: 3

### 2024-01-18 10:05:00 - CRITICAL
Connection lost to database server

### 2024-01-18 10:30:00 - ERROR
Query timeout after 30s
```

## 注意事项

- 日志格式必须相对标准（包含时间戳、级别、模块）
- 大文件处理可能需要较长时间
- 建议先在小文件上测试正则表达式
- 输出文件会覆盖已存在的同名文件

## 文件结构

```
log-error-extractor/
├── SKILL.md
└── scripts/
    └── extract_errors.py
```
```

### 目录结构

```
log-error-extractor/
├── SKILL.md
└── scripts/
    └── extract_errors.py
```

---

## 示例 2：Git 提交信息生成器

### 用户输入

```
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
```

### 生成的 SKILL.md

```markdown
---
name: git-commit-generator
description: 分析 git diff 自动生成符合 Conventional Commits 规范的提交信息。支持识别变更类型（feat/fix/docs/refactor）、提取关键内容、格式化输出。适用于提交代码时自动生成描述、统一团队提交风格、快速总结代码变更的场景。关键词：Git、提交信息、Conventional Commits、自动生成、代码分析、变更总结。
---

# Git 提交信息生成器

## 概述

这个 Skill 通过分析 git diff 输出，自动理解代码变更内容，生成符合 Conventional Commits 规范的提交信息，帮助开发者快速创建高质量、格式统一的提交记录。

## 使用场景

- **快速提交**：自动生成提交信息，节省编写时间
- **规范统一**：确保所有提交遵循 Conventional Commits 格式
- **团队协作**：提升团队提交信息的一致性和可读性
- **变更总结**：自动总结多文件变更的核心内容
- **提交历史**：生成清晰的提交历史，便于追溯

## 工作流程

### 步骤 1：获取代码变更

```bash
git diff --staged
```

### 步骤 2：识别变更类型

根据变更内容自动判断类型：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档变更
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具变更

### 步骤 3：提取关键信息

分析变更的文件和内容，提取核心变更点。

### 步骤 4：生成提交信息

格式：`<type>(<scope>): <subject>`

示例：
```
feat(auth): add OAuth2 login support
fix(api): resolve timeout issue in user endpoint
docs(readme): update installation instructions
```

## 使用方法

**输入要求**：
- 已暂存的 git 变更（`git add` 后）

**输出格式**：
- Conventional Commits 格式的提交信息

**调用示例**：
```bash
python scripts/generate_commit.py
```

## 示例

### 示例 1：新功能提交

**变更**：添加了用户认证模块

**生成**：
```
feat(auth): implement user authentication system

- Add login/logout endpoints
- Integrate JWT token generation
- Add session management
```

### 示例 2：Bug 修复

**变更**：修复了 API 超时问题

**生成**：
```
fix(api): resolve timeout in user data fetch

- Increase timeout to 30s
- Add retry mechanism
- Improve error handling
```

## 注意事项

- 需要先执行 `git add` 暂存变更
- 自动生成的信息可能需要手动调整
- 支持中英文混合（建议使用英文）
- 大量变更时建议分批提交

## 文件结构

```
git-commit-generator/
├── SKILL.md
└── scripts/
    └── generate_commit.py
```
```

### 目录结构

```
git-commit-generator/
├── SKILL.md
└── scripts/
    └── generate_commit.py
```

---

## 示例 3：API 文档生成器

### 用户输入

```
我想创建一个 Skill，用于从代码注释生成 API 文档。

功能：扫描 Python/JavaScript 代码，提取函数注释，生成 Markdown 格式的 API 文档。
支持：类型提示、参数说明、返回值说明、示例代码
使用场景：
- 自动更新 API 文档
- 保持代码和文档同步
- 生成 API 参考手册
```

### 目录结构

```
api-docs-generator/
├── SKILL.md
├── scripts/
│   ├── parse_python.py
│   └── parse_javascript.py
├── templates/
│   ├── api_template.md
│   └── function_template.md
└── references/
    └── EXAMPLES.md
```

---

## 示例 4：数据验证工具

### 用户输入

```
我想创建一个 Skill，用于验证 JSON 数据格式。

功能：根据 JSON Schema 验证数据，生成验证报告。
使用场景：
- API 请求数据验证
- 配置文件格式检查
- 数据质量保证
```

### 目录结构

```
json-validator/
├── SKILL.md
├── scripts/
│   └── validate.py
├── templates/
│   └── report_template.md
└── assets/
    ├── user_schema.json
    └── product_schema.json
```

---

## 转换模式对比

### 模式 1：信息完整（≥80分）

**特点**：用户提供了完整的能力描述、场景、流程

**Agent 行为**：
1. 评估完整度 → 95分
2. 直接生成 SKILL.md
3. 创建目录结构
4. 输出成功消息

### 模式 2：信息不足（50-79分）

**特点**：核心功能清晰，但缺少细节

**Agent 行为**：
1. 评估完整度 → 65分
2. 输出 3-5 个精准追问
3. 接收补充信息
4. 生成 SKILL.md

### 模式 3：信息严重不足（<50分）

**特点**：仅有基本想法，缺少大部分信息

**Agent 行为**：
1. 评估完整度 → 30分
2. 分阶段引导（目的→场景→流程）
3. 多轮补充信息
4. 生成 SKILL.md

---

## Description 优化示例

### 示例 1：过于简短（❌）

**原始**：
```
处理文件的工具
```

**问题**：
- 仅 6 字
- "处理"太宽泛
- 无使用场景
- 无关键词

**优化**：
```
批量重命名文件工具，支持正则表达式替换、序号自动添加、大小写转换。适用于批量整理文件名、统一命名规范、添加序号前缀的场景。关键词：文件重命名、批量处理、正则替换、序号、大小写转换、文件管理。
```

### 示例 2：过于泛化（❌）

**原始**：
```
帮助用户完成数据分析任务
```

**问题**：
- "帮助用户"太宽泛
- 未说明具体功能
- 无关键词

**优化**：
```
从 CSV/Excel 文件中提取数据，执行统计分析（均值、方差、分布），生成可视化图表和统计报告。适用于快速数据探索、生成统计摘要、数据质量检查的场景。关键词：数据分析、CSV、Excel、统计、可视化、报告生成。
```

### 示例 3：缺少关键词（❌）

**原始**：
```
一个很有用的 PDF 处理功能，可以做很多事情。
```

**问题**：
- "很有用"无实际信息
- "做很多事情"不具体
- 无关键词

**优化**：
```
提取 PDF 文档中的文本、图片和表格，转换为 Markdown/JSON 格式。支持批量处理、OCR 识别、表格结构保留。适用于文档内容提取、格式转换、数据迁移的场景。关键词：PDF、文本提取、OCR、表格识别、格式转换、Markdown。
```

---

**版本**: v1.0  
**更新日期**: 2026-01-18
