"""交互式评论分析看板生成器（competitor-analyzer 第 4 件套）。

输入亚马逊评论数据（.json 或 .xlsx），产出一个**完全离线、自包含**的
交互式 HTML 看板 `review_dashboard.html`：
- 内联本地 ECharts（assets/echarts.min.js），双击即用、不依赖网络。
- 内嵌全量归一化评论记录，前端可二次过滤。
- 多维图表：星级 / 月度趋势（可框选时间范围）/ 变体 / 国家 / VP / 长度 / 主题 / 关键词云。
- 智能问题归类（--aspects）：维度→子问题分层 + 关键词上下文原话，点击下钻到评论明细。
- 任一图表点击或时间轴框选 → KPI、其它图表、评论明细表全局联动重算。

用法：
  python build_review_dashboard.py --input <reviews.json|.xlsx> \
      --meta <metadata.json> --output <输出目录> [--asin ASIN] [--themes themes.json]

默认全量、不按 ASIN 剔除（文件内多 ASIN = 同系列不同款式/颜色）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import review_core as rc

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ECHARTS_PATH = ASSETS_DIR / "echarts.min.js"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="生成交互式评论分析看板 HTML（离线自包含）")
    p.add_argument("--input", required=True, help="评论文件路径（.json 或 .xlsx）")
    p.add_argument("--meta", default="", help="metadata.json 路径（取标题/原链接/全局评分/目标ASIN）")
    p.add_argument(
        "--asin",
        default="",
        help="显式指定目标 ASIN；不传则默认取 metadata.json 的 asin（只分析 URL 对应竞品）",
    )
    p.add_argument(
        "--all-variants",
        action="store_true",
        help="逃生开关：分析文件内全部 ASIN（同系列所有款式/颜色），仅用户明确要求时使用",
    )
    p.add_argument("--themes", default="", help="可选主题配置 JSON：{主题名:[关键词...]}")
    p.add_argument(
        "--aspects",
        default="",
        help="可选智能问题归类 JSON：{维度名:{子问题名:[关键词...]}}（关键词用去撇号小写形式，如 'wont charge'）",
    )
    p.add_argument(
        "--keywords",
        default="",
        help="可选策展关键词云 JSON：{pos:[{term,match[]}],neg:[{term,match[]}]}（agent 二次校正后的关键词；match 用去撇号小写子串）。传入后覆盖该极性的自动词云",
    )
    p.add_argument(
        "--output",
        default="",
        help="输出目录；默认输入文件所在目录。文件名固定 review_dashboard.html",
    )
    return p.parse_args()


def compact_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """压缩记录用于内嵌（缩短键名 + 截断正文）。"""
    out = []
    for r in records:
        body = r["body"]
        title = r["title"]
        out.append(
            {
                "s": r["stars"],
                "d": r["date"] or "",
                "m": r["month"] or "",
                "v": r["variation"] or "（未标注）",
                "c": r["country"] or "（未知）",
                "p": 1 if r["vp"] else 0,
                "n": r["length"],
                "ti": title[:300],
                "bo": body[:5000],                              # 明细表展示完整正文（封顶 5000 防极端长文）
                "t": (title + " " + body)[:5000].lower(),       # 关键词/搜索/归类匹配文本同步放长，提高召回
            }
        )
    return out


def main() -> int:
    args = parse_args()

    themes: dict[str, list[str]] = {}
    if args.themes:
        themes = json.loads(Path(args.themes).read_text(encoding="utf-8-sig"))

    aspects: dict[str, Any] = {}
    if args.aspects:
        aspects = json.loads(Path(args.aspects).read_text(encoding="utf-8-sig"))

    keywords: dict[str, Any] = {}
    if args.keywords:
        keywords = json.loads(Path(args.keywords).read_text(encoding="utf-8-sig"))

    meta_json: dict[str, Any] = {}
    if args.meta:
        mp = Path(args.meta)
        if mp.exists():
            try:
                meta_json = json.loads(mp.read_text(encoding="utf-8"))
            except Exception:
                meta_json = {}

    target_asin = rc.resolve_target_asin(args.asin, meta_json, args.all_variants)
    records, load_meta = rc.load_reviews(args.input, asin_filter=target_asin)
    if not records:
        avail = ", ".join(f"{k}({v})" for k, v in load_meta["distinct_asin"].items())
        raise ValueError(
            f"目标 ASIN '{target_asin}' 在评论文件内 0 条评论。"
            f"文件内可用 ASIN：{avail}。"
            f"请确认 ASIN 是否正确，或加 --all-variants 分析全系列。"
        )

    in_path = Path(load_meta["source"])
    out_dir = Path(args.output).expanduser().resolve() if args.output else in_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "review_dashboard.html"

    # 全局综合评分主口径（覆盖全部评论，是产品真实口碑分；与抓取样本严格区分）
    global_rating = rc.global_rating_from_meta(meta_json)
    global_hist = global_rating.get("histogram") or None

    if target_asin:
        scoped_distinct_asin = {target_asin: len(records)}
        scoped_distinct_asin_count = 1
    else:
        scoped_distinct_asin = load_meta["distinct_asin"]
        scoped_distinct_asin_count = load_meta["distinct_asin_count"]

    meta_payload = {
        "meta": {
            "title": meta_json.get("title") or in_path.stem,
            "brand": meta_json.get("brand") or "",
            "asin": meta_json.get("asin") or "",
            "source_url": (meta_json.get("source_url") or "").strip(),
            "rating": meta_json.get("rating"),
            "rating_count": meta_json.get("rating_count"),
            "scope": load_meta["scope"],
            "distinct_asin": scoped_distinct_asin,
            "distinct_asin_count": scoped_distinct_asin_count,
            "global_histogram": global_hist,
            "global_rating": global_rating,
        },
        "themes": themes,
        "aspects": aspects,
        "keywords": keywords,
    }

    # 评论记录写成独立 JS 文件（script src 方式兼容 file:// 协议，双击 HTML 即可打开）
    records_compact = compact_records(records)
    records_js_path = out_dir / "reviews_data.js"
    records_js_path.write_text(
        "window.__REVIEW_RECORDS__=" + json.dumps(records_compact, ensure_ascii=False) + ";",
        encoding="utf-8",
    )

    echarts_js = ECHARTS_PATH.read_text(encoding="utf-8")
    meta_json_str = json.dumps(meta_payload, ensure_ascii=False)

    html_out = (
        HTML_TEMPLATE
        .replace("__TITLE__", _esc(meta_payload["meta"]["title"]))
        .replace("/*__ECHARTS__*/", echarts_js)
        .replace("/*__DATA__*/", "window.__REVIEW_META__ = " + meta_json_str + ";")
        .replace("/*__CSS__*/", CSS)
        .replace("/*__APP__*/", APP_JS)
    )
    out_path.write_text(html_out, encoding="utf-8")
    print(f"[ok] dashboard generated: {out_path} （{len(records)} 条评论）")
    print(f"[ok] reviews_data.js:     {records_js_path}")
    return 0


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ===========================================================================
# 前端模板
# ===========================================================================
CSS = r"""
:root{
  --bg:#f4f6fb; --card:#ffffff; --ink:#1f2937; --sub:#6b7280; --line:#e5e7eb;
  --accent:#2563eb; --accent2:#7c3aed; --good:#16a34a; --warn:#ea580c; --bad:#dc2626;
  --shadow:0 1px 3px rgba(15,23,42,.08),0 8px 24px rgba(15,23,42,.06);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;}
