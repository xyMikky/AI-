---
name: amazon-image-extractor
description: 输入亚马逊商品页 URL（或本地 HTML 兜底），自动抓取并解析页面，提取套图与 A+ 图，下载原图后分别纵向拼接为一张长图。纯 Python，不需要浏览器渲染。适用：单 SKU 竞品分析、套图与 A+ 图一键收集。关键词：Amazon、亚马逊、套图、A+、竞品分析、图片抓取、纵向拼接、URL 抓取。
---

# Amazon 套图与 A+ 图提取器

## 概述

针对**单个商品**做竞品分析的提取器：

- 直接输入亚马逊商品页 URL，脚本自带浏览器伪装头抓页面
- 解析套图（主图/辅图）与 A+ 图文区域
- 下载原图到本地目录
- 分别拼接为 PNG 长图（RGBA，**画布留白与行间距完全透明**）：
  - `gallery_vertical.png`：套图纵向单列堆叠
  - `aplus_vertical.png`：同一跳转框横排成行，跨框纵向堆叠，所有图左对齐
- 输出结构化执行报告 `report.json`

无批量抓取场景，单次一个 URL，低频使用。

## 输入模式

| 模式 | 适用 | 参数 |
|---|---|---|
| **URL 模式（推荐）** | 单 SKU 竞品分析的默认方式 | `--url` |
| HTML 兜底模式 | URL 模式被亚马逊风控页拦截时使用 | `--html-path` |

两者二选一。`--url` 优先。

## 提取规则

- `gallery`：优先使用页面状态 `colorImages.initial`，按当前变体提取。
- `gallery`：若页面存在 `#altImages` 的 `variant-*` 缩略图列表，按该列表对齐过滤，只保留页面真实可见套图。
- `gallery`：默认 `hiRes-only`；仅在 `hiRes` 缺失时回退 `large`。
- `gallery`：按 Amazon 图片物理 ID 去重（忽略同图不同尺寸参数）。
- `aplus`：优先 `#aplus_feature_div`，仅在该容器缺失时回退 `#aplus`。
- `aplus`：过滤占位资源（`grey-pixel`、`.gif`）和明显非当前商品的卡片图（如模块 5 对比卡片）。
- `aplus`：抓取 `#aplus_feature_div` 内 JS 配置块中的 `aplus-media-library-service-media` URL，捕获轮播版块图片（排除对比表 `emc_p_m_5` / `_atc` 上下文）。
- `aplus`：**按页面模块分组拼接**——以 `aplus-module` 顶层节点为单位，每个轮播模块/单图模块=一组：
  - **同组（同一个跳转/轮播框）的图横向并排成一行**（各图按最小高度等比缩放对齐）
  - **跨组之间纵向堆叠**，所有行**左对齐**，画布宽 = 最宽行宽（最多张数的横排行）
  - 每张图保持原始尺寸（不强制行宽对齐），单图行右侧自然留白
  - 留白与行间距区域 = **透明**（alpha=0），结果保存为 `aplus_vertical.png`

## 命令行用法

### 默认：URL 模式

```powershell
python ".cursor/skills/amazon-image-extractor/scripts/extract_and_stitch.py" `
  --url "https://www.amazon.com/dp/B0F37FYBPG" `
  --output-dir "生成结果输出/amazon_extract_demo"
```

输出目录可省略，默认 `生成结果输出/amazon_extract_<ASIN>_<时间戳>/`。

### 风控兜底：HTML 模式

```powershell
python ".cursor/skills/amazon-image-extractor/scripts/extract_and_stitch.py" `
  --html-path "输入图片/amazon_sample.html" `
  --output-dir "生成结果输出/amazon_extract_html_demo"
```

## 参数说明

| 参数 | 说明 |
|---|---|
| `--url` | 亚马逊商品页 URL（与 `--html-path` 二选一） |
| `--html-path` | 本地 HTML 文件路径（URL 模式失败时兜底） |
| `--output-dir` | 输出目录，默认 `生成结果输出/amazon图片提取/<ASIN>_<时间戳>/` |
| `--spacing` | 纵向拼接间距，默认 `20` |
| `--min-width` | 过滤过小图片宽度，默认 `200` |
| `--timeout` | 抓取与下载超时秒数，默认 `20` |
| `--user-agent` | 抓取与下载使用的 UA，默认内置 Chrome UA |
| `--save-fetched-html` | URL 模式下额外保存原始 HTML 到输出目录（便于排查） |

## 抓取行为说明（URL 模式）

脚本使用 `requests.Session` + 完整浏览器请求头（UA / Accept / Accept-Language / Sec-Fetch-* 等）模拟首次访问 Amazon。

