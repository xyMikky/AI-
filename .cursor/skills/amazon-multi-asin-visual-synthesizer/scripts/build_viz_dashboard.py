# -*- coding: utf-8 -*-
"""
多 ASIN 综合可视化沉淀 · 自包含 HTML 渲染器
================================================
输入一份「数据契约 JSON」(viz_data.json) + 单品三件套所在的 _compare 目录，
跨家归并后渲染一张离线自包含 HTML（内联 ECharts），含 4 图：
  ① 评论痛点强度热力矩阵   ② 市场定位气泡图
  ③ 竞品 × 卖点 关系网络图  ④ Kano 行业级需求聚合
并在顶部输出「竞品基础数据对比」转置表格（行=属性 / 列=竞品，含产品主图 + 跳转竞品报告 / 评论看板 / 简析）。

数据契约由上游 Agent 从各 ASIN 的 visual.json / metadata.json / 评论聚合中抽取后填写，
本脚本不解析 visual.json（结构多变、Kano/痛点派生需判断），只负责把契约渲染成图。
契约字段见 templates/viz_data_template.json。

用法（在工作区根目录执行）：
  python ".cursor/skills/amazon-multi-asin-visual-synthesizer/scripts/build_viz_dashboard.py" \
      --data "生成结果输出/amazon图片提取/_compare_<时间戳>/viz_data.json" \
      --compare-dir "生成结果输出/amazon图片提取/_compare_<时间戳>"

  viz_data.json 与输出 index.html 均直接落在 _compare_<时间戳>/ 根目录（与各 ASIN 子目录平级），
  卡片跳转链接为 "<asin>/index.html" / "<asin>/review_dashboard.html" / "<asin>/brief_analysis.md"。

可选参数：
  --out      输出 HTML 路径（默认 <compare-dir>/index.html）
  --echarts  ECharts 库路径（默认本 skill assets/echarts.min.js）
"""
import os
import io
import sys
import glob
import json
import base64
import argparse
import statistics

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ECHARTS = os.path.join(SKILL_DIR, "assets", "echarts.min.js")

# 报告 / 看板候选文件名（按优先级探测，存在才生成链接）
REPORT_CANDIDATES = ["competitor_analysis.html", "index.html"]
DASHBOARD_CANDIDATES = ["review_dashboard.html"]
BRIEF_CANDIDATES = ["brief_analysis.md"]  # 简析层 ASIN 的轻量分析（无 .html 三件套时回退）

