---
name: excel-to-json
description: 将整个 Excel 工作簿（.xlsx/.xlsm）转换为 JSON 文件的工具脚本。输入 Excel 文件路径，输出与源文件同名的 .json（UTF-8、缩进 2）；默认给每条数据加一个从 1 开始的行号字段 number 标注这是第几组数据；单工作表输出对象数组、多工作表输出以工作表名为键的字典；自动把日期/时间单元格转为 ISO 字符串、为空表头补 col_N、为重名表头去重。仅依赖 openpyxl，无需 pandas。支持指定工作表、自定义表头行、自定义/关闭行号字段、records/columns 输出方向、只取首表。适用于：把 Excel 转成 JSON、表格数据导出为 JSON、xlsx 转 json、Excel 数据结构化、带行号/序号导出、评论/订单/商品表导出。关键词：Excel 转 JSON、xlsx 转 json、表格转 JSON、工作簿转换、数据导出、行号、序号、number、openpyxl、JSON 转换、表格数据。
---

# Excel 转 JSON 工具

## 概述

输入一个 Excel 工作簿（`.xlsx` / `.xlsm`），把它整体转换为 JSON 文件。单工作表输出对象数组，多工作表输出以工作表名为键的字典。**默认给每条数据追加一个从 1 开始的行号字段 `number`**，标注这是第几组数据。常被需要把表格数据结构化、导出或喂给程序处理的任务调用。仅依赖 `openpyxl`，无需安装 pandas。

## 调用方式

### 命令行

```bash
# 最简：输出到与源文件同名的 .json
python .codex/skills/excel-to-json/scripts/excel_to_json.py --input "d:\path\data.xlsx"

# 指定输出路径与缩进
python .codex/skills/excel-to-json/scripts/excel_to_json.py -i data.xlsx -o out.json --indent 4

# 只转换某个工作表，表头在第 2 行
python .codex/skills/excel-to-json/scripts/excel_to_json.py -i data.xlsx --sheet Sheet1 --header-row 2

# 按列输出（列字典）而非对象数组
python .codex/skills/excel-to-json/scripts/excel_to_json.py -i data.xlsx --orient columns

# 多工作表但只取第一个（不包工作表名层级）
python .codex/skills/excel-to-json/scripts/excel_to_json.py -i data.xlsx --first-sheet

# 自定义行号字段名为 序号
python .codex/skills/excel-to-json/scripts/excel_to_json.py -i data.xlsx --number-field 序号

# 不要行号字段
python .codex/skills/excel-to-json/scripts/excel_to_json.py -i data.xlsx --no-number
```

> Windows + 中文路径：直接传入完整路径并用双引号包裹即可。脚本以 UTF-8 写出，中文与换行符均正确保留（PowerShell 终端回显可能乱码，但文件内容正常）。

### 被其他任务/Skill 调用

任何需要"先把 Excel 变成结构化 JSON 再处理"的场景（数据分析、批量读取、导入数据库前的中转）都可直接调用本脚本，读取其打印的 JSON 摘要（含 `output` 路径与 `records_total`）。

## 参数说明

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|---|---|---|---|---|
| `--input` / `-i` | 路径 | 是 | — | 输入 `.xlsx`/`.xlsm` 文件 |
| `--output` / `-o` | 路径 | 否 | 同名 `.json` | 输出 JSON 路径 |
| `--sheet` / `-s` | 字符串 | 否 | 全部工作表 | 只转换指定名称的工作表 |
| `--header-row` | 整数 | 否 | `1` | 表头所在行号（1 基） |
| `--orient` | 枚举 | 否 | `records` | `records`=对象数组；`columns`=列字典 |
| `--first-sheet` | 开关 | 否 | 关 | 多表时只输出第一个工作表 |
| `--indent` | 整数 | 否 | `2` | JSON 缩进空格数 |
| `--number-field` | 字符串 | 否 | `number` | 行号字段名，标注第几组数据 |
| `--no-number` | 开关 | 否 | 关 | 关闭行号字段 |

## 返回值 / 产物

- **产物**：写出 JSON 文件（默认与源文件同目录、同名、`.json` 后缀）。
  - 单工作表 / `--first-sheet`：`[ {number: 1, 列名: 值, ...}, ... ]`（`number` 为行号，置于每条记录最前）
  - 多工作表：`{ "工作表名": [ {number: 1, ...}, ... ], ... }`（每个工作表内行号各自从 1 开始）
  - `--orient columns`：`{ "number": [1, 2, ...], "列名": [值, 值, ...], ... }`
  - `--no-number`：不含 `number` 字段
- **stdout**：一段 JSON 摘要，包含 `input` / `output` / `sheets` / `orient` / `records_total`，便于上层程序解析。

### 数据处理约定

- 行号字段 `number` → 默认开启，从 1 开始，按"实际有数据的行"计数（跳过的空行不占号），置于每条记录最前。
- 日期 / 时间单元格 → ISO 字符串（如 `2026-05-29`、`2026-05-29T10:30:00`）。
- 空表头 → 自动命名为 `col_1`、`col_2`……
- 重名表头 → 自动追加后缀去重（`名称`、`名称_1`）。
- 整行全空 → 跳过，不生成空对象。

## 错误处理

| 情况 | 行为 |
|---|---|
| 缺少 `openpyxl` | 打印安装提示（`pip install openpyxl`），退出码 2 |
| 输入文件不存在 | 报错并退出码 1 |
| 指定的 `--sheet` 不存在 | 报错并列出可用工作表名，退出码 1 |
| `.xls`（旧版二进制格式） | openpyxl 不支持，需先另存为 `.xlsx` |

## 依赖说明

- Python 3.7+
- `openpyxl`（读取 `.xlsx`/`.xlsm`；项目环境已安装）

## 文件结构

```
excel-to-json/
├── SKILL.md
└── scripts/
    └── excel_to_json.py
```
