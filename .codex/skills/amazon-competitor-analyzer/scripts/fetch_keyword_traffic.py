# -*- coding: utf-8 -*-
"""
关键词架构 + 流量入口 采集器（阶段 ②.8）
============================================
调用已安装的 LinkFox SIF skill，按 ASIN 取「关键词架构」与「流量入口结构」两类数据，
归一化为每个 ASIN 目录下的 keyword_arch.json + traffic_source.json，
并在 compare 根目录汇总一份 kw_traffic_index.json（供综合看板 viz_data 回填）。

依赖（须已安装且配置 LINKFOXAGENT_API_KEY）：
- linkfox-sif-asin-keywords/scripts/sif_asin_keywords.py   → /sif/asinKeywords（单 ASIN）
- linkfox-sif-asin-summary/scripts/sif_asin_summary.py     → /sif/asinSummary（批量 ≤10 ASIN）

用法（工作区根目录执行）：
  # 单 ASIN
  python .codex/skills/amazon-competitor-analyzer/scripts/fetch_keyword_traffic.py \
      --asin B0XXXXXXXX --outdir "<阶段①输出目录>" --country US
  # 批量（自动发现 _compare 目录下的 ASIN 子目录，或用 --asins 指定）
  python .codex/skills/amazon-competitor-analyzer/scripts/fetch_keyword_traffic.py \
      --compare-dir "生成结果输出/amazon图片提取/_compare_<时间戳>" --country US

无 LINKFOXAGENT_API_KEY 或接口失败时：打印告警并跳过该 ASIN，不抛错（不阻塞主链路）。
"""
import os
import re
import sys
import json
import argparse
import subprocess

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SKILLS_DIR = os.path.abspath(os.path.join(SKILL_DIR, ".."))
LEGACY_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))



def skill_roots():
    roots = [
        SKILLS_DIR,
        os.path.join(os.environ.get("CODEX_HOME", ""), "skills") if os.environ.get("CODEX_HOME") else "",
        os.path.join(os.path.expanduser("~"), ".codex", "skills"),
        os.path.join(os.getcwd(), ".codex", "skills"),
        os.path.join(LEGACY_ROOT, ".codex", "skills"),
    ]
    seen = set()
    out = []
    for root in roots:
        if not root:
            continue
        root = os.path.abspath(root)
        if root in seen:
            continue
        seen.add(root)
        out.append(root)
    return out


def find_skill_script(skill_name, rel_script):
    for root in skill_roots():
        candidate = os.path.join(root, skill_name, rel_script)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(SKILLS_DIR, skill_name, rel_script)


KW_SCRIPT = find_skill_script("linkfox-sif-asin-keywords", os.path.join("scripts", "sif_asin_keywords.py"))
SUM_SCRIPT = find_skill_script("linkfox-sif-asin-summary", os.path.join("scripts", "sif_asin_summary.py"))

POS_ZH = {
    "natural": "自然位", "ac": "AC推荐", "sp": "SP广告", "top": "顶部品牌广告",
    "bottom": "底部品牌广告", "er": "编辑推荐", "vedio": "视频广告",
    "tr": "高评分推荐", "trfob": "高频购买推荐", "rec": "推荐位",
}
MARK_ZH = {
    "isMainKw": "主词", "isAccurateKw": "精准词", "isAccurateAboveKw": "精准大词",
    "isAccurateTailKw": "长尾词", "isPurchaseKw": "出单词", "isQualityKw": "优质转化",
    "isStableKw": "平稳转化", "isLossKw": "转化流失", "isInvalidKw": "无效曝光",
}


