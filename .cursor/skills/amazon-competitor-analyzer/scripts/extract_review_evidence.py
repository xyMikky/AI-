"""按「优缺点分组」提取对应的全部评论证据（喂给 agent 做综合分析）。

输入：评论数据（.json/.xlsx）+ metadata.json（目标 ASIN）+ keywords.json（策展词云）+ aspects.json（智能问题归类）。
逻辑：复用 review_core 读入并按目标 ASIN 过滤；对每个优缺点分组（keywords.pos/neg 的 term，
      以及 aspects 各维度的子问题），用「去撇号小写子串匹配 + 情感星档门控」找出**命中的全部评论**，
      与看板点击口径完全一致（count == 命中评论数）。
输出：review_evidence.json —— 每个分组含 {极性, 命中量, 均分, 低星比, 星级分布, 代表原话, 全部命中评论}。
      并向 stdout 打印可读摘要，供 agent 直接据此重写报告的优缺点综合分析。

匹配口径（与 build_review_dashboard.py 严格对齐）：
  keywords.pos → 仅 4-5★      keywords.neg → 仅 1-2★
  aspects 维度 polarity: pos→4-5★ / neg→1-3★ / any→不限
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import review_core as rc

_APOS = re.compile(r"[\u2018\u2019\u02bc']")


def _norm(s: str) -> str:
    return _APOS.sub("", (s or "").lower())


def _star_gate(star: int, polarity: str) -> bool:
    if polarity == "pos":
        return star >= 4
    if polarity == "neg":
        return 1 <= star <= 2
    if polarity == "neg3":  # aspects 的 neg：含中评
        return 1 <= star <= 3
    return True


def _match(rec: dict[str, Any], terms: list[str]) -> bool:
    t = _norm(rec.get("text", ""))
    return any(term and term in t for term in terms)


def _stats(recs: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(recs)
    valid = [r["stars"] for r in recs if 1 <= r["stars"] <= 5]
    low = sum(1 for r in recs if r["stars"] in (1, 2))
    dist = {s: sum(1 for r in recs if r["stars"] == s) for s in range(1, 6)}
    return {
        "count": n,
        "avg": round(sum(valid) / len(valid), 2) if valid else 0,
        "low_pct": round(low / n * 100, 1) if n else 0,
        "star_dist": dist,
    }


def _quotes(recs: list[dict[str, Any]], terms: list[str], k: int = 5) -> list[dict[str, Any]]:
    """挑代表性原话：截取命中关键词上下文片段，长文优先（信息量更足）。"""
    pool = sorted(recs, key=lambda r: -(r.get("length") or 0))
    out = []
    for r in pool:
        disp = ((r["title"] + "：") if r["title"] else "") + (r["body"] or "")
        disp = re.sub(r"\s+", " ", disp).strip()
        low = _norm(disp)
        pos = -1
        for term in terms:
            p = low.find(term)
            if p >= 0:
                pos = p
                hit = term
                break
        if pos < 0:
            continue
        s = max(0, pos - 50)
        e = min(len(disp), pos + len(hit) + 110)
        snip = ("…" if s > 0 else "") + disp[s:e].strip() + ("…" if e < len(disp) else "")
        out.append({"stars": r["stars"], "date": r["date"] or "", "snippet": snip})
        if len(out) >= k:
            break
    return out


def _slim(recs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "stars": r["stars"],
            "date": r["date"] or "",
            "vp": bool(r["vp"]),
            "title": r["title"],
            "body": r["body"],
        }
        for r in sorted(recs, key=lambda r: (r["stars"], r["date"] or ""))
    ]


def _build_groups(keywords: dict, aspects: dict) -> list[dict[str, Any]]:
    """汇总所有优缺点分组：(source, polarity, label, terms)。"""
    groups: list[dict[str, Any]] = []
    # 1) 策展词云优缺点
    for band in ("pos", "neg"):
        for e in (keywords.get(band) or []):
            terms = [_norm(m) for m in (e.get("match") or [])]
            groups.append({
                "source": "keywords",
                "polarity": band,
                "label": e.get("term") or (terms[0] if terms else ""),
                "terms": terms,
            })
    # 2) 智能问题归类子问题
    for dim, v in (aspects or {}).items():
        has_wrap = isinstance(v, dict) and ("issues" in v or "polarity" in v)
        issues = (v.get("issues") if has_wrap else v) or {}
        pol = (v.get("polarity") if has_wrap else None)
        if not pol:
            pol = "pos" if re.search(r"正面|好评|优点|满意|positive|pros|赞", dim) else "any"
        gate = "neg3" if pol == "neg" else pol  # aspects 的 neg 含中评
        for name, kws in issues.items():
            terms = [_norm(k) for k in (kws or [])]
            groups.append({
                "source": "aspects",
                "polarity": pol,
                "gate": gate,
                "label": f"{dim} · {name}",
                "terms": terms,
            })
    return groups


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="按优缺点分组提取对应的全部评论证据")
    p.add_argument("--input", required=True, help="评论文件路径（.json/.xlsx）")
    p.add_argument("--meta", default="", help="metadata.json（取目标 ASIN）")
    p.add_argument("--asin", default="", help="显式目标 ASIN")
    p.add_argument("--all-variants", action="store_true", help="分析全部 ASIN")
    p.add_argument("--keywords", default="", help="keywords.json（策展词云）")
    p.add_argument("--aspects", default="", help="aspects.json（智能问题归类）")
    p.add_argument("--output", default="", help="输出目录，默认输入文件同目录")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    keywords = json.loads(Path(args.keywords).read_text(encoding="utf-8-sig")) if args.keywords else {}
    aspects = json.loads(Path(args.aspects).read_text(encoding="utf-8-sig")) if args.aspects else {}
    meta_json = {}
    if args.meta and Path(args.meta).exists():
        try:
            meta_json = json.loads(Path(args.meta).read_text(encoding="utf-8"))
        except Exception:
            meta_json = {}

    target_asin = rc.resolve_target_asin(args.asin, meta_json, args.all_variants)
    records, load_meta = rc.load_reviews(args.input, asin_filter=target_asin)
    if not records:
        raise ValueError(f"目标 ASIN '{target_asin}' 命中 0 条评论。")

    overall = _stats(records)
    groups = _build_groups(keywords, aspects)

    result: list[dict[str, Any]] = []
    for g in groups:
        gate = g.get("gate", g["polarity"])
        hits = [r for r in records if _star_gate(r["stars"], gate) and _match(r, g["terms"])]
        st = _stats(hits)
        result.append({
            "source": g["source"],
            "polarity": g["polarity"],
            "label": g["label"],
            "terms": g["terms"],
            **st,
            "quotes": _quotes(hits, g["terms"]),
            "reviews": _slim(hits),
        })

    out_dir = Path(args.output).expanduser().resolve() if args.output else Path(load_meta["source"]).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "review_evidence.json"
    payload = {
        "asin": target_asin,
        "scope": load_meta["scope"],
        "overall": overall,
        "groups": result,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 可读摘要（agent 据此综合分析）----
    print(f"[evidence] ASIN={target_asin} 样本={overall['count']} 均分={overall['avg']} 低星比={overall['low_pct']}%")
    print(f"[evidence] 输出: {out_path}\n")

    def _show(src_label: str, src_key: str):
        rows = [r for r in result if r["source"] == src_key]
        if not rows:
            return
        print(f"==== {src_label} ====")
        for r in sorted(rows, key=lambda x: -x["count"]):
            tag = {"pos": "好评", "neg": "差评", "any": "中性"}.get(r["polarity"], r["polarity"])
            print(f"\n[{tag}] {r['label']} | 命中 {r['count']} 条 · 均分 {r['avg']} · 低星比 {r['low_pct']}% · 星级 {r['star_dist']}")
            for q in r["quotes"][:3]:
                print(f"    {q['stars']}★ {q['snippet']}")
        print()

    _show("策展词云 · 优缺点分组", "keywords")
    _show("智能问题归类 · 子问题", "aspects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
