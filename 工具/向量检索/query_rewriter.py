"""
向量检索 Query 改写器
======================

把口语化 / 稀疏 query 扩展为向量检索友好的结构化串。
纯规则驱动 · 零额外 API 成本 · AI 侧与 CLI 均可直接调用。

工作流:
    原始 query
      ↓
    ① 抽取(extract) - 正则匹配出 任务类型/品牌/产品品类/地域/平台
      ↓
    ② 扩展(expand)  - 按抽取结果追加术语表 + 同义词
      ↓
    扩展后 query(向量检索效果更好)

典型例子:
    in  : "帮我做个好看的促销图,NEBILITY 塑身衣,美国市场"
    out : "帮我做个好看的促销图,NEBILITY 塑身衣,美国市场
           promotional banner poster CTA 折扣 红色 版式
           NEBILITY  shapewear bodysuit 塑形 内衣
           US DTC 欧美市场"

用法(CLI):
    python 工具/向量检索/query_rewriter.py "帮我做个促销图 NEBILITY 塑身衣"
    python 工具/向量检索/query_rewriter.py "..." --json
    python 工具/向量检索/query_rewriter.py "..." --task-type 促销图 --brand NEBILITY

用法(Python):
    from query_rewriter import rewrite
    result = rewrite("帮我做个好看的促销图 NEBILITY 塑身衣")
    print(result["expanded"])   # 扩展后的 query
    print(result["extracted"])  # 自动识别的元数据
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ============================================================================
# 领域词表(可随项目演进扩充)
# ============================================================================

# --- 任务类型 → 关键词 ---
TASK_TYPE_KEYWORDS = {
    "促销图": "promotional banner poster CTA 折扣 红色 版式 电商主图",
    "Banner": "banner 横幅 hero 主视觉 版式",
    "海报": "poster 广告 版式 视觉冲击",
    "产品主图": "product hero shot 白底 电商主图 产品展示",
    "白底产品图": "white background product shot 白底 纯产品 电商",
    "详情页": "detail page A+ listing 长图 模块化 卖点 电商详情",
    "详情页首图": "hero image 首屏 主视觉 详情页首图",
    "模特场景图": "model lifestyle shot 情境 生活场景 人物穿搭",
    "生活方式图": "lifestyle shot 生活场景 情境 氛围",
    "Logo": "logo mark 标识 品牌符号 视觉识别",
    "配色": "color palette 色板 配色方案 HEX",
    "字体": "typography font 字体设计 字重 排版",
    "换背景": "background replacement 换底 场景替换",
    "换装": "outfit change garment swap 换装",
    "风格转换": "style transfer 风格迁移 画风",
}

# --- 品牌 → 扩展关键词(读品牌规范/的品牌目录自动补全) ---
BRAND_KEYWORDS: dict[str, str] = {}  # 动态填充(init_brand_keywords)

# --- 产品品类 → 英文术语 + 相关词 ---
PRODUCT_KEYWORDS = {
    "塑身衣": "shapewear bodysuit 塑形 内衣 身材修饰",
    "塑身": "shapewear 塑形 身材修饰",
    "bodysuit": "bodysuit shapewear 连体塑身衣",
    "运动内衣": "sports bra activewear 运动 支撑",
    "运动": "sportswear activewear 运动",
    "塑形裤": "shaping leggings 塑形裤 紧身裤",
    "leggings": "leggings 紧身裤 塑形裤 运动",
    "打底裤": "leggings 紧身裤 打底",
    "内衣": "underwear lingerie 内衣",
    "泳装": "swimwear bikini 泳衣",
    "连体": "bodysuit jumpsuit 连体",
    "T恤": "t-shirt tee 上衣",
    "上衣": "top 上衣 tee",
    "裙装": "dress skirt 裙子",
}

# --- 地域 → 市场/平台关键词 ---
REGION_KEYWORDS = {
    "美国": "US DTC Amazon 欧美市场 北美",
    "欧美": "US EU DTC Amazon 欧美市场",
    "US": "US DTC Amazon 欧美市场",
    "欧洲": "EU 欧洲市场 Amazon",
    "日本": "Japan 日本 Rakuten Amazon.jp 日式",
    "中国": "China 中国市场 天猫 淘宝 小红书 京东",
    "国内": "China 中国市场 天猫 淘宝 小红书",
    "东南亚": "Southeast Asia SEA Shopee Lazada 东南亚",
    "泰国": "Thailand 泰国 Shopee Lazada 东南亚",
    "越南": "Vietnam 越南 Shopee Lazada 东南亚",
    "印尼": "Indonesia 印尼 Shopee Tokopedia 东南亚",
}

# --- 平台 → 规范关键词 ---
PLATFORM_KEYWORDS = {
    "Amazon": "Amazon A+ listing 亚马逊 电商详情页",
    "亚马逊": "Amazon A+ listing 亚马逊",
    "Shopify": "Shopify DTC 独立站 landing page Hero",
    "DTC": "DTC 独立站 Shopify landing page",
    "独立站": "DTC Shopify 独立站 landing page",
    "天猫": "Tmall 天猫 淘宝 详情页 宝贝详情",
    "淘宝": "Taobao 淘宝 天猫 详情页 宝贝详情",
    "京东": "JD 京东 详情页",
    "拼多多": "PDD 拼多多 详情页",
    "小红书": "Xiaohongshu RED 小红书 图文",
    "Instagram": "Instagram IG 社媒 方图",
    "TikTok": "TikTok 社媒 竖屏 9:16",
    "Shopee": "Shopee 虾皮 东南亚 电商",
}

# --- 风格/调性同义词(用于扩展口语化描述) ---
STYLE_SYNONYMS = {
    "高级感": "editorial premium sophisticated 高级感 精致",
    "简约": "minimal clean 极简 简约",
    "复古": "retro vintage 复古 怀旧",
    "年轻": "youthful vibrant 年轻 活力",
    "专业": "professional functional 专业 功能感",
    "温馨": "warm cozy 温馨 柔和",
    "性感": "sexy seductive 性感",
    "包容": "inclusive diverse 包容 多元",
}


# ============================================================================
# 数据类
# ============================================================================
@dataclass
class RewriteResult:
    original: str
    expanded: str
    extracted: dict[str, list[str]] = field(default_factory=dict)
    keywords_added: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "expanded": self.expanded,
            "extracted": self.extracted,
            "keywords_added": self.keywords_added,
        }


# ============================================================================
# 品牌表动态加载(从 品牌规范/*/品牌档案.txt 自动提取品牌名)
# ============================================================================
def init_brand_keywords():
    """扫描 品牌规范/ 下的所有品牌目录,把品牌名加入 BRAND_KEYWORDS。"""
    global BRAND_KEYWORDS
    if BRAND_KEYWORDS:
        return
    project_root = Path(__file__).resolve().parent.parent.parent
    brand_dir = project_root / "品牌规范"
    if not brand_dir.exists():
        return
    for sub in brand_dir.iterdir():
        if not sub.is_dir():
            continue
        if sub.name.startswith("_") or sub.name.startswith("00_"):
            continue
        # 用目录名作为品牌名关键词,向检索中引入品牌标识
        BRAND_KEYWORDS[sub.name] = sub.name  # 品牌名本身就是最有效的检索词


# ============================================================================
# 抽取(从自然语言 query 里识别元数据)
# ============================================================================
def extract_task_type(q: str) -> list[str]:
    hits = []
    # 长关键词优先匹配(避免"详情页首图"被"详情页"先吃掉)
    sorted_keys = sorted(TASK_TYPE_KEYWORDS.keys(), key=len, reverse=True)
    seen_positions = set()
    for key in sorted_keys:
        for m in re.finditer(re.escape(key), q, re.IGNORECASE):
            # 避免与已匹配的更长关键词重叠
            if any(p in range(m.start(), m.end()) for p in seen_positions):
                continue
            hits.append(key)
            seen_positions.update(range(m.start(), m.end()))
    return hits


def extract_by_dict(q: str, dictionary: dict) -> list[str]:
    """
    通用字典匹配,返回命中的 key 列表。
    长词优先覆盖:若"塑身衣"已命中并占据位置 3-6,则后续"塑身"出现在同区间时跳过。
    """
    hits: list[str] = []
    occupied: list[tuple[int, int]] = []
    sorted_keys = sorted(dictionary.keys(), key=len, reverse=True)
    for key in sorted_keys:
        for m in re.finditer(re.escape(key), q, re.IGNORECASE):
            s, e = m.start(), m.end()
            if any(os_ <= s and e <= oe for os_, oe in occupied):
                continue
            if key not in hits:
                hits.append(key)
            occupied.append((s, e))
    return hits


def extract_brand(q: str) -> list[str]:
    init_brand_keywords()
    return extract_by_dict(q, BRAND_KEYWORDS)


def extract_product(q: str) -> list[str]:
    return extract_by_dict(q, PRODUCT_KEYWORDS)


def extract_region(q: str) -> list[str]:
    return extract_by_dict(q, REGION_KEYWORDS)


def extract_platform(q: str) -> list[str]:
    return extract_by_dict(q, PLATFORM_KEYWORDS)


def extract_style(q: str) -> list[str]:
    return extract_by_dict(q, STYLE_SYNONYMS)


# ============================================================================
# 核心:改写
# ============================================================================
def rewrite(
    query: str,
    task_type: str | None = None,
    brand: str | None = None,
    product: str | None = None,
    region: str | None = None,
    platform: str | None = None,
) -> dict:
    """
    对输入 query 做两步扩展:
      1) extract — 自动识别任务类型 / 品牌 / 品类 / 地域 / 平台 / 风格
      2) expand  — 按识别结果追加术语表

    显式参数(task_type 等)会与自动识别结果合并去重,供 AI 精准控制扩展范围。
    """
    q = (query or "").strip()
    if not q:
        return RewriteResult(original="", expanded="").to_dict()

    init_brand_keywords()

    # -- Step 1: 抽取(auto + explicit 合并) --
    task_types = list(dict.fromkeys(extract_task_type(q) + ([task_type] if task_type else [])))
    brands = list(dict.fromkeys(extract_brand(q) + ([brand] if brand else [])))
    products = list(dict.fromkeys(extract_product(q) + ([product] if product else [])))
    regions = list(dict.fromkeys(extract_region(q) + ([region] if region else [])))
    platforms = list(dict.fromkeys(extract_platform(q) + ([platform] if platform else [])))
    styles = extract_style(q)

    extracted = {
        "task_type": task_types,
        "brand": brands,
        "product": products,
        "region": regions,
        "platform": platforms,
        "style": styles,
    }

    # -- Step 2: 扩展(按抽取结果追加同义/相关词) --
    added_blocks: list[str] = []

    def _add_from(keys: list[str], dictionary: dict):
        for k in keys:
            val = dictionary.get(k)
            if val and val not in added_blocks:
                added_blocks.append(val)

    _add_from(task_types, TASK_TYPE_KEYWORDS)
    _add_from(brands, BRAND_KEYWORDS)
    _add_from(products, PRODUCT_KEYWORDS)
    _add_from(regions, REGION_KEYWORDS)
    _add_from(platforms, PLATFORM_KEYWORDS)
    _add_from(styles, STYLE_SYNONYMS)

    if added_blocks:
        expanded = q + " " + " ".join(added_blocks)
    else:
        expanded = q

    result = RewriteResult(
        original=q,
        expanded=expanded,
        extracted=extracted,
        keywords_added=added_blocks,
    )
    return result.to_dict()


# ============================================================================
# CLI
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description="Query 改写器 · 把口语化 query 扩展为向量检索友好串")
    ap.add_argument("query", help="原始 query")
    ap.add_argument("--task-type", default=None, help="显式指定任务类型(覆盖自动识别)")
    ap.add_argument("--brand", default=None)
    ap.add_argument("--product", default=None)
    ap.add_argument("--region", default=None)
    ap.add_argument("--platform", default=None)
    ap.add_argument("--json", dest="as_json", action="store_true", help="以 JSON 输出完整元数据")
    args = ap.parse_args()

    result = rewrite(
        args.query,
        task_type=args.task_type,
        brand=args.brand,
        product=args.product,
        region=args.region,
        platform=args.platform,
    )

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 人类可读输出
    print("━" * 76)
    print("【Query 改写】")
    print("━" * 76)
    print(f"原 query  : {result['original']}")
    print(f"扩展 query: {result['expanded']}")
    print()
    print("抽取元数据:")
    for k, v in result["extracted"].items():
        if v:
            print(f"  {k:<10}: {', '.join(v)}")
    if result["keywords_added"]:
        print("\n追加的词块:")
        for i, block in enumerate(result["keywords_added"], 1):
            print(f"  [{i}] {block}")
    print("━" * 76)


if __name__ == "__main__":
    main()