def run_skill(script, params):
    """调用 LinkFox skill 脚本，返回解析后的 dict；失败返回 {'error':...}。"""
    if not os.path.exists(script):
        return {"error": "script not found: %s" % script}
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run([sys.executable, script, json.dumps(params)],
                           capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
    except Exception as e:
        return {"error": "subprocess failed: %s" % e}
    out = (r.stdout or "").lstrip("\ufeff").strip()
    if not out:
        return {"error": "empty output; stderr=%s" % (r.stderr or "")[-300:]}
    try:
        return json.loads(out)
    except Exception as e:
        return {"error": "json parse failed: %s; head=%s" % (e, out[:200])}


def _num(x, default=0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def build_keyword_arch(asin, country, top_n=15):
    """调 asinKeywords，归一化关键词架构。"""
    res = run_skill(KW_SCRIPT, {"asin": asin, "country": country,
                                "sortBy": "estSearchesNum", "desc": True, "pageSize": 100})
    if res.get("error") or res.get("errcode") not in (None, 200, "200"):
        return None, res.get("error") or res.get("errmsg") or ("errcode=%s" % res.get("errcode"))
    rows = res.get("data") or []
    if not rows:
        return None, "no keyword data"
    # 按流量占比排序取 Top N 进表
    rows_sorted = sorted(rows, key=lambda d: _num(d.get("trafficShare")), reverse=True)
    top = []
    for d in rows_sorted[:top_n]:
        pos = [POS_ZH.get(p, p) for p in (d.get("displayPositionTypes") or [])]
        mk = [MARK_ZH.get(m, m) for m in (d.get("trafficCharacteristicMarkers") or [])]
        top.append({
            "kw": d.get("keyword"),
            "kw_zh": d.get("translateKeyword"),
            "nat_rank": d.get("productNaturalRank"),
            "ad_rank": d.get("productAdRank"),
            "search_vol": d.get("weeklySearchVolume"),
            "traffic_share_pct": round(_num(d.get("trafficShare")) * 100, 2),
            "positions": pos,
            "markers": mk,
        })
    top_kw_sv = max((_num(d.get("weeklySearchVolume")) for d in rows), default=0)
    arch = {
        "asin": asin, "country": country,
        "returned": len(rows),
        "top_kw_sv": int(top_kw_sv),
        "top_keywords": top,
    }
    return arch, None


def parse_summary_row(s):
    """从 asinSummary 单条记录归一化流量入口构成。"""
    nat = _num(s.get("naturalSearchExposureRatio"))
    sp = _num(s.get("sponsoredProductsExposureRatio"))
    sb = _num(s.get("brandAdExposureRatio"))
    sbv = _num(s.get("videoAdExposureRatio"))
    ac = _num(s.get("amazonsChoiceExposureRatio"))
    er = _num(s.get("editorialRecommendationsExposureRatio"))
    tr = _num(s.get("topRatedExposureRatio"))
    rec = round(ac + er + tr, 4)
    paid = round(sp + sb + sbv, 4)
    comp = {"nat": round(nat, 4), "sp": round(sp, 4), "sb": round(sb, 4),
            "sbv": round(sbv, 4), "rec": rec}
    return {
        "asin": s.get("asin"),
        "composition": comp,                 # 曝光占比（自然/SP/SB/SBV/推荐位）
        "organic_share": round(nat, 4),
        "paid_share": paid,
        "counts": {
            "total_kw": s.get("totalTrafficKeywordCount"),
            "nf_count": s.get("naturalSearchKeywordCount"),
            "sp_count": s.get("sponsoredProductsKeywordCount"),
            "sb_count": s.get("brandAdKeywordCount"),
            "sbv_count": s.get("videoAdKeywordCount"),
            "ac_count": s.get("amazonsChoiceKeywordCount"),
        },
        "period": {
            "in": s.get("totalTrafficKeywordCountIn"),
            "out": s.get("totalTrafficKeywordCountOut"),
            "prev": s.get("totalTrafficKeywordCountPrev"),
        },
        "exposure_score": s.get("totalExposureScore"),
        "exposure_score_prev": s.get("totalExposureScorePrev"),
    }


def build_traffic_sources(asins, country):
    """批量调 asinSummary（≤10），返回 {asin: traffic_source_dict}。"""
    out = {}
    for i in range(0, len(asins), 10):
        chunk = asins[i:i + 10]
        res = run_skill(SUM_SCRIPT, {"searchValue": ",".join(chunk), "country": country,
                                     "pageSize": 100, "pageNum": 1})
        if res.get("error"):
            for a in chunk:
                out[a] = {"error": res.get("error")}
            continue
        rows = res.get("data") or []
        by_asin = {r.get("asin"): r for r in rows}
        for a in chunk:
            r = by_asin.get(a)
            out[a] = parse_summary_row(r) if r else {"error": "no summary data"}
    return out


def discover_asins(compare_dir):
    out = []
    for name in sorted(os.listdir(compare_dir)):
        p = os.path.join(compare_dir, name)
        if os.path.isdir(p) and re.match(r"^B0[0-9A-Z]{8}$", name):
            out.append(name)
    return out


def main():
    ap = argparse.ArgumentParser(description="关键词架构 + 流量入口 采集器")
    ap.add_argument("--asin", help="单个 ASIN")
    ap.add_argument("--asins", help="逗号分隔多个 ASIN")
    ap.add_argument("--compare-dir", help="_compare 目录（自动发现 ASIN 子目录并写回各自目录）")
    ap.add_argument("--outdir", help="单 ASIN 模式输出目录（默认当前目录）")
    ap.add_argument("--country", default="US")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    if not os.environ.get("LINKFOXAGENT_API_KEY"):
        print("[跳过] 未配置 LINKFOXAGENT_API_KEY，关键词/流量结构采集未执行。", file=sys.stderr)
        return 0

    # 解析 ASIN 列表 + 各自输出目录
    targets = []  # (asin, outdir)
    if args.compare_dir:
        cdir = os.path.abspath(args.compare_dir)
        for a in discover_asins(cdir):
            targets.append((a, os.path.join(cdir, a)))
    elif args.asins:
        for a in [x.strip() for x in args.asins.split(",") if x.strip()]:
            base_out = os.path.abspath(args.outdir or ".")
            asin_dir = os.path.join(base_out, a)
            targets.append((a, asin_dir if os.path.isdir(asin_dir) else base_out))
    elif args.asin:
        targets.append((args.asin, args.outdir or "."))
    else:
        print("需提供 --asin / --asins / --compare-dir 之一", file=sys.stderr)
        return 2

    asins = [a for a, _ in targets]
    traffic = build_traffic_sources(asins, args.country)

    index = {}
    for asin, outdir in targets:
        os.makedirs(outdir, exist_ok=True)
        arch, kw_err = build_keyword_arch(asin, args.country, args.top)
        ts = traffic.get(asin, {})
        ts_err = ts.get("error") if isinstance(ts, dict) else "n/a"

        if arch:
            # 把 ASIN 级占比/词数从 summary 并入 keyword_arch，便于报告与看板共用
            if not ts_err:
                arch["organic_share"] = ts.get("organic_share")
                arch["paid_share"] = ts.get("paid_share")
                arch["total_kw"] = (ts.get("counts") or {}).get("total_kw")
                arch["nf_count"] = (ts.get("counts") or {}).get("nf_count")
                arch["ad_count"] = sum(_num((ts.get("counts") or {}).get(k))
                                       for k in ("sp_count", "sb_count", "sbv_count"))
            with open(os.path.join(outdir, "keyword_arch.json"), "w", encoding="utf-8") as f:
                json.dump(arch, f, ensure_ascii=False, indent=2)
        if ts and not ts_err:
            with open(os.path.join(outdir, "traffic_source.json"), "w", encoding="utf-8") as f:
                json.dump(ts, f, ensure_ascii=False, indent=2)

        index[asin] = {
            "kw_ok": bool(arch), "kw_err": kw_err,
            "ts_ok": bool(ts and not ts_err), "ts_err": ts_err,
            "top_kw_sv": (arch or {}).get("top_kw_sv"),
            "organic_share": (ts or {}).get("organic_share") if not ts_err else None,
            "total_kw": ((ts or {}).get("counts") or {}).get("total_kw") if not ts_err else None,
            "composition": (ts or {}).get("composition") if not ts_err else None,
        }
        print("%s: kw=%s ts=%s organic=%s total_kw=%s"
              % (asin, "OK" if arch else "FAIL(%s)" % kw_err,
                 "OK" if (ts and not ts_err) else "FAIL(%s)" % ts_err,
                 index[asin]["organic_share"], index[asin]["total_kw"]), flush=True)

    if args.compare_dir:
        with open(os.path.join(os.path.abspath(args.compare_dir), "kw_traffic_index.json"),
                  "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    print("=== fetch_keyword_traffic DONE ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