KANO_COLOR = {1: "#e8553b", 2: "#f0a539", 3: "#2fae8f"}
DEFAULT_BAND_LABELS = {1: "基本型 Must-be", 2: "期望型 One-dim", 3: "兴奋型 Attractive"}
SIZE_MIN, SIZE_MAX = 22, 60


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #
def product_thumb(compare_dir, asin, max_px=360, quality=82):
    """取该 ASIN 的 gallery 第一张图，缩略后转 base64 data URI（离线内联）。"""
    hits = sorted(glob.glob(os.path.join(compare_dir, asin, "gallery", "01_*")))
    if not hits:
        hits = sorted(glob.glob(os.path.join(compare_dir, asin, "gallery", "*")))
    if not hits:
        return ""
    try:
        from PIL import Image
        im = Image.open(hits[0]).convert("RGB")
        im.thumbnail((max_px, max_px))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        with open(hits[0], "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def find_link(compare_dir, asin, candidates):
    """在 <compare_dir>/<asin>/ 下找第一个存在的候选文件，返回相对 out（位于 compare 根目录）的链接。"""
    for fn in candidates:
        if os.path.exists(os.path.join(compare_dir, asin, fn)):
            return "%s/%s" % (asin, fn)
    return ""


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def build(data, compare_dir, out_html, echarts_path):
    comps = data["competitors"]
    # 双层竞品模型：detail = 完整三件套（驱动图1-4 严谨口径）；rough = 简析层（仅元数据+评论，进图5/卡片）
    comps_detail = [c for c in comps if c.get("tier", "detail") != "rough"]
    if not comps_detail:
        comps_detail = comps
    n = len(comps)                 # 全部竞品（含简析）→ Hero / 卡片 / 图5
    n_detail = len(comps_detail)   # 仅详细 → 图1-4
    dim_names = data.get("dim_names", [])
    pains = data["pains"]
    pos_kw = data.get("pos_kw", [])
    palette = data.get("palette",
                       ["#e8553b", "#f0a539", "#3fa372", "#3b82c4", "#8b5cf6",
                        "#d6457f", "#1aa7b8", "#9b7b3a", "#6b7280", "#c0392b"])
    palette = (palette * ((n // len(palette)) + 1))[:n]

    out_dir = os.path.dirname(out_html)
    os.makedirs(out_dir, exist_ok=True)

    # 每家主图（base64 内联）+ 报告 / 看板 / 简析链接
    prod_img = {}
    report_link = {}
    dash_link = {}
    brief_link = {}
    for c in comps:
        a = c["asin"]
        prod_img[a] = product_thumb(compare_dir, a)
        report_link[a] = find_link(compare_dir, a, REPORT_CANDIDATES)
        dash_link[a] = find_link(compare_dir, a, DASHBOARD_CANDIDATES)
        brief_link[a] = find_link(compare_dir, a, BRIEF_CANDIDATES)

    # 跨家聚合：好评/差评关键词提及合计（供 Kano Y 轴数据驱动派生）—— 仅详细层，保持口径严谨
    pos_sum = [sum(c.get("pos_matrix", [0] * len(pos_kw))[k] for c in comps_detail)
               for k in range(len(pos_kw))]
    crit_sum = [sum(c["crit"][k] for c in comps_detail) for k in range(len(pains))]

    # ---------------- 图① 痛点强度热力矩阵 ----------------
    heat_data, row_avgs = [], []
    for r, _pain in enumerate(pains):
        vals = []
        for ci, comp in enumerate(comps_detail):
            pct = round(comp["crit"][r] / max(comp["sample"], 1) * 100, 1)
            heat_data.append([ci, r, pct])
            vals.append(pct)
        row_avgs.append(round(sum(vals) / len(vals), 1))
    heat_max = max((v[2] for v in heat_data), default=10)

    # ---------------- 图② 市场定位气泡图 ----------------
    bubble_series = []
    for i, comp in enumerate(comps_detail):
        bubble_series.append({
            "name": comp["name"], "type": "scatter",
            "symbolSize": max(22, (comp["rc"] ** 0.34) / 2.4),
            "itemStyle": {"color": palette[i], "opacity": 0.85,
                          "borderColor": "#fff", "borderWidth": 1.5},
            "label": {"show": True, "formatter": comp["name"], "position": "top",
                      "fontSize": 12, "fontWeight": "bold", "color": "#333"},
            "data": [{"value": [comp["star"], comp["rc"]],
                      "meta": {"bsr": comp.get("bsr", "—"),
                               "total": comp.get("total", "—"), "asin": comp["asin"]}}],
        })
    stars = [c["star"] for c in comps_detail]
    rcs = [c["rc"] for c in comps_detail]
    star_min = min(stars) - 0.1
    star_max = max(stars) + 0.1
    rc_min = max(10 ** (len(str(int(min(rcs)))) - 1), 100)
    rc_max = 10 ** len(str(int(max(rcs))))

    # ---------------- 图③ 竞品 × 卖点 关系网络图 ----------------
    CAT_COMP, CAT_SELL, CAT_GAP, CAT_HUB = 0, 1, 2, 3
    hub_name = data.get("hub_name", "本品机会切入")
    common_sells = data.get("common_sells", [])
    gap_nodes = data.get("gap_nodes", [])
    graph_categories = [
        {"name": "竞品 (%d家)" % n_detail, "itemStyle": {"color": "#3b82c4"}},
        {"name": "共性卖点 · 红海", "itemStyle": {"color": "#e8553b"}},
        {"name": "盲区机会 · 蓝海", "itemStyle": {"color": "#1aa7b8"}},
        {"name": "本品建议切入", "itemStyle": {"color": "#f0a539"}},
    ]
    graph_nodes, graph_links = [], []
    for comp in comps_detail:
        graph_nodes.append({"name": comp["name"], "category": CAT_COMP,
                            "asin": comp["asin"],
                            "symbolSize": round(14 + comp["rc"] ** 0.22),
                            "value": comp["rc"]})
    for s in common_sells:
        graph_nodes.append({"name": s, "category": CAT_SELL, "symbolSize": 26})
        for comp in comps_detail:
            graph_links.append({"source": comp["name"], "target": s})
    if gap_nodes:
        graph_nodes.append({"name": hub_name, "category": CAT_HUB, "symbolSize": 44})
        for g in gap_nodes:
            graph_nodes.append({"name": g, "category": CAT_GAP, "symbolSize": 24})
            graph_links.append({"source": hub_name, "target": g,
                                "lineStyle": {"type": "dashed", "width": 2}})

    # ---------------- 图④ Kano 行业级需求聚合 ----------------
    band_labels = {int(k): v for k, v in
                   data.get("kano_band_labels", DEFAULT_BAND_LABELS).items()}
    p_label = data.get("p_label", ["好评·" + k for k in pos_kw])
    c_label = data.get("c_label", ["差评·" + p for p in pains])
    kano_def = data["kano_def"]

    def raw_and_bd(parts):
        raw, segs = 0.0, []
        for kind, idx, w in parts:
            base = pos_sum[idx] if kind == "p" else crit_sum[idx]
            raw += base * w
            lab = p_label[idx] if kind == "p" else c_label[idx]
            suffix = "×%s" % w if w != 1 else ""
            segs.append("%s%s %d" % (lab, suffix, round(base * w)))
        return raw, (" + ".join(segs) if segs else "无直接关键词")

    raw_max = max((raw_and_bd(d["comps"])[0] for d in kano_def), default=1.0) or 1.0
    Y_LO, Y_HI = 1.5, 9.5
    kano_points = []
    for d in kano_def:
        raw, bd = raw_and_bd(d["comps"])
        y = round(Y_LO + raw / raw_max * (Y_HI - Y_LO), 2)
        kano_points.append({"band": int(d["band"]), "name": d["name"], "y": y,
                            "hit": d["hit"], "raw": round(raw), "bd": bd})

    hits = [p["hit"] for p in kano_points]
    hmin, hmax = min(hits), max(hits)

    def kano_size(hit):
        if hmax == hmin:
            return round((SIZE_MIN + SIZE_MAX) / 2)
        return round(SIZE_MIN + (hit - hmin) / (hmax - hmin) * (SIZE_MAX - SIZE_MIN))

    bands_present = sorted({p["band"] for p in kano_points})
    kano_series = []
    for band in bands_present:
        pts = [p for p in kano_points if p["band"] == band]
        kano_series.append({
            "name": band_labels.get(band, "档位%d" % band), "type": "scatter",
            "itemStyle": {"color": KANO_COLOR.get(band, "#888"), "opacity": 0.85,
                          "borderColor": "#fff", "borderWidth": 1.5},
            "label": {"show": True, "formatter": "{b}", "position": "right",
                      "fontSize": 11, "color": "#333"},
            "data": [{"value": [band + (idx - len(pts) / 2) * 0.06, p["y"]],
                      "name": p["name"], "hit": p["hit"], "raw": p["raw"],
                      "bd": p["bd"], "symbolSize": kano_size(p["hit"])}
                     for idx, p in enumerate(pts)],
        })
    if kano_series:
        kano_series[0]["markArea"] = {
            "silent": True, "itemStyle": {"opacity": 0.07},
            "label": {"show": True, "position": "insideTop", "distance": 10,
                      "color": "#777", "fontSize": 12, "fontWeight": "bold"},
            "data": [[{"xAxis": b - 0.5, "itemStyle": {"color": KANO_COLOR.get(b, "#888")},
                       "name": band_labels.get(b, "档位%d" % b)},
                      {"xAxis": b + 0.5}] for b in bands_present],
        }
    kano_xmin = min(bands_present) - 0.5
    kano_xmax = max(bands_present) + 0.5

    # ---------------- 图⑤ 价格–口碑性价比矩阵（详细 + 简析 全员参与） ----------------
    # 仅依赖 price/star/rc（详细与简析共有数据），是简析层 ASIN 的专属参与角度。
    def _price_of(c):
        p = c.get("price")
        try:
            return float(p)
        except (TypeError, ValueError):
            return None
    priced = [c for c in comps if _price_of(c) is not None]
    value_series = []
    val_price_med = val_star_med = val_xmin = val_xmax = val_ymin = val_ymax = None
    if priced:
        val_price_med = round(statistics.median([_price_of(c) for c in priced]), 2)
        val_star_med = round(statistics.median([float(c["star"]) for c in priced]), 2)

        def _verdict(price, star):
            hi_p, hi_s = price >= val_price_med, star >= val_star_med
            if not hi_p and hi_s:
                return "性价比甜区（低价高口碑）"
            if hi_p and hi_s:
                return "溢价品质（高价高口碑）"
            if not hi_p and not hi_s:
                return "低质走量（低价低口碑）"
            return "危险区（高价低口碑）"

        for i, c in enumerate(comps):
            price = _price_of(c)
            if price is None:
                continue
            star = float(c["star"])
            is_rough = c.get("tier", "detail") == "rough"
            value_series.append({
                "name": c["name"], "type": "scatter",
                "symbol": "diamond" if is_rough else "circle",
                "symbolSize": max(20, (c["rc"] ** 0.32) / 2.6),
                "itemStyle": {"color": palette[i % len(palette)], "opacity": 0.85,
                              "borderColor": "#c0392b" if is_rough else "#fff",
                              "borderType": "dashed" if is_rough else "solid",
                              "borderWidth": 2 if is_rough else 1.5},
                "label": {"show": True, "position": "top", "fontSize": 11,
                          "fontWeight": "bold", "color": "#333",
                          "formatter": c["name"] + ("（简析）" if is_rough else "")},
                "data": [{"value": [round(price, 2), star],
                          "meta": {"rc": c["rc"], "bsr": c.get("bsr", "—"),
                                   "asin": c["asin"],
                                   "tier": "简析" if is_rough else "详细",
                                   "verdict": _verdict(price, star)}}],
            })
        _vp = [_price_of(c) for c in priced]
        _vs = [float(c["star"]) for c in priced]
        val_xmin = max(0, int(min(_vp) // 5) * 5 - 2)
        val_xmax = int(max(_vp) // 5) * 5 + 7
        val_ymin = round(min(_vs) - 0.15, 1)
        val_ymax = round(max(_vs) + 0.15, 1)
        if value_series:
            value_series[0]["markLine"] = {
                "silent": True, "symbol": "none",
                "lineStyle": {"type": "dashed", "color": "#bbb"},
                "label": {"show": True, "color": "#999", "fontSize": 11},
                "data": [{"xAxis": val_price_med, "name": "价格中位 $%s" % val_price_med},
                         {"yAxis": val_star_med, "name": "口碑中位 %s★" % val_star_med}],
            }
            value_series[0]["markArea"] = {
                "silent": True,
                "label": {"show": True, "color": "#9a9a9a", "fontSize": 12,
                          "fontWeight": "bold", "position": "inside"},
                "data": [
                    [{"name": "性价比甜区", "coord": [val_xmin, val_star_med],
                      "itemStyle": {"color": "rgba(47,174,143,0.08)"}},
                     {"coord": [val_price_med, val_ymax]}],
                    [{"name": "溢价品质", "coord": [val_price_med, val_star_med],
                      "itemStyle": {"color": "rgba(59,130,196,0.07)"}},
                     {"coord": [val_xmax, val_ymax]}],
                    [{"name": "低质走量", "coord": [val_xmin, val_ymin],
                      "itemStyle": {"color": "rgba(240,165,57,0.07)"}},
                     {"coord": [val_price_med, val_star_med]}],
                    [{"name": "危险区", "coord": [val_price_med, val_ymin],
                      "itemStyle": {"color": "rgba(232,85,59,0.08)"}},
                     {"coord": [val_xmax, val_star_med]}],
                ],
            }

    # ---------------- 图⑥ 流量入口结构对比（详细层 · traffic_mix） ----------------
    TM_KEYS = [("nat", "自然搜索", "#2fae8f"), ("sp", "SP广告", "#3b82c4"),
               ("sb", "品牌广告", "#8b5cf6"), ("sbv", "视频广告", "#d6457f"),
               ("rec", "推荐位", "#f0a539")]
    comps_tm = [c for c in comps_detail if isinstance(c.get("traffic_mix"), dict)]
    tm_cats = [c["name"] for c in comps_tm]
    tm_series = []
    if comps_tm:
        for key, label, color in TM_KEYS:
            row = []
            for c in comps_tm:
                mix = c["traffic_mix"]
                tot = sum(max(0.0, float(mix.get(k, 0) or 0)) for k, _, _ in TM_KEYS) or 1.0
                row.append(round(max(0.0, float(mix.get(key, 0) or 0)) / tot * 100, 2))
            tm_series.append({"name": label, "type": "bar", "stack": "mix",
                              "itemStyle": {"color": color}, "emphasis": {"focus": "series"},
                              "barWidth": "55%", "data": row})

    # ---------------- 图⑦ 关键词架构矩阵（详细层 · kw_arch） ----------------
    comps_ka = [c for c in comps_detail if isinstance(c.get("kw_arch"), dict)]
    ka_series = []
    if comps_ka:
        for i, c in enumerate(comps_ka):
            ka = c["kw_arch"]
            org = round(float(ka.get("organic_share", 0) or 0) * 100, 1)
            tot_kw = int(float(ka.get("total_kw", 0) or 0))
            sv = float(ka.get("top_kw_sv", 0) or 0)
            ka_series.append({
                "name": c["name"], "type": "scatter",
                "symbolSize": max(18, round(sv ** 0.28)),
                "itemStyle": {"color": palette[i % len(palette)], "opacity": 0.85,
                              "borderColor": "#fff", "borderWidth": 1.5},
                "label": {"show": True, "formatter": c["name"], "position": "top",
                          "fontSize": 11, "fontWeight": "bold", "color": "#333"},
                "data": [{"value": [org, tot_kw],
                          "meta": {"asin": c["asin"], "top_kw_sv": int(sv),
                                   "organic": org, "total_kw": tot_kw}}],
            })
        ka_orgs = [float(c["kw_arch"].get("organic_share", 0) or 0) * 100 for c in comps_ka]
        ka_tots = [int(float(c["kw_arch"].get("total_kw", 0) or 0)) for c in comps_ka]
        ka_xmin = max(0, min(ka_orgs) - 8)
        ka_xmax = min(100, max(ka_orgs) + 8)
        ka_ymax = max(ka_tots) * 1.15 + 1
        if ka_series:
            ka_series[0]["markLine"] = {
                "silent": True, "symbol": "none",
                "lineStyle": {"type": "dashed", "color": "#bbb"},
                "label": {"show": True, "formatter": "自然/广告驱动分界", "color": "#999", "fontSize": 11},
                "data": [{"xAxis": 50}],
            }

    # ---------------- 顶部摘要 ----------------
    category = data.get("category", "")
    if data.get("summary_cards"):
        summary_cards = [tuple(s) for s in data["summary_cards"]]
    else:
        leader = max(comps, key=lambda c: c["rc"])
        universal_pain = pains[row_avgs.index(max(row_avgs))]
        summary_cards = [
            ("🧩", "竞品数 / 品类", "%d 家 · %s" % (n, category)),
            ("🥇", "市场龙头", "%s · %s 评价 · BSR #%s"
             % (leader["name"], format(leader["rc"], ","), leader.get("bsr", "—"))),
            ("⭐", "行业口碑带", "%.1f – %.1f ★" % (min(stars), max(stars))),
            ("🎯", "全行业共同盲区", "%s（整行最红）" % universal_pain),
        ]

    charts = {
        "heat": {
            "title": "评论痛点强度热力矩阵",
            "sub": "差评命中 / 样本占比%（行=痛点，列=竞品）",
            "read": "整<b>行</b>偏红 = 全行业共同盲区（谁都没解决，本品机会）；整<b>列</b>偏红 = 该竞品问题集中。",
            "h": max(320, 60 + len(pains) * 48),
        },
        "bubble": {
            "title": "市场定位气泡图",
            "sub": "X=全局星级（口碑） · Y=评价数对数（市场体量） · 气泡大小=评价数",
            "read": "右上=高口碑高体量龙头；左下=口碑与体量都弱的位置。"
                    "价格字段缺失时用“口碑×体量”定位，待有价格可无缝换 X 轴。",
            "h": 420,
        },
        "graph": {
            "title": "竞品 × 卖点 关系网络图",
            "sub": "力导向二部网络 · 蓝=竞品 / 红=共性卖点(红海) / 青=盲区机会(蓝海) / 橙=本品切入",
            "read": "竞品全部连向同一组红色卖点 → 红海高度同质；青色盲区节点挂在橙色“本品建议切入”簇上、"
                    "几乎无竞品连线 → 蓝海差异化空间。节点可拖拽，重叠标签自动隐藏，悬停查看。",
            "h": 540,
        },
        "kano": {
            "title": "Kano 行业级需求聚合",
            "sub": "由 %d 家详细评论好评/差评派生 · 气泡大小=命中竞品家数" % n_detail,
            "read": "横向三分区=Kano 类别（非数值轴），纵轴=信号强度（由各家相关评论关键词提及量聚合归一到"
                    " 1.5–9.5，<b>悬停看构成明细可溯源</b>），气泡大小=命中家数。"
                    "基本型(红)：缺失即差评，必须先保命；期望型(黄)：越做越拉分；兴奋型(绿)：超预期爆点。",
            "h": 460,
        },
    }
    if value_series:
        charts["value"] = {
            "title": "价格–口碑性价比矩阵（含简析层）",
            "sub": "X=价格 $ · Y=全局星级 · 气泡大小=评价数（体量）· 菱形虚边=简析层 ASIN",
            "read": "以价格中位 / 口碑中位切四象限：左上<b>性价比甜区</b>（低价高口碑）、右上<b>溢价品质</b>、"
                    "左下<b>低质走量</b>、右下<b>危险区</b>（高价低口碑）。"
                    "简析款（菱形）撑开了价格跨度，本品可据此找定价空位。",
            "h": 460,
        }
    if tm_series:
        charts["trafficmix"] = {
            "title": "流量入口结构对比（详细层）",
            "sub": "各竞品曝光来源 100% 占比 · 自然搜索 / SP / 品牌 / 视频 / 推荐位（数据源 SIF asinSummary）",
            "read": "整条偏绿=<b>自然流量主导</b>（口碑型，抗广告波动）；偏蓝紫=<b>广告驱动</b>（停投即掉量）。"
                    "对比可看出红海里谁靠自然吃饭、谁在烧广告，定位本品的流量打法。",
            "h": max(300, 80 + len(tm_cats) * 42),
        }
    if ka_series:
        charts["kwarch"] = {
            "title": "关键词架构矩阵（详细层）",
            "sub": "X=自然流量占比% · Y=流量词总数 · 气泡大小=头部词周搜索量（数据源 SIF asinKeywords/asinSummary）",
            "read": "右侧=<b>自然驱动</b>、左侧=<b>广告驱动</b>（50% 虚线为界）；越靠上=<b>词库越宽</b>。"
                    "右上=自然且词广（健康），左下=词窄且靠广告（脆弱），据此判断本品关键词布局方向。",
            "h": 460,
        }

    options = {
        "heat": {
            "tooltip": {"position": "top"},
            "grid": {"left": 120, "right": 30, "top": 30, "bottom": 70},
            "xAxis": {"type": "category", "data": [c["name"] for c in comps_detail],
                      "splitArea": {"show": True},
                      "axisLabel": {"fontSize": 12, "fontWeight": "bold"}},
            "yAxis": {"type": "category", "data": pains, "splitArea": {"show": True},
                      "axisLabel": {"fontSize": 11}},
            "visualMap": {"min": 0, "max": round(heat_max), "calculable": True,
                          "orient": "horizontal", "left": "center", "bottom": 8,
                          "inRange": {"color": ["#2fae8f", "#fbe7a2", "#e8553b"]},
                          "text": ["高发(红)", "低发(绿)"]},
            "series": [{"name": "差评占比%", "type": "heatmap", "data": heat_data,
                        "label": {"show": True, "formatter": "{@[2]}%", "fontSize": 11},
                        "emphasis": {"itemStyle": {"shadowBlur": 10,
                                     "shadowColor": "rgba(0,0,0,0.4)"}}}],
        },
        "bubble": {
            "tooltip": {},
            "grid": {"left": 70, "right": 40, "top": 30, "bottom": 60},
            "xAxis": {"type": "value", "name": "全局星级 ★",
                      "min": round(star_min, 1), "max": round(star_max, 1),
                      "nameLocation": "middle", "nameGap": 32,
                      "splitLine": {"lineStyle": {"type": "dashed"}}},
            "yAxis": {"type": "log", "name": "评价数（对数）", "min": rc_min, "max": rc_max,
                      "nameLocation": "middle", "nameGap": 50},
            "series": bubble_series,
        },
        "graph": {
            "tooltip": {},
            "legend": [{"data": [c["name"] for c in graph_categories], "top": 6}],
            "series": [{"type": "graph", "layout": "force", "roam": True,
                        "draggable": True, "categories": graph_categories, "top": 44,
                        "label": {"show": True, "position": "right", "fontSize": 11},
                        "labelLayout": {"hideOverlap": True, "moveOverlap": "shiftY"},
                        "force": {"repulsion": 620, "edgeLength": [80, 180],
                                  "gravity": 0.06, "friction": 0.12},
                        "lineStyle": {"color": "source", "opacity": 0.4,
                                      "width": 1.1, "curveness": 0.08},
                        "emphasis": {"focus": "adjacency", "label": {"show": True},
                                     "lineStyle": {"width": 3}},
                        "data": graph_nodes, "links": graph_links}],
        },
        "kano": {
            "tooltip": {},
            "legend": {"data": [s["name"] for s in kano_series], "top": 6},
            "grid": {"left": 50, "right": 160, "top": 64, "bottom": 50},
            "xAxis": {"type": "value", "min": kano_xmin, "max": kano_xmax,
                      "axisLabel": {"show": False}, "axisTick": {"show": False},
                      "axisLine": {"show": False}, "splitLine": {"show": False}},
            "yAxis": {"type": "value", "name": "行业信号强度", "min": 0, "max": 12,
                      "nameLocation": "middle", "nameGap": 32,
                      "axisLabel": {"formatter": "{value}"}},
            "series": kano_series,
        },
    }
    if value_series:
        options["value"] = {
            "tooltip": {},
            "grid": {"left": 70, "right": 40, "top": 30, "bottom": 60},
            "xAxis": {"type": "value", "name": "价格 $", "min": val_xmin, "max": val_xmax,
                      "nameLocation": "middle", "nameGap": 32,
                      "splitLine": {"lineStyle": {"type": "dashed"}}},
            "yAxis": {"type": "value", "name": "全局星级 ★", "min": val_ymin, "max": val_ymax,
                      "nameLocation": "middle", "nameGap": 40,
                      "splitLine": {"lineStyle": {"type": "dashed"}}},
            "series": value_series,
        }
    if tm_series:
        options["trafficmix"] = {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"top": 6, "data": [s["name"] for s in tm_series]},
            "grid": {"left": 90, "right": 40, "top": 44, "bottom": 40},
            "xAxis": {"type": "value", "max": 100, "axisLabel": {"formatter": "{value}%"}},
            "yAxis": {"type": "category", "data": tm_cats, "inverse": True,
                      "axisLabel": {"fontSize": 12, "fontWeight": "bold"}},
            "series": tm_series,
        }
    if ka_series:
        options["kwarch"] = {
            "tooltip": {},
            "grid": {"left": 70, "right": 40, "top": 30, "bottom": 56},
            "xAxis": {"type": "value", "name": "自然流量占比 %", "min": ka_xmin, "max": ka_xmax,
                      "nameLocation": "middle", "nameGap": 32,
                      "splitLine": {"lineStyle": {"type": "dashed"}}},
            "yAxis": {"type": "value", "name": "流量词总数", "min": 0, "max": ka_ymax,
                      "nameLocation": "middle", "nameGap": 52,
                      "splitLine": {"lineStyle": {"type": "dashed"}}},
            "series": ka_series,
        }

    # ---------------- 组装 HTML ----------------
    with open(echarts_path, "r", encoding="utf-8") as f:
        echarts_js = f.read()

    cards_html = "".join(
        '<div class="kpi"><div class="kpi-ic">%s</div>'
        '<div class="kpi-l">%s</div><div class="kpi-v">%s</div></div>' % (ic, lb, vl)
        for ic, lb, vl in summary_cards)

    chart_blocks = ""
    for key, meta in charts.items():
        chart_blocks += '''
    <section class="card">
      <div class="card-h"><h2>%s</h2><span class="sub">%s</span></div>
      <div class="chart" id="chart_%s" style="height:%dpx"></div>
      <p class="read"><b>怎么读：</b>%s</p>
    </section>''' % (meta["title"], meta["sub"], key, meta["h"], meta["read"])

    opt_js = ";\n".join(
        'echarts.init(document.getElementById("chart_%s")).setOption(%s)'
        % (k, json.dumps(options[k], ensure_ascii=False)) for k in options)

    extra_js = '''
    (function(){
      function prodImg(asin){ var u = (window.PROD_IMG||{})[asin];
        return u ? '<img src="'+u+'" style="width:150px;height:150px;object-fit:contain;display:block;margin:4px auto 6px;border:1px solid #eee;border-radius:6px;background:#fff"/>' : ''; }
      var bc = echarts.getInstanceByDom(document.getElementById("chart_bubble"));
      if(bc){ bc.setOption({tooltip:{formatter:function(p){var m=p.data.meta||{};
        return "<b>"+p.seriesName+"</b>"+prodImg(m.asin)+"全局星级："+p.value[0]+" ★<br/>评价数："+p.value[1].toLocaleString()
        +"<br/>类目 BSR：#"+m.bsr+"<br/>页面加权总分："+m.total+" / 5";}}}); }
      var gc = echarts.getInstanceByDom(document.getElementById("chart_graph"));
      if(gc){ gc.setOption({tooltip:{formatter:function(p){
        if(p.dataType==="edge"){return p.data.source+" → "+p.data.target;}
        return "<b>"+p.data.name+"</b>"+prodImg(p.data.asin)+(p.data.value?"评价数："+p.data.value.toLocaleString():"");}}}); }
      var kc = echarts.getInstanceByDom(document.getElementById("chart_kano"));
      if(kc){ kc.setOption({tooltip:{formatter:function(p){
        return "<b>"+p.data.name+"</b><br/>类别："+p.seriesName+"<br/>命中竞品："+p.data.hit+" 家"
        +"<br/>信号强度（各家提及合计）："+p.data.raw+"<br/>构成："+p.data.bd
        +"<br/>归一高度："+p.value[1];}}}); }
      var vc = echarts.getInstanceByDom(document.getElementById("chart_value"));
      if(vc){ vc.setOption({tooltip:{formatter:function(p){
        if(!p.data||p.data.value===undefined){return p.name||"";}
        var m=p.data.meta||{};
        return "<b>"+p.seriesName+"</b>"+prodImg(m.asin)+"价格：$"+p.value[0]
        +"<br/>全局星级："+p.value[1]+" ★<br/>评价数："+(m.rc?m.rc.toLocaleString():"—")
        +"<br/>类目 BSR：#"+m.bsr+"<br/>层级："+m.tier+"<br/>性价比定位："+m.verdict;}}}); }
      var tmc = echarts.getInstanceByDom(document.getElementById("chart_trafficmix"));
      if(tmc){ tmc.setOption({tooltip:{trigger:"axis",axisPointer:{type:"shadow"},formatter:function(ps){
        if(!ps||!ps.length)return"";var s="<b>"+ps[0].axisValue+"</b>";
        ps.forEach(function(p){s+="<br/>"+p.marker+p.seriesName+"："+(p.value||0).toFixed(1)+"%";});return s;}}}); }
      var kac = echarts.getInstanceByDom(document.getElementById("chart_kwarch"));
      if(kac){ kac.setOption({tooltip:{formatter:function(p){
        if(!p.data||p.data.value===undefined){return p.name||"";}
        var m=p.data.meta||{};
        return "<b>"+p.seriesName+"</b>"+prodImg(m.asin)+"自然流量占比："+m.organic+"%"
        +"<br/>流量词总数："+(m.total_kw?m.total_kw.toLocaleString():"—")
        +"<br/>头部词周搜索量："+(m.top_kw_sv?m.top_kw_sv.toLocaleString():"—");}}}); }
      window.addEventListener("resize",function(){
        ["heat","bubble","graph","kano","value","trafficmix","kwarch"].forEach(function(k){
          var el=document.getElementById("chart_"+k); if(!el)return;
          var c=echarts.getInstanceByDom(el); if(c)c.resize();});
      });
    })();'''

    def card_links(c):
        a = c["asin"]
        rl, dl, bl = report_link[a], dash_link[a], brief_link[a]
        out = "<div class='plinks'>"
        if rl:
            out += "<a class='lnk lnk-r' href='%s' target='_blank'>竞品报告</a>" % rl
        elif bl:
            out += "<a class='lnk lnk-b' href='%s' target='_blank'>简析报告</a>" % bl
        if dl:
            out += "<a class='lnk lnk-d' href='%s' target='_blank'>评论看板</a>" % dl
        out += "</div>"
        return out if (rl or bl or dl) else ""

    def card_img(c):
        a = c["asin"]
        link = report_link[a] or brief_link[a]
        img = "<img src='%s'/>" % prod_img.get(a, "")
        if link:
            return "<a href='%s' target='_blank' title='打开分析报告'>%s</a>" % (link, img)
        return img

    def is_rough(c):
        return c.get("tier", "detail") == "rough"

    # ---------------- 竞品基础数据对比表格（转置：行=属性，列=竞品） ----------------
    # 通用商业属性行（key, 显示标签, 顶层回退键）：basics 优先，缺失回退顶层字段
    UNIVERSAL_ROWS = [
        ("rating",         "星级评分", "star"),
        ("rating_count",   "评价数",   "rc"),
        ("bsr",            "类目 BSR", "bsr"),
        ("deal_price",     "现价",     "price"),
        ("list_price",     "原价",     None),
        ("discount_pct",   "折扣力度", None),
        ("monthly_sales",  "月销量",   None),
        ("launch_date",    "上架时间", None),
        ("color_variants", "颜色变体", None),
        ("size_variants",  "尺寸变体", None),
    ]

    def basics_val(c, key, fallback):
        b = c.get("basics", {}) or {}
        if key in b and b[key] not in (None, "", "—"):
            return b[key]
        if fallback and c.get(fallback) not in (None, "", "—"):
            return c.get(fallback)
        return None

    def fmt_cell(key, v):
        if v in (None, "", "—"):
            return None
        try:
            if key == "rating":
                return "%s ★" % v
            if key == "rating_count":
                return "{:,}".format(int(v))
            if key == "bsr":
                return "#%s" % v
            if key in ("deal_price", "list_price"):
                return "$%.2f" % float(v)
            if key == "discount_pct":
                iv = float(v)
                return None if iv <= 0 else ("-%g" % iv) + "%"
            if key == "color_variants":
                return ("%s 色" % v) if int(v) > 0 else None
            if key == "size_variants":
                return ("%s 款" % v) if int(v) > 0 else None
        except Exception:
            pass
        return str(v)

    def comp_table_row(label, cells):
        tds = "".join(
            ("<td>%s</td>" % x) if x is not None else "<td class='na'>—</td>"
            for x in cells)
        return "<tr><th class='rowhead'>%s</th>%s</tr>" % (label, tds)

    head_cells = "".join(
        "<th class='col-head%s'>%s%s<div class='ch-brand'>%s</div>"
        "<div class='ch-asin'>%s</div>%s</th>"
        % (" rough" if is_rough(c) else "",
           "<span class='tier-badge'>简析</span>" if is_rough(c) else "",
           card_img(c), c["name"], c["asin"], card_links(c))
        for c in comps)
    head_html = "<tr><th class='corner'>竞品</th>%s</tr>" % head_cells

    body_rows = []
    for key, label, fb in UNIVERSAL_ROWS:
        cells = [fmt_cell(key, basics_val(c, key, fb)) for c in comps]
        if any(x is not None for x in cells):
            body_rows.append(comp_table_row(label, cells))
    for row in data.get("basics_rows", []):
        key, label = row.get("key"), row.get("label", row.get("key"))
        if not key:
            continue
        cells = [fmt_cell(key, (c.get("basics", {}) or {}).get(key)) for c in comps]
        if any(x is not None for x in cells):
            body_rows.append(comp_table_row(label, cells))

    comp_table_html = ("<div class='comp-table-wrap'><table class='comp-table'>"
                       "<thead>%s</thead><tbody>%s</tbody></table></div>"
                       % (head_html, "".join(body_rows)))

    prod_img_js = "var PROD_IMG = " + json.dumps(prod_img, ensure_ascii=False) + ";"
    title = data.get("title", "多 ASIN 综合分析 · 可视化沉淀")
    source_name = os.path.basename(os.path.normpath(compare_dir))

    html = '''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;
        background:#f4f5f7;color:#222;line-height:1.6}
  .wrap{max-width:1080px;margin:0 auto;padding:28px 20px 60px}
  header.hero{background:linear-gradient(120deg,#c0392b,#7d1f15);color:#fff;
        border-radius:16px;padding:26px 30px;box-shadow:0 6px 24px rgba(150,30,20,.25)}
  header.hero h1{margin:0 0 6px;font-size:24px}
  header.hero p{margin:0;opacity:.9;font-size:14px}
  .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0 26px}
  .kpi{background:#fff;border-radius:12px;padding:14px 16px;box-shadow:0 2px 10px rgba(0,0,0,.05)}
  .kpi-ic{font-size:20px}
  .kpi-l{font-size:12px;color:#888;margin-top:4px}
  .kpi-v{font-size:15px;font-weight:700;margin-top:2px;color:#c0392b}
  .card{background:#fff;border-radius:14px;padding:20px 22px;margin-bottom:22px;
        box-shadow:0 2px 12px rgba(0,0,0,.06)}
  .card-h{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;
        border-left:4px solid #c0392b;padding-left:12px;margin-bottom:8px}
  .card-h h2{margin:0;font-size:18px}
  .card-h .sub{color:#888;font-size:13px}
  .read{background:#fbf3f1;border:1px solid #f0d9d4;border-radius:8px;
        padding:9px 13px;font-size:13px;color:#5a4340;margin:8px 0 0}
  .read b{color:#c0392b}
  .comp-table-wrap{overflow-x:auto;padding:2px 0 6px}
  .comp-table{border-collapse:separate;border-spacing:0;font-size:12.5px;min-width:100%%}
  .comp-table th,.comp-table td{border-bottom:1px solid #eee;border-right:1px solid #f2f2f2;
        padding:8px 10px;text-align:center;white-space:nowrap}
  .comp-table thead th{background:#fbf3f1;vertical-align:top;border-bottom:2px solid #e6b3ab;min-width:132px}
  .comp-table thead th.col-head.rough{background:#fff6f3}
  .comp-table .rowhead{position:sticky;left:0;z-index:3;background:#faf7f6;text-align:left;
        font-weight:700;color:#5a4340;border-right:2px solid #e6b3ab}
  .comp-table thead th.corner{position:sticky;left:0;z-index:5;background:#f3e4e0;color:#5a4340;font-weight:700}
  .comp-table tbody tr:nth-child(even) td{background:#fcfcfc}
  .comp-table tbody tr:hover td{background:#fbf3f1}
  .comp-table th img{width:74px;height:74px;object-fit:contain;background:#fff;border-radius:6px;
        cursor:pointer;display:block;margin:0 auto 6px;transition:transform .15s}
  .comp-table th img:hover{transform:scale(1.06)}
  .comp-table .ch-brand{font-weight:700;color:#c0392b;font-size:13px}
  .comp-table .ch-asin{font-size:10px;color:#bbb;letter-spacing:.3px;margin-bottom:5px}
  .comp-table td.na{color:#ccc}
  .tier-badge{display:inline-block;background:#c0392b;color:#fff;font-size:10px;
        padding:2px 7px;border-radius:8px;font-weight:700;letter-spacing:.5px;margin-bottom:5px}
  .comp-table .plinks{flex-direction:column;gap:4px;margin-top:2px}
  .comp-table .plinks .lnk{font-size:10px;padding:3px 4px}
  .plinks{display:flex;gap:6px;margin-top:10px}
  .lnk{flex:1;font-size:11px;padding:5px 4px;border-radius:6px;text-decoration:none;
        border:1px solid;transition:.15s;white-space:nowrap}
  .lnk-r{color:#c0392b;border-color:#e6b3ab}
  .lnk-r:hover{background:#c0392b;color:#fff}
  .lnk-d{color:#2563a8;border-color:#a9c6e6}
  .lnk-d:hover{background:#2563a8;color:#fff}
  .lnk-b{color:#b06a00;border-color:#e6c9a0}
  .lnk-b:hover{background:#b06a00;color:#fff}
  footer.note{font-size:12px;color:#999;background:#fff;border-radius:12px;
        padding:16px 20px;margin-top:6px;box-shadow:0 2px 10px rgba(0,0,0,.04)}
  footer.note b{color:#666}
  @media(max-width:720px){.kpis{grid-template-columns:repeat(2,1fr)}}
</style></head>
<body><div class="wrap">
  <header class="hero">
    <h1>%s</h1>
    <p>%s · %d 个竞品 · 数据源自 %s 单品三件套</p>
  </header>
  <div class="kpis">%s</div>
  <section class="card">
    <div class="card-h"><h2>竞品基础数据对比</h2><span class="sub">行=属性 · 列=竞品（左列属性固定，横向滚动看全部竞品；点击产品图或按钮跳转竞品报告 / 评论看板 / 简析）</span></div>
    %s
  </section>
  %s
  <footer class="note">
    <b>数据适配说明：</b>① “市场定位气泡图”以<b>全局星级 × 评价数（体量）</b>定位；“价格–口碑性价比矩阵”已用各家<b>真实价格</b>切四象限；
    ② “Kano 行业聚合”的纵轴信号强度由各家相关评论关键词提及量按规则聚合后归一到 1.5–9.5
    （基本型=差评量 / 兴奋型=好评量 / 期望型=两者合计），悬停可见每个气泡的构成明细，可溯源到具体评论计数；
    ③ 热力矩阵用“差评命中 / 样本占比%%”，已按各家样本量归一，规避绝对数因样本不同造成的误读；
    ④ 关系网络图中各家“卖家强调卖点”被归一为同一组，故红海连线高度重合，恰好印证品类同质化；
    ⑤ <b>双层竞品</b>：图1-4 与 Kano 仅取<b>详细层</b>（完整三件套 + 六维评分）保持口径严谨；<b>简析层 ASIN</b>（菱形虚边 · 仅评论与元数据、无六维页面评分）仅参与“价格–口碑性价比矩阵”与顶部卡片，作为价格带与口碑分布的补充参照。<br/>
    本页完全离线自包含（内联 ECharts），双击即可打开，可整体转发。
  </footer>
</div>
<script>%s</script>
<script>%s</script>
<script>%s;%s</script>
</body></html>''' % (title, title, category, n, source_name, cards_html,
                     comp_table_html, chart_blocks, echarts_js, prod_img_js, opt_js, extra_js)

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK ->", out_html)
    print("competitors:", n, "| echarts bytes:", len(echarts_js))


def main():
    ap = argparse.ArgumentParser(description="多 ASIN 综合可视化沉淀 HTML 渲染器")
    ap.add_argument("--data", required=True, help="数据契约 viz_data.json 路径")
    ap.add_argument("--compare-dir", default=None,
                    help="单品三件套 _compare 目录（默认取 data 文件的上两级目录）")
    ap.add_argument("--out", default=None, help="输出 HTML 路径")
    ap.add_argument("--echarts", default=DEFAULT_ECHARTS, help="ECharts 库路径")
    args = ap.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    if args.compare_dir:
        compare_dir = os.path.abspath(args.compare_dir)
    else:
        # 默认：data(viz_data.json) 位于 <compare>/ 根目录
        compare_dir = os.path.dirname(os.path.abspath(args.data))

    if args.out:
        out_html = os.path.abspath(args.out)
    else:
        out_html = os.path.join(compare_dir, "index.html")

    if not os.path.exists(args.echarts):
        sys.exit("ECharts 库未找到：%s" % args.echarts)

    build(data, compare_dir, out_html, args.echarts)


if __name__ == "__main__":
    main()