.wrap{max-width:1320px;margin:0 auto;padding:20px 18px 64px;}
.hero{display:flex;align-items:flex-start;gap:16px;flex-wrap:wrap;
  background:linear-gradient(120deg,#1e3a8a,#6d28d9);color:#fff;border-radius:16px;
  padding:20px 24px;box-shadow:var(--shadow);margin-bottom:18px;}
.hero h1{font-size:20px;margin:0 0 6px;line-height:1.35;}
.hero p{margin:0;opacity:.86;font-size:13px;max-width:760px;}
.hero-right{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap;}
.hero a{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.16);
  color:#fff;text-decoration:none;border-radius:999px;padding:8px 14px;font-size:13px;
  border:1px solid rgba(255,255,255,.3);transition:.15s;white-space:nowrap;}
.hero a:hover{background:rgba(255,255,255,.28);}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin-bottom:16px;}
.kpi{background:var(--card);border-radius:14px;padding:14px 16px;box-shadow:var(--shadow);
  display:flex;flex-direction:column;}
.kpi .k{font-size:12px;color:var(--sub);margin-bottom:6px;}
.kpi .v{font-size:26px;font-weight:700;}
.kpi .v small{font-size:13px;font-weight:500;color:var(--sub);}
.kpi .note{font-size:10.5px;color:var(--sub);margin-top:6px;line-height:1.4;}
/* 全局综合评分卡：主口径，视觉突出且不随筛选变化 */
.kpi.global{background:linear-gradient(135deg,#eef2ff,#faf5ff);
  border:1px solid #c7d2fe;box-shadow:0 1px 3px rgba(79,70,229,.12),0 10px 26px rgba(79,70,229,.10);}
.kpi.global .k{color:#4338ca;font-weight:700;display:flex;align-items:center;gap:6px;}
.kpi.global .v{color:#3730a3;}
.kpi.global .badge{font-size:9.5px;font-weight:700;color:#fff;background:#6366f1;
  border-radius:999px;padding:1px 7px;}
/* 样本口径卡：弱化标注，避免被误读为产品综合分 */
.kpi.sample .k::before{content:"样本 · ";color:#9ca3af;}
.toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:var(--card);
  border-radius:12px;padding:10px 14px;box-shadow:var(--shadow);margin-bottom:16px;}
.toolbar .lbl{font-size:13px;color:var(--sub);}
.chips{display:flex;gap:6px;flex-wrap:wrap;flex:1;min-width:200px;}
.chip{background:#eef2ff;color:#3730a3;border-radius:999px;padding:4px 10px;font-size:12px;
  display:inline-flex;align-items:center;gap:6px;border:1px solid #e0e7ff;}
.chip b{font-weight:700;}
.chip .x{cursor:pointer;opacity:.6;}.chip .x:hover{opacity:1;}
.btn{cursor:pointer;border:1px solid var(--line);background:#fff;color:var(--ink);
  border-radius:8px;padding:7px 14px;font-size:13px;transition:.15s;}
.btn:hover{border-color:var(--accent);color:var(--accent);}
.btn.reset{background:#fef2f2;border-color:#fecaca;color:#b91c1c;}
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px;}
.card{background:var(--card);border-radius:14px;padding:14px 16px;box-shadow:var(--shadow);}
.card h3{margin:0 0 10px;font-size:14px;display:flex;align-items:center;gap:8px;}
.card h3 .hint{font-size:11px;color:var(--sub);font-weight:400;margin-left:auto;}
.col-12{grid-column:span 12;}.col-8{grid-column:span 8;}.col-6{grid-column:span 6;}
.col-4{grid-column:span 4;}
.chart{width:100%;height:280px;}
.chart.tall{height:320px;}
.cloud{display:flex;flex-wrap:wrap;gap:7px;align-items:center;}
.cloud .cw{cursor:pointer;border-radius:8px;padding:3px 9px;border:1px solid transparent;
  transition:.12s;line-height:1.5;}
.cloud .cw:hover{border-color:currentColor;}
.cloud .pos{background:#ecfdf5;color:#047857;}
.cloud .neg{background:#fef2f2;color:#b91c1c;}
.cloud .lv3{font-size:19px;font-weight:700;}
.cloud .lv2{font-size:15px;font-weight:600;}
.cloud .lv1{font-size:12px;}
.cloud .cw small{opacity:.6;font-size:.8em;}
.cloud-cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.cloud-cols .ct{font-size:12px;color:var(--sub);margin-bottom:6px;font-weight:600;}
.tablewrap{overflow:auto;max-height:560px;border:1px solid var(--line);border-radius:10px;}
table.rv{width:100%;border-collapse:collapse;font-size:12.5px;}
table.rv th{position:sticky;top:0;background:#f8fafc;text-align:left;padding:8px 10px;
  border-bottom:1px solid var(--line);font-weight:600;color:var(--sub);z-index:1;cursor:pointer;}
table.rv td{padding:8px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top;}
table.rv tr:hover td{background:#fafbff;}
.stars{color:#f59e0b;white-space:nowrap;}
.stars .dim{color:#e5e7eb;}
.vp-yes{color:var(--good);font-weight:600;}.vp-no{color:var(--sub);}
.rv-text b{display:block;margin-bottom:2px;}
.rv-text .rv-body{color:var(--sub);white-space:pre-wrap;word-break:break-word;display:block;}
.tbl-note{font-size:12px;color:var(--sub);margin:8px 2px 0;}
.rv-tools{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 10px;}
.rv-tools .rl{font-size:12px;color:var(--sub);font-weight:600;}
.seg{display:inline-flex;gap:4px;flex-wrap:wrap;align-items:center;}
.seg button{cursor:pointer;border:1px solid var(--line);background:#fff;color:var(--ink);
  border-radius:7px;padding:5px 10px;font-size:12px;transition:.12s;line-height:1.2;}
.seg button:hover{border-color:var(--accent);color:var(--accent);}
.seg button.on{background:var(--accent);border-color:var(--accent);color:#fff;}
.seg button.on.bad{background:var(--bad);border-color:var(--bad);}
.seg button.on.good{background:var(--good);border-color:var(--good);}
.seg-sep{width:1px;height:18px;background:var(--line);margin:0 4px;}
.rv-sel,.rv-search{border:1px solid var(--line);border-radius:7px;padding:6px 10px;font-size:12px;
  background:#fff;color:var(--ink);}
.rv-search{min-width:200px;flex:1;}
.rv-search:focus,.rv-sel:focus{outline:none;border-color:var(--accent);}
.dual{font-size:12px;color:var(--sub);margin-top:8px;line-height:1.6;}
.dual b{color:var(--ink);}
.empty{color:var(--sub);font-size:13px;padding:20px;text-align:center;}
.aspects{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px;}
.asp-group{border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:#fafbff;}
.asp-head{font-size:13px;font-weight:700;margin-bottom:8px;display:flex;align-items:center;gap:8px;}
.asp-total{font-size:11px;color:var(--sub);font-weight:500;margin-left:auto;}
.asp-pol{font-size:10px;font-weight:700;padding:1px 7px;border-radius:999px;}
.asp-pol.pos{color:#15803d;background:#dcfce7;}
.asp-pol.neg{color:#b91c1c;background:#fee2e2;}
.asp-issues{display:flex;flex-direction:column;gap:6px;}
.asp-issue{cursor:pointer;text-align:left;border:1px solid var(--line);background:#fff;border-radius:9px;
  padding:8px 10px;display:flex;flex-direction:column;gap:5px;transition:.12s;width:100%;font:inherit;}
.asp-issue:hover{border-color:var(--accent);}
.asp-issue.on{border-color:var(--accent);background:#eff4ff;box-shadow:inset 0 0 0 1px var(--accent);}
.asp-issue.void{cursor:default;opacity:.5;}
.asp-issue.void:hover{border-color:var(--line);}
.asp-row1{display:flex;align-items:center;gap:8px;}
.asp-name{font-size:12.5px;font-weight:600;color:var(--ink);white-space:nowrap;}
.asp-bar{flex:1;height:6px;background:#eef2f7;border-radius:999px;overflow:hidden;min-width:36px;}
.asp-bar i{display:block;height:100%;border-radius:999px;}
.asp-cnt{font-size:11px;color:var(--sub);white-space:nowrap;font-variant-numeric:tabular-nums;}
.asp-quote{font-size:11px;color:#6b7280;line-height:1.5;overflow:hidden;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;}
@media(max-width:980px){.kpis{grid-template-columns:repeat(2,1fr)}
  .col-8,.col-6,.col-4{grid-column:span 12}.cloud-cols{grid-template-columns:1fr}}
"""

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>__TITLE__ · 评论分析看板</title>
<style>/*__CSS__*/</style>
<script>/*__ECHARTS__*/</script>
<script>/*__DATA__*/</script>
<script src="reviews_data.js"></script>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <div>
      <h1 id="heroTitle">评论分析看板</h1>
      <p>多维交互分析：点击任意图表筛选，拖动「月度趋势」下方的时间轴可<b>框选时间范围</b>，全看板联动重算。</p>
    </div>
    <div class="hero-right" id="heroRight"></div>
  </section>

  <section class="kpis" id="kpis"></section>

  <section class="toolbar">
    <span class="lbl">当前筛选：</span>
    <div class="chips" id="chips"><span class="lbl" id="noFilter">无（全量）</span></div>
    <button class="btn reset" id="resetBtn">重置全部筛选</button>
  </section>

  <section class="grid">
    <div class="card col-12">
      <h3>📈 月度趋势（评论量 + 平均星级）<span class="hint">拖动下方时间轴手柄即可框选时间范围 → 联动其它图表</span></h3>
      <div id="trendChart" class="chart tall"></div>
    </div>

    <div class="card col-6" id="globalStarCard">
      <h3>🌐 全局星级分布<span class="hint">全部评论 · 来自 Amazon 页面 · 主口径 · 不受筛选影响</span></h3>
      <div id="globalStarChart" class="chart"></div>
    </div>
    <div class="card col-6">
      <h3>⭐ 样本星级分布<span class="hint">抓取样本 · 受配额放大低星 · 点击柱体筛选</span></h3>
      <div id="starChart" class="chart"></div>
    </div>

    <div class="card col-4">
      <h3>🎨 变体 / 款式<span class="hint">点击筛选 · 颜色=低星比</span></h3>
      <div id="variationChart" class="chart"></div>
    </div>
    <div class="card col-4">
      <h3>🌍 国家 / 站点<span class="hint">点击筛选</span></h3>
      <div id="countryChart" class="chart"></div>
    </div>
    <div class="card col-4">
      <h3>✅ VP 认证对比<span class="hint">点击筛选</span></h3>
      <div id="vpChart" class="chart"></div>
    </div>

    <div class="card col-6">
      <h3>📏 评论长度分布</h3>
      <div id="lengthChart" class="chart"></div>
    </div>
    <div class="card col-6" id="themeCard">
      <h3>🎯 痛点主题分布</h3>
      <div id="themeChart" class="chart"></div>
    </div>

    <div class="card col-12">
      <h3>☁️ 评论关键词云<span class="hint">数据驱动 · 点击关键词筛选含该词评论</span></h3>
      <div class="cloud-cols">
        <div><div class="ct">✓ 好评高频词（4-5★）</div><div class="cloud" id="cloudPos"></div></div>
        <div><div class="ct">✗ 差评高频词（1-2★）</div><div class="cloud" id="cloudNeg"></div></div>
      </div>
    </div>

    <div class="card col-12" id="aspectCard">
      <h3>🧩 智能问题归类<span class="hint">AI 按主题归类同类问题 · 点击子问题→下方「评论明细」即筛出该问题的全部原话</span></h3>
      <div class="aspects" id="aspectBox"></div>
    </div>

    <div class="card col-12">
      <h3>📋 评论明细<span class="hint" id="tblHint">支持星级 / VP / 长度 / 关键词快速筛选，与上方图表联动</span></h3>
      <div class="rv-tools">
        <span class="rl">快速筛选</span>
        <div class="seg" id="rvStarSeg">
          <button data-grp="bad">差评 1-2★</button>
          <button data-grp="mid">中评 3★</button>
          <button data-grp="good">好评 4-5★</button>
          <span class="seg-sep"></span>
          <button data-star="5">5★</button>
          <button data-star="4">4★</button>
          <button data-star="3">3★</button>
          <button data-star="2">2★</button>
          <button data-star="1">1★</button>
        </div>
        <select class="rv-sel" id="rvVp">
          <option value="">VP：全部</option>
          <option value="1">仅 VP 认证</option>
          <option value="0">非 VP</option>
        </select>
        <select class="rv-sel" id="rvLen">
          <option value="">长度：全部</option>
          <option value="0-50">0-50 字</option>
          <option value="51-150">51-150 字</option>
          <option value="151-300">151-300 字</option>
          <option value="301-600">301-600 字</option>
          <option value="600+">600+ 字</option>
        </select>
        <input class="rv-search" id="rvSearch" type="search" placeholder="🔍 搜索标题 / 正文关键词…" />
      </div>
      <div class="tablewrap">
        <table class="rv">
          <thead><tr>
            <th data-sort="s">星级</th><th data-sort="d">日期</th>
            <th data-sort="v">款式</th><th data-sort="c">国家</th>
            <th data-sort="p">VP</th><th>评论内容</th>
          </tr></thead>
          <tbody id="rvBody"></tbody>
        </table>
      </div>
      <div class="tbl-note" id="tblNote"></div>
    </div>
  </section>
</div>
<script>/*__APP__*/</script>
</body>
</html>
"""

APP_JS = r"""
(function(){
  var DATA = window.__REVIEW_META__ || {meta:{},themes:{},aspects:{}};
  var ALL = window.__REVIEW_RECORDS__ || [];   // 由外部 reviews_data.js 提供（script src，兼容 file://）
  var META = DATA.meta || {};
  var THEMES = DATA.themes || {};
  var ASPECTS = DATA.aspects || {};
  var KEYWORDS = DATA.keywords || {};   // 策展词云（agent 二次校正）：{pos:[{term,match[]}], neg:[...]}

  // ---- 停用词（与 review_core.py 对齐）：虚词 / 介词 / 缩写碎片 / 通用评价词 ----
  var STOP = new Set((
    "the and for are but not you all any can had her was one our out has him his how its may new now old see two way who boy "+
    "did get let put say she too use used using uses that this with have from they will would there their what which when your "+
    "them then than into onto upon more some could other been very just also after only over such most even make made much many "+
    "well back still being where while these those because before between should does got really were read less off out on in up "+
    "down away around through about above below again once here there both each few nor own same own "+
    "doesnt dont didnt isnt wasnt arent werent cant couldnt wouldnt shouldnt wont havent hasnt hadnt aint "+
    "im ive id ill youre youve theyre theyve weve dont thats whats heres its lets gonna wanna "+
    "need needs needed want wants wanted like likes liked tried try trying feel feels felt look looks looked thought think "+
    "product amazon item buy bought purchase purchased ordered order review reviews star stars rating thing things lot bit "+
    "time times day days really actually basically literally definitely overall pretty quite kind sort "+
    "is it to of at be by do go he if me my or so us we am an as oh ok id"
  ).split(/\s+/));
  // 否定词：不直接丢弃，而是与后面的实词合并成「not work / not good / not worth」，避免语义反转
  var NEG = new Set("not no never none cannot cant couldnt wont wouldnt dont doesnt didnt isnt wasnt arent werent hasnt havent hadnt nor neither hardly barely without aint".split(" "));
  // 撇号统一为直引号并去除，使 doesn't→doesnt、turbo's→turbos 不被花引号截断成碎片
  var WORD = /[a-z]{2,}/g;

  function tokens(t){
    var s = (t||"").replace(/[\u2018\u2019\u02bc']/g,"");
    var m = s.match(WORD) || [], out=[], neg=false, span=0;
    for(var i=0;i<m.length;i++){
      var w=m[i];
      if(NEG.has(w)){ neg=true; span=0; continue; }      // 标记否定，作用到下一个实词
      if(STOP.has(w)){ if(neg && ++span>3) neg=false; continue; } // 否定可跨少量虚词(如 not really good)
      if(neg){ out.push("not "+w); neg=false; } else out.push(w);
    }
    return out;
  }
  function extractKw(recs, topN){
    var uni={}, bi={};
    for(var i=0;i<recs.length;i++){
      var tk = tokens(recs[i].t);
      for(var j=0;j<tk.length;j++){ uni[tk[j]]=(uni[tk[j]]||0)+1;
        if(j+1<tk.length){ var bg=tk[j]+" "+tk[j+1]; bi[bg]=(bi[bg]||0)+1; } }
    }
    // 仅保留达到阈值的词组
    var bigrams={};
    for(var b in bi){ if(bi[b]>=3) bigrams[b]=bi[b]; }
    // 词组优先：从构成词组的单词计数中扣除词组次数，避免“词组又被拆成单词”重复刷屏
    for(var bg2 in bigrams){ var ps=bg2.split(" ");
      for(var p=0;p<ps.length;p++){ if(uni[ps[p]]!=null) uni[ps[p]]-=bigrams[bg2]; } }
    var merged={};
    for(var u in uni){ if(uni[u]>=3) merged[u]=uni[u]; }          // 单词阈值抬到 3，削掉长尾碎词
    for(var bb in bigrams){ merged[bb]=Math.max(merged[bb]||0,bigrams[bb]); }
    var arr=Object.keys(merged).map(function(k){return {text:k,count:merged[k]};});
    arr.sort(function(a,b){return b.count-a.count;});
    return arr.slice(0, topN||18);
  }

  // ---- 全局筛选状态 ----
  var state = { stars:new Set(), variations:new Set(), countries:new Set(),
               vp:null, dateRange:null, lengthRange:null, keyword:null, search:"", aspect:null };

  // 归一化文本（去撇号）缓存：让 "wont charge" 能匹配 "won't charge"
  function normT(r){ if(r.__n==null) r.__n=String(r.t||"").replace(/[\u2018\u2019\u02bc']/g,""); return r.__n; }
  // 词元集合缓存（含一元词 + 相邻二元词组），与词云生成同源。点击词云时用「词元命中」而非「子串命中」，
  // 否则像 "not waste money" 这类否定合成词在原文里并非连续子串，会出现“点了却 0 条评论”的 bug。
  function tokenSet(r){
    if(r.__ts) return r.__ts;
    var tk=tokens(r.t), s=Object.create(null);
    for(var i=0;i<tk.length;i++){ s[tk[i]]=1; if(i+1<tk.length) s[tk[i]+" "+tk[i+1]]=1; }
    return r.__ts=s;
  }
  // 统一关键词匹配：state.keyword 为对象 {label, match:[...], mode:"tok"|"sub", band:"pos"|"neg"|null}
  function keywordMatch(r, kw){
    if(!kw) return true;
    var ok;
    if(kw.mode==="sub"){ var s=normT(r); ok=kw.match.some(function(m){return m && s.indexOf(m)>=0;}); }
    else { var ts=tokenSet(r); ok=kw.match.some(function(m){return !!ts[m];}); }
    if(!ok) return false;
    if(kw.band==="pos" && r.s<4) return false;
    if(kw.band==="neg" && !(r.s===1||r.s===2)) return false;
    return true;
  }
  // 情感极性星级门控：pos=只看好评(4-5★)，neg=只看差评/中评(1-3★)，any=不限
  function polOk(s, pol){ if(pol==="pos") return s>=4; if(pol==="neg") return s>=1&&s<=3; return true; }
  function kwHit(r, kws){ var s=normT(r); for(var i=0;i<kws.length;i++){ if(kws[i] && s.indexOf(kws[i])>=0) return true; } return false; }
  function matchAspect(r, kws, pol){ return polOk(r.s, pol) && kwHit(r, kws); }
  // 解析维度：支持 {子问题:[词]} 旧格式 或 {polarity, issues:{...}} 新格式；未声明 polarity 时按维度名推断
  function dimMeta(dim){
    var v = ASPECTS[dim] || {};
    var hasWrap = v && typeof v==="object" && !Array.isArray(v) && (v.issues || v.polarity);
    var issues = hasWrap ? (v.issues||{}) : v;
    var pol = hasWrap && v.polarity ? v.polarity : null;
    if(!pol){ pol = /正面|好评|优点|满意|positive|pros|赞/i.test(dim) ? "pos" : "any"; }
    return {pol:pol, issues:issues};
  }

  var ALL_MONTHS = (function(){
    var s={}; ALL.forEach(function(r){ if(r.m) s[r.m]=1; });
    return Object.keys(s).sort();
  })();
  var LEN_BUCKETS=[
    {label:"0-50",min:0,max:50},
    {label:"51-150",min:51,max:150},
    {label:"151-300",min:151,max:300},
    {label:"301-600",min:301,max:600},
    {label:"600+",min:601,max:1e9}
  ];
  function lengthBucket(label){
    for(var i=0;i<LEN_BUCKETS.length;i++){ if(LEN_BUCKETS[i].label===label) return LEN_BUCKETS[i]; }
    return null;
  }

  function inDateRange(m){
    if(!state.dateRange) return true;
    if(!m) return false;
    return m>=state.dateRange[0] && m<=state.dateRange[1];
  }
  function applyFilters(skipAspect){
    return ALL.filter(function(r){
      if(state.stars.size && !state.stars.has(r.s)) return false;
      if(state.variations.size && !state.variations.has(r.v)) return false;
      if(state.countries.size && !state.countries.has(r.c)) return false;
      if(state.vp!==null && r.p!==state.vp) return false;
      if(!inDateRange(r.m)) return false;
      if(state.lengthRange && !(r.n>=state.lengthRange.min && r.n<=state.lengthRange.max)) return false;
      if(state.keyword && !keywordMatch(r,state.keyword)) return false;
      if(state.search && r.t.indexOf(state.search)<0) return false;
      if(!skipAspect && state.aspect && !matchAspect(r,state.aspect.kws,state.aspect.pol)) return false;
      return true;
    });
  }

  // ---- 统计辅助 ----
  function bucketStats(recs){
    var n=recs.length, sum=0, valid=0, low=0;
    recs.forEach(function(r){ if(r.s>=1&&r.s<=5){sum+=r.s;valid++;} if(r.s===1||r.s===2)low++; });
    return {count:n, avg:valid? +(sum/valid).toFixed(2):0, lowPct:n? +(low/n*100).toFixed(1):0};
  }
  function groupBy(recs,key,top){
    var g={};
    recs.forEach(function(r){ var v=r[key]||"（未知）"; (g[v]=g[v]||[]).push(r); });
    var out=Object.keys(g).map(function(k){ var s=bucketStats(g[k]); return {label:k,count:s.count,avg:s.avg,lowPct:s.lowPct}; });
    out.sort(function(a,b){return b.count-a.count;});
    return out.slice(0, top||12);
  }

  // ---- 图表实例 ----
  var charts={};
  function mk(id){ var c=echarts.init(document.getElementById(id)); charts[id]=c; return c; }
  var GRID={left:8,right:16,top:24,bottom:8,containLabel:true};
  // 横向柱状图专用：右侧留足空间，避免 position:"right" 的数值标签（如满格 100/405）被裁切
  var GRIDH={left:8,right:52,top:24,bottom:8,containLabel:true};

  function toggleSet(set,val){ if(set.has(val)) set.delete(val); else set.add(val); }

  // ---- 月度趋势（时间轴框选源；始终基于全量） ----
  function renderTrend(){
    var c=charts.trendChart||mk("trendChart");
    var g={}; ALL.forEach(function(r){ if(r.m)(g[r.m]=g[r.m]||[]).push(r); });
    var counts=ALL_MONTHS.map(function(m){return g[m]?g[m].length:0;});
    var avgs=ALL_MONTHS.map(function(m){return g[m]?bucketStats(g[m]).avg:null;});
    c.setOption({
      tooltip:{trigger:"axis"},
      legend:{data:["评论量","平均星级"],top:2,left:"center"},
      grid:{left:8,right:24,top:46,bottom:64,containLabel:true},
      xAxis:{type:"category",data:ALL_MONTHS,axisLabel:{rotate:ALL_MONTHS.length>12?45:0}},
      yAxis:[
        {type:"value",name:"评论量",nameGap:16,nameTextStyle:{color:"#60a5fa",align:"left"}},
        {type:"value",name:"平均星级",min:0,max:5,interval:1,nameGap:16,
          nameTextStyle:{color:"#7c3aed",align:"right"},splitLine:{show:false}}
      ],
      dataZoom:[{type:"slider",bottom:14,height:20,start:0,end:100},{type:"inside"}],
      series:[
        {name:"评论量",type:"bar",data:counts,itemStyle:{color:"#93c5fd"},barMaxWidth:34},
        {name:"平均星级",type:"line",yAxisIndex:1,data:avgs,smooth:true,
          itemStyle:{color:"#7c3aed"},lineStyle:{width:3},connectNulls:true}
      ]
    });
    var apply=function(){
      var opt=c.getOption(); var dz=opt.dataZoom[0];
      var n=ALL_MONTHS.length; if(!n) return;
      var si = dz.startValue!=null? dz.startValue : Math.round((dz.start/100)*(n-1));
      var ei = dz.endValue!=null? dz.endValue : Math.round((dz.end/100)*(n-1));
      si=Math.max(0,Math.min(n-1,si)); ei=Math.max(0,Math.min(n-1,ei));
      if(si===0 && ei===n-1){ state.dateRange=null; }
      else { state.dateRange=[ALL_MONTHS[si],ALL_MONTHS[ei]]; }
      renderAll(false);
    };
    c.off("datazoom"); c.on("datazoom", debounce(apply,180));
  }

  function debounce(fn,ms){ var t; return function(){ clearTimeout(t); var a=arguments,th=this; t=setTimeout(function(){fn.apply(th,a);},ms); }; }

  // ---- 全局星级分布（主口径 · 常量，不随筛选变化；来自 Amazon 页面 global ratings） ----
  function renderGlobalStar(){
    var card=document.getElementById("globalStarCard");
    var gh=META.global_histogram;
    if(!gh || !gh.length){ if(card) card.style.display="none"; return; }
    if(card) card.style.display="";
    var c=charts.globalStarChart||mk("globalStarChart");
    var colors={5:"#16a34a",4:"#65a30d",3:"#ca8a04",2:"#ea580c",1:"#dc2626"};
    var byStar={}; gh.forEach(function(h){ byStar[+h.star]=+h.percent; });
    var data=[5,4,3,2,1].map(function(s){
      return {value: byStar[s]!=null?byStar[s]:0, star:s, itemStyle:{color:colors[s]}};
    });
    c.setOption({
      tooltip:{trigger:"axis",formatter:function(p){var d=p[0];return d.name+"<br/>占比 "+d.value+"%（全部评论）";}},
      grid:GRIDH,
      xAxis:{type:"value",max:100,axisLabel:{formatter:"{value}%"}},
      yAxis:{type:"category",data:["5★","4★","3★","2★","1★"]},
      series:[{type:"bar",data:data,barMaxWidth:24,label:{show:true,position:"right",
        formatter:function(p){return p.value+"%";}}}]
    });
  }

  // ---- 星级（样本口径） ----
  function renderStar(recs){
    var c=charts.starChart||mk("starChart");
    var cnt={1:0,2:0,3:0,4:0,5:0}; recs.forEach(function(r){ if(cnt[r.s]!=null)cnt[r.s]++; });
    var colors={5:"#16a34a",4:"#65a30d",3:"#ca8a04",2:"#ea580c",1:"#dc2626"};
    var data=[5,4,3,2,1].map(function(s){return {value:cnt[s],star:s,
      itemStyle:{color: state.stars.size&&!state.stars.has(s)?"#e5e7eb":colors[s]}};});
    c.setOption({tooltip:{trigger:"axis"},grid:GRIDH,
      xAxis:{type:"value",scale:false},yAxis:{type:"category",data:["5★","4★","3★","2★","1★"]},
      series:[{type:"bar",data:data,barMaxWidth:24,label:{show:true,position:"right",
        formatter:function(p){return p.value;}}}]});
    c.off("click"); c.on("click",function(p){ var s=5-p.dataIndex; toggleSet(state.stars,s); renderAll(false); });
  }

  // ---- 通用分组条形（变体/国家） ----
  function renderGroupBar(id,recs,key,stateSet,colorByLow){
    var c=charts[id]||mk(id);
    var rows=groupBy(recs,key,12);
    var labels=rows.map(function(r){return r.label;});
    var data=rows.map(function(r){
      var dim = stateSet.size && !stateSet.has(r.label);
      var col = colorByLow ? lowColor(r.lowPct) : "#60a5fa";
      return {value:r.count, label:r.label, avg:r.avg, lowPct:r.lowPct,
        itemStyle:{color: dim?"#e5e7eb":col}};
    });
    c.setOption({
      tooltip:{trigger:"item",formatter:function(p){var d=p.data;
        return d.label+"<br/>数量 "+d.value+" · 均分 "+d.avg+"★ · 低星比 "+d.lowPct+"%";}},
      grid:GRIDH,xAxis:{type:"value"},
      yAxis:{type:"category",data:labels,inverse:true,axisLabel:{width:96,overflow:"truncate"}},
      series:[{type:"bar",data:data,barMaxWidth:20,label:{show:true,position:"right",
        formatter:function(p){return p.value;}}}]
    });
    c.off("click"); c.on("click",function(p){ toggleSet(stateSet,p.data.label); renderAll(false); });
  }
  function lowColor(p){ return p>=30?"#dc2626":(p>=15?"#ea580c":"#16a34a"); }

  // ---- VP ----
  function renderVp(recs){
    var c=charts.vpChart||mk("vpChart");
    var vp=recs.filter(function(r){return r.p===1;}), non=recs.filter(function(r){return r.p===0;});
    var sv=bucketStats(vp), sn=bucketStats(non);
    c.setOption({tooltip:{trigger:"item",formatter:function(p){
        return p.name+"<br/>数量 "+p.value+" · 均分 "+p.data.avg+"★";}},
      grid:GRID,xAxis:{type:"category",data:["VP 认证","非 VP"]},yAxis:{type:"value"},
      series:[{type:"bar",barMaxWidth:60,data:[
        {value:sv.count,avg:sv.avg,k:1,itemStyle:{color:state.vp===0?"#e5e7eb":"#16a34a"}},
        {value:sn.count,avg:sn.avg,k:0,itemStyle:{color:state.vp===1?"#e5e7eb":"#9ca3af"}}],
        label:{show:true,position:"top",formatter:function(p){return p.value;}}}]});
    c.off("click"); c.on("click",function(p){ var k=p.data.k; state.vp=(state.vp===k)?null:k; renderAll(false); });
  }

  // ---- 长度 ----
  function renderLength(recs){
    var c=charts.lengthChart||mk("lengthChart");
    var data=LEN_BUCKETS.map(function(b){
      var active = state.lengthRange && state.lengthRange.label===b.label;
      var dim = state.lengthRange && !active;
      return {
        value:recs.filter(function(r){return r.n>=b.min&&r.n<=b.max;}).length,
        label:b.label,min:b.min,max:b.max,
        itemStyle:{color:dim?"#e5e7eb":(active?"#7c3aed":"#a78bfa")}
      };
    });
    c.setOption({tooltip:{trigger:"axis",formatter:function(params){
        var p=params[0], d=p.data;
        return d.label+" 字<br/>数量 "+d.value+"<br/>点击可筛选该长度区间";
      }},grid:GRID,
      xAxis:{type:"category",data:LEN_BUCKETS.map(function(b){return b.label;})},yAxis:{type:"value"},
      series:[{type:"bar",data:data,barMaxWidth:40,
        label:{show:true,position:"top"}}]});
    c.off("click"); c.on("click",function(p){
      var d=p.data;
      state.lengthRange = (state.lengthRange && state.lengthRange.label===d.label)
        ? null
        : {label:d.label,min:d.min,max:d.max};
      renderAll(false);
    });
  }

  // ---- 主题 ----
  function renderTheme(recs){
    var card=document.getElementById("themeCard");
    var names=Object.keys(THEMES||{});
    if(!names.length){ card.style.display="none"; return; }
    card.style.display="";
    var c=charts.themeChart||mk("themeChart");
    var neg=recs.filter(function(r){return r.s===1||r.s===2;});
    var all=names.map(function(n){var pats=THEMES[n].map(function(p){return p.toLowerCase();});
      return recs.filter(function(r){return pats.some(function(p){return r.t.indexOf(p)>=0;});}).length;});
    var negc=names.map(function(n){var pats=THEMES[n].map(function(p){return p.toLowerCase();});
      return neg.filter(function(r){return pats.some(function(p){return r.t.indexOf(p)>=0;});}).length;});
    c.setOption({tooltip:{trigger:"axis"},legend:{data:["命中","其中差评"],top:0,right:0},
      grid:GRID,xAxis:{type:"value"},yAxis:{type:"category",data:names,inverse:true,
        axisLabel:{width:84,overflow:"truncate"}},
      series:[{name:"命中",type:"bar",data:all,barGap:"-100%",itemStyle:{color:"#cbd5e1"},barMaxWidth:18},
        {name:"其中差评",type:"bar",data:negc,itemStyle:{color:"#dc2626"},barMaxWidth:18}]});
  }

  // ---- 智能问题归类（维度→子问题→关键词；点击下钻到评论明细） ----
  var ASP_FLAT = [];   // 渲染时重建：[{label, kws}]，按钮 data-asp=index
  function renderAspects(){
    var card=document.getElementById("aspectCard");
    var dims=Object.keys(ASPECTS||{});
    if(!dims.length){ if(card) card.style.display="none"; return; }
    card.style.display="";
    var base=applyFilters(true);                 // 归类统计忽略 aspect 自身，便于横向比较
    ASP_FLAT=[];
    var html="";
    dims.forEach(function(dim){
      var dm=dimMeta(dim), issues=dm.issues, pol=dm.pol, names=Object.keys(issues);
      var rows=names.map(function(nm){
        var kws=(issues[nm]||[]).map(function(k){return String(k).toLowerCase();});
        var hit=base.filter(function(r){return matchAspect(r,kws,pol);});
        var low=hit.filter(function(r){return r.s===1||r.s===2;}).length;
        var quote=pickQuote(hit,kws);
        return {name:nm,kws:kws,count:hit.length,
          lowPct:hit.length?Math.round(low/hit.length*100):0,quote:quote};
      });
      var total=rows.reduce(function(a,b){return a+b.count;},0);
      var maxc=Math.max(1,Math.max.apply(null,rows.map(function(r){return r.count;})));
      var issuesHtml=rows.map(function(r){
        var idx=ASP_FLAT.length; ASP_FLAT.push({label:dim+" · "+r.name,kws:r.kws,pol:pol});
        var on = state.aspect && state.aspect.label===(dim+" · "+r.name);
        var voidCls = r.count? "":" void";
        var w=Math.round(r.count/maxc*100);
        // 正面维度：count 越多越绿（好评信号）；其余维度：低星比越高越红
        var col=r.count? (pol==="pos"? "#16a34a" : lowColor(r.lowPct)) : "#cbd5e1";
        var metric = r.count? (pol==="pos"? " · 好评" : " · 低星 "+r.lowPct+"%") : "";
        var q = r.count? esc(r.quote||"") : "（当前范围无匹配评论）";
        return '<button class="asp-issue'+(on?" on":"")+voidCls+'" data-asp="'+idx+'"'+(r.count?"":" disabled")+'>'+
          '<div class="asp-row1"><span class="asp-name">'+esc(r.name)+'</span>'+
          '<span class="asp-bar"><i style="width:'+w+'%;background:'+col+'"></i></span>'+
          '<span class="asp-cnt">×'+r.count+metric+'</span></div>'+
          '<div class="asp-quote">'+q+'</div></button>';
      }).join("");
      var polTag = pol==="pos"? '<span class="asp-pol pos">好评</span>'
                 : pol==="neg"? '<span class="asp-pol neg">差评/中评</span>' : "";
      html+='<div class="asp-group"><div class="asp-head">'+esc(dim)+polTag+
        '<span class="asp-total">命中 '+total+' 次</span></div>'+
        '<div class="asp-issues">'+issuesHtml+'</div></div>';
    });
    document.getElementById("aspectBox").innerHTML=html;
  }
  // 选一条代表性原话：优先低星，并截取「关键词所在上下文片段」，让引语精准对应该子问题
  function pickQuote(hit, kws){
    if(!hit.length) return "";
    var pool=hit.slice().sort(function(a,b){
      var la=(a.s<=2?0:1), lb=(b.s<=2?0:1); if(la!==lb) return la-lb;   // 低星优先
      return (b.n||0)-(a.n||0);                                          // 再按长度
    });
    var scan=Math.min(pool.length,14);
    for(var i=0;i<scan;i++){
      var disp=((pool[i].ti?pool[i].ti+"：":"")+(pool[i].bo||"")).replace(/\s+/g," ").trim();
      var low=disp.toLowerCase();
      for(var j=0;j<kws.length;j++){
        var p=low.indexOf(kws[j]); if(p<0) continue;
        var s=Math.max(0,p-42), e=Math.min(disp.length,p+kws[j].length+78);
        return (s>0?"…":"")+disp.slice(s,e).trim()+(e<disp.length?"…":"");
      }
    }
    var f=(pool[0].bo||pool[0].ti||"").trim();    // 兜底（多因撇号差异未命中）
    return f.length>120? f.slice(0,120)+"…":f;
  }

  // ---- 词云 ----
  // KW_FLAT：词云关键词注册表，按钮 data-kw=index → {label, match[], mode, band}，点击/高亮统一据此
  var KW_FLAT = [];
  function curatedBand(band){
    var arr = KEYWORDS[band];
    return (arr && arr.length) ? arr : null;
  }
  // 构造某极性的词云条目数组：优先用 agent 策展（match 子串计数），否则回退自动分词
  function buildCloud(band, sub){
    var curated = curatedBand(band);
    if(curated){
      return curated.map(function(e){
        var match=(e.match||[]).map(function(m){return String(m).toLowerCase().replace(/[\u2018\u2019\u02bc']/g,"");});
        var cnt=sub.filter(function(r){ var s=normT(r); return match.some(function(m){return m&&s.indexOf(m)>=0;}); }).length;
        return {label:e.term||(match[0]||""), match:match, mode:"sub", band:band, count:cnt};
      }).filter(function(d){return d.count>0;}).sort(function(a,b){return b.count-a.count;});
    }
    return extractKw(sub,18).map(function(d){
      return {label:d.text, match:[d.text], mode:"tok", band:band, count:d.count};
    });
  }
  function renderClouds(recs){
    KW_FLAT=[];
    var posSub=recs.filter(function(r){return r.s>=4;});
    var negSub=recs.filter(function(r){return r.s<=2 && r.s>=1;});
    paintCloud("cloudPos",buildCloud("pos",posSub),"pos");
    paintCloud("cloudNeg",buildCloud("neg",negSub),"neg");
  }
  function paintCloud(id,arr,cls){
    var el=document.getElementById(id);
    if(!arr.length){ el.innerHTML='<span class="empty">当前筛选下无足够数据</span>'; return; }
    var max=arr[0].count||1;
    el.innerHTML=arr.map(function(d){
      var idx=KW_FLAT.length; KW_FLAT.push({label:d.label,match:d.match,mode:d.mode,band:d.band});
      var lv = d.count/max>=0.66?3:(d.count/max>=0.33?2:1);
      var active = (state.keyword && state.keyword.label===d.label) ? ' style="outline:2px solid currentColor"':'';
      return '<span class="cw '+cls+' lv'+lv+'" data-kw="'+idx+'"'+active+'>'+esc(d.label)+' <small>×'+d.count+'</small></span>';
    }).join("");
    [].forEach.call(el.querySelectorAll(".cw"),function(node){
      node.onclick=function(){ var k=KW_FLAT[+node.getAttribute("data-kw")]; if(!k) return;
        state.keyword = (state.keyword && state.keyword.label===k.label)? null : {label:k.label,match:k.match,mode:k.mode,band:k.band};
        renderAll(false); };
    });
  }

  // ---- 明细表 ----
  var sortKey="d", sortDir=-1;
  function renderTable(recs){
    var rows=recs.slice().sort(function(a,b){
      var x=a[sortKey],y=b[sortKey]; if(x<y)return -1*sortDir; if(x>y)return 1*sortDir; return 0; });
    var body=document.getElementById("rvBody");
    if(!rows.length){ body.innerHTML='<tr><td colspan="6"><div class="empty">当前筛选下没有评论</div></td></tr>'; }
    else{
      body.innerHTML=rows.map(function(r){
        var bo=r.bo||"";
        return '<tr><td><span class="stars">'+stars(r.s)+'</span></td>'+
          '<td>'+esc(r.d||"-")+'</td><td>'+esc(r.v)+'</td><td>'+esc(r.c)+'</td>'+
          '<td class="'+(r.p?'vp-yes':'vp-no')+'">'+(r.p?'✓':'—')+'</td>'+
          '<td class="rv-text"><b>'+esc(r.ti||"")+'</b><span class="rv-body">'+esc(bo)+'</span></td></tr>';
      }).join("");
    }
    document.getElementById("tblNote").textContent = "显示全部 "+rows.length+" 条";
  }
  function stars(n){ n=Math.max(0,Math.min(5,n||0)); var s=""; for(var i=0;i<5;i++) s+= i<n?"★":'<span class="dim">★</span>'; return s; }

  // ---- KPI + chips ----
  function fmtInt(n){ return (n==null||n==="")?"":String(n).replace(/\B(?=(\d{3})+(?!\d))/g,","); }
  function renderKpis(recs){
    var s=bucketStats(recs);
    var vp=recs.filter(function(r){return r.p===1;}).length;
    var vpPct=recs.length? Math.round(vp/recs.length*100):0;
    // 全局综合评分（主口径）：覆盖全部评论，常量，不随筛选变化
    var g=META.global_rating||{};
    var gVal = (g.rating!=null? g.rating : (g.avg!=null? g.avg : null));
    var gValHtml = gVal!=null
      ? gVal+'<small> ★'+(g.rating_count?(' / '+fmtInt(g.rating_count)+' 评价'):'')+'</small>'
      : '—<small> 页面未提供</small>';
    var gNote = gVal!=null
      ? '全部评论综合 · 产品真实口碑分'
      : '页面未抓到全局评分，综合分缺失';
    document.getElementById("kpis").innerHTML=
      kpiGlobal("全局综合评分", gValHtml, gNote)+
      kpiSample("评论数", recs.length+'<small> / '+ALL.length+' 样本</small>')+
      kpiSample("均分", s.avg+'<small> ★</small>')+
      kpiSample("低星比 (1-2★)", s.lowPct+'<small>%</small>')+
      kpiSample("VP 认证占比", vpPct+'<small>%</small>');
  }
  function kpiGlobal(k,v,note){
    return '<div class="kpi global"><div class="k"><span class="badge">主口径</span>'+esc(k)+'</div>'+
      '<div class="v">'+v+'</div><div class="note">'+esc(note)+'</div></div>';
  }
  function kpiSample(k,v){ return '<div class="kpi sample"><div class="k">'+esc(k)+'</div><div class="v">'+v+'</div></div>'; }

  function renderChips(){
    var box=document.getElementById("chips"); var items=[];
    function add(label,onx){ items.push({label:label,onx:onx}); }
    state.stars.forEach(function(s){ add("星级 "+s+"★",function(){state.stars.delete(s);}); });
    state.variations.forEach(function(v){ add("款式: "+v,function(){state.variations.delete(v);}); });
    state.countries.forEach(function(c){ add("国家: "+c,function(){state.countries.delete(c);}); });
    if(state.vp!==null) add("VP: "+(state.vp?"是":"否"),function(){state.vp=null;});
    if(state.dateRange) add("时间: "+state.dateRange[0]+" ~ "+state.dateRange[1],function(){
      state.dateRange=null; resetTrendZoom(); });
    if(state.lengthRange) add("长度: "+state.lengthRange.label+" 字",function(){state.lengthRange=null;});
    if(state.keyword) add("关键词: "+state.keyword.label,function(){state.keyword=null;});
    if(state.search) add("搜索: "+state.search,function(){state.search="";});
    if(state.aspect) add("问题: "+state.aspect.label,function(){state.aspect=null;});
    document.getElementById("noFilter").style.display = items.length?"none":"";
    box.querySelectorAll(".chip").forEach(function(n){n.remove();});
    items.forEach(function(it){
      var sp=document.createElement("span"); sp.className="chip";
      sp.innerHTML='<b>'+esc(it.label)+'</b> <span class="x">✕</span>';
      sp.querySelector(".x").onclick=function(){ it.onx(); renderAll(true); };
      box.appendChild(sp);
    });
  }
  function resetTrendZoom(){ if(charts.trendChart) charts.trendChart.dispatchAction({type:"dataZoom",start:0,end:100}); }

  // ---- 评论明细快速筛选条（与全局 state 同源，状态回显） ----
  var RV_GROUPS={bad:[1,2],mid:[3],good:[4,5]};
  function renderTableTools(){
    var seg=document.getElementById("rvStarSeg");
    if(seg){
      [].forEach.call(seg.querySelectorAll("button[data-star]"),function(b){
        b.classList.toggle("on", state.stars.has(+b.getAttribute("data-star")));
      });
      [].forEach.call(seg.querySelectorAll("button[data-grp]"),function(b){
        var grp=b.getAttribute("data-grp"), g=RV_GROUPS[grp]||[];
        var on=g.length && g.every(function(s){return state.stars.has(s);});
        b.classList.remove("on","bad","good");
        if(on){ b.classList.add("on"); if(grp==="bad")b.classList.add("bad"); if(grp==="good")b.classList.add("good"); }
      });
    }
    var vpSel=document.getElementById("rvVp");
    if(vpSel) vpSel.value = (state.vp===null)?"":String(state.vp);
    var lenSel=document.getElementById("rvLen");
    if(lenSel) lenSel.value = state.lengthRange ? state.lengthRange.label : "";
    var sb=document.getElementById("rvSearch");
    if(sb && document.activeElement!==sb) sb.value = state.search||"";
  }
  function bindTableTools(){
    var seg=document.getElementById("rvStarSeg");
    if(seg) seg.addEventListener("click",function(e){
      var b=e.target.closest&&e.target.closest("button"); if(!b||!seg.contains(b)) return;
      if(b.hasAttribute("data-star")){ toggleSet(state.stars,+b.getAttribute("data-star")); renderAll(false); }
      else if(b.hasAttribute("data-grp")){
        var g=RV_GROUPS[b.getAttribute("data-grp")]||[];
        var allOn=g.length && g.every(function(s){return state.stars.has(s);});
        g.forEach(function(s){ if(allOn) state.stars.delete(s); else state.stars.add(s); });
        renderAll(false);
      }
    });
    var vpSel=document.getElementById("rvVp");
    if(vpSel) vpSel.onchange=function(){ state.vp = this.value===""?null:+this.value; renderAll(false); };
    var lenSel=document.getElementById("rvLen");
    if(lenSel) lenSel.onchange=function(){
      var b = lengthBucket(this.value);
      state.lengthRange = b ? {label:b.label,min:b.min,max:b.max} : null;
      renderAll(false);
    };
    var sb=document.getElementById("rvSearch");
    if(sb) sb.oninput=debounce(function(){ state.search=(sb.value||"").trim().toLowerCase(); renderAll(false); },220);
  }

  // ---- 主渲染 ----
  function renderAll(includeTrend){
    var recs=applyFilters();
    renderKpis(recs);
    renderChips();
    renderStar(recs);
    renderGroupBar("variationChart",recs,"v",state.variations,true);
    renderGroupBar("countryChart",recs,"c",state.countries,false);
    renderVp(recs);
    renderLength(recs);
    renderTheme(recs);
    renderClouds(recs);
    renderAspects();
    renderTable(recs);
    renderTableTools();
  }

  function esc(s){ return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }

  // ---- 初始化 ----
  function init(){
    var t=META.title||"评论分析看板";
    document.getElementById("heroTitle").textContent = (META.brand?META.brand+" · ":"") + t;
    var hr=document.getElementById("heroRight"); var links="";
    if(META.source_url) links+='<a href="'+esc(META.source_url)+'" target="_blank" rel="noopener">🛒 在 Amazon 打开 ↗</a>';
    links+='<a href="index.html">📄 返回竞品分析报告 ↗</a>';
    hr.innerHTML=links;

    // 双口径提示（全局综合 vs 抓取样本，明确告警配额偏置）
    var dual=document.createElement("div"); dual.className="dual";
    var g=META.global_rating||{};
    var gAvg=(g.rating!=null?g.rating:(g.avg!=null?g.avg:null));
    var globalTxt="";
    if(META.global_histogram){
      globalTxt="<b>① 全局综合评分（主口径）：</b>"+
        (gAvg!=null?("综合 "+gAvg+"★"+(META.rating_count?("／"+fmtInt(META.rating_count)+" 评价"):"")+" · "):"")+
        META.global_histogram.map(function(h){return h.star+"★ "+h.percent+"%";}).join(" / ")+
        "（覆盖全部评论，是产品真实口碑分）。";
    } else {
      globalTxt="<b>① 全局综合评分（主口径）：</b>页面未提供，综合分缺失。";
    }
    var scopeTxt = META.scope==="all_variants"
      ? "覆盖 "+META.distinct_asin_count+" 个 ASIN 款式/颜色，共 "+ALL.length+" 条"
      : "共 "+ALL.length+" 条";
    var sampleTxt="<b>② 抓取样本（挖掘口径）：</b>"+scopeTxt+
      "，受抓取星级配额（每星级上限 100 条）系统性放大低星，"+
      "<b>样本均分／低星比不代表产品综合分</b>，仅用于挖掘抱怨主题与真实原话。";
    dual.innerHTML=globalTxt+"<br/>"+sampleTxt;
    document.querySelector(".toolbar").insertAdjacentElement("afterend",dual);

    document.getElementById("resetBtn").onclick=function(){
      state={stars:new Set(),variations:new Set(),countries:new Set(),vp:null,dateRange:null,keyword:null,search:"",aspect:null};
      resetTrendZoom(); renderAll(true);
    };
    var aspBox=document.getElementById("aspectBox");
    if(aspBox) aspBox.addEventListener("click",function(e){
      var b=e.target.closest&&e.target.closest(".asp-issue"); if(!b||b.disabled) return;
      var a=ASP_FLAT[+b.getAttribute("data-asp")]; if(!a) return;
      state.aspect=(state.aspect&&state.aspect.label===a.label)?null:{label:a.label,kws:a.kws,pol:a.pol};
      renderAll(false);
    });
    document.querySelectorAll("table.rv th[data-sort]").forEach(function(th){
      th.onclick=function(){ var k=th.getAttribute("data-sort");
        if(sortKey===k) sortDir*=-1; else {sortKey=k; sortDir=-1;} renderAll(false); };
    });
    bindTableTools();

    renderTrend();
    renderGlobalStar();   // 常量主口径，独立于筛选，仅渲染一次
    renderAll(true);
    window.addEventListener("resize",function(){ for(var k in charts) charts[k].resize(); });
  }
  if(document.readyState!=="loading") init(); else document.addEventListener("DOMContentLoaded",init);
})();
"""


if __name__ == "__main__":
    raise SystemExit(main())