亚马逊的核心数据（`colorImages.initial`、A+ 全部模块的 URL 包括轮播）都在**首屏静态 HTML** 内，因此 `requests` 模式即可完整覆盖，无需 Playwright/浏览器渲染。

### 风控检测

如果亚马逊返回 robot check / captcha 页面，脚本会自动识别并输出：

```json
{
  "success": false,
  "error": "blocked_by_amazon: robot_check_page",
  "hint": "亚马逊触发了风控页。请稍后重试，或改用 --html-path 传入本地保存的 HTML。"
}
```

退出码为 `2`。建议处理：

1. 间隔 1-2 分钟后重试
2. 换网络环境（如切换梯子节点）
3. 浏览器手动打开 → 完整网页保存 → 改用 `--html-path` 兜底

## 输出结构

```text
生成结果输出/amazon图片提取/<ASIN>_<时间戳>/
  gallery/
    01_xxx.jpg            # 套图原图（保留亚马逊给的 JPEG，无需强转 PNG）
    02_xxx.jpg
    ...
  aplus/
    g01_01_xxx.jpg        # 第 1 个模块的第 1 张图
    g01_02_xxx.jpg        # 第 1 个模块的第 2 张图（同组横排）
    g02_01_xxx.jpg        # 第 2 个模块（单图）
    g05_03_xxx.jpg        # 第 5 个模块的第 3 张图
    ...
  gallery_vertical.png    # 套图纵向拼接（RGBA，行间隔透明）
  aplus_vertical.png      # A+ 同组横排 + 跨组纵向堆叠（RGBA，留白透明）
  report.json
  fetched_page.html       # 仅 --save-fetched-html 时存在
```

> 备注：单张下载的产品/A+ 原图保持亚马逊给的 JPEG 不改格式，避免无谓增大体积；只有最终的拼接长图才是 PNG + RGBA 透明背景。

A+ 图片命名规则：`g{模块序号:02d}_{组内序号:02d}_{md5_前10位}.{ext}`。同 `g0X` 前缀的图属于同一个轮播/跳转框。

## 报告字段（report.json）

- `success`: 是否执行成功
- `source.kind`: `url` 或 `html`
- `source.value`: 输入的 URL 或 HTML 路径
- `source.final_url`: URL 模式跳转后的实际 URL
- `base_url`: 用于解析与 ASIN 匹配的基准 URL
- `output_dir`: 固定为 `"."`（report.json 自身所在目录）。**文件内所有路径均为相对 output_dir 的相对路径**（如 `gallery/01_xxx.jpg`、`gallery_vertical.png`），保证整目录拷贝/转发给他人后仍可用，不含生成机器的绝对路径；stdout 打印版会把 `output_dir` 替换为绝对路径供调用方定位，但不写入文件
- `selectors_hit`: 命中选择器统计（含 `aplus_module_top_level` = 识别到的模块数量）
- `gallery`: 套图提取统计与文件列表
- `aplus.group_count`: A+ 模块（跳转框 + 独立大图）数量
- `aplus.groups[]`: 每个模块的 `{index, url_count, downloaded_count, files}`
- `aplus.vertical_image`: 最终拼接长图路径
- `errors`: 下载失败或解析异常信息

## 常见失败与处理

| 场景 | 表现 | 处理 |
|---|---|---|
| URL 风控页 | `blocked_by_amazon: robot_check_page` | 间隔后重试 / 换节点 / 改用 `--html-path` |
| URL 404 / 商品下架 | `fetch_failed: 404 Client Error` | 检查 URL 是否有效 |
| 套图数量偏少 | `gallery.url_count < 实际` | 加 `--save-fetched-html` 排查 HTML 是否被部分截断 |
| A+ 数量为 0 | `aplus.url_count: 0` | 该商品确实没有 A+ 内容（正常） |
| 下载部分失败 | `errors` 中有 `download_failed` | 通常是图床瞬时抖动，重跑即可 |

## 相关脚本

- `.cursor/skills/amazon-image-extractor/scripts/extract_and_stitch.py` — 唯一入口脚本
- `.cursor/skills/amazon-image-extractor/scripts/requirements.txt` — Python 依赖（首次使用前执行 `pip install -r .cursor/skills/amazon-image-extractor/scripts/requirements.txt`）

> V2.4 起本 Skill 的脚本由 `工具/amazon_image_extractor/` 迁移到此目录，遵循 Skill 自包含原则（详见 `.cursor/rules/skill-file-structure.mdc`）。原 `工具/amazon_image_extractor/` 已下线。
