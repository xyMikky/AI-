"""
竞品报告一致性校验器（发布前防错门）。

检查项：
1) visual.json / competitor_analysis.md / index.html（旧名 competitor_analysis.html 兼容）总分一致
2) visual.json.evidence.logo_mentions 与页面中 Logo 出现位置文本一致
3) visual.json 是否含 UTF-8 BOM（会导致渲染回退）
4) html 是否错误回退到了 markdown 全文模式（content-card）
5) Sections 编排顺序硬约束（V2.2 升级 · 章节六/七/八三联硬锁）：
   - sections[0] 必须是 verdict-headline（〇 · 问题本质）
   - sections[1] 必须是 kv-table（一 · 基础信息卡，严禁末三位）
   - sections[-1] 必须是 action-cards（八 · 行动结论收尾）
   - sections[-2] 必须是 score-cards（七 · 关键评分，紧贴 action-cards 之前）
   - sections[-3] 必须是 review-sentiment（六 · 评论情感解析）；允许其后紧随一个
     「优缺点证据分布」two-column-list（此时 sections[-3] 为该 two-column-list、[-4] 为 review-sentiment）；
     若评论不可用导致 review-sentiment 缺席，则 sections[-3] 必须是 metric-grid
   - 若 review-sentiment 与 metric-grid 同时存在，则必须严格相邻：
     metric-grid → review-sentiment →（可选「优缺点证据分布」two-column-list）→ score-cards → action-cards
   - kv-table 严禁排到末三位
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


try:
  sys.path.insert(0, str(Path(__file__).resolve().parent))
  from render_report_html import SECTION_RENDERERS  # type: ignore
  SUPPORTED_SECTION_TYPES = set(SECTION_RENDERERS)
except Exception:
  SUPPORTED_SECTION_TYPES = {
    "tag-cards",
    "score-cards",
    "action-cards",
    "kv-table",
    "info-list",
    "quote",
    "custom-html",
    "step-ladder",
    "info-layers",
    "two-column-list",
    "metric-grid",
    "keyword-cloud",
    "verdict-headline",
    "best-for-grid",
    "feature-breakdown",
    "look-suite",
    "review-sentiment",
    "w5h2-grid",
    "persona-cards",
    "kano-model",
    "dev-watchpoints",
  }


def parse_args() -> argparse.Namespace:
  p = argparse.ArgumentParser(description="校验竞品报告三件套一致性")
  p.add_argument("--dir", required=True, help="报告目录（含 md/json/html）")
  return p.parse_args()


def read_text(path: Path, enc: str = "utf-8") -> str:
  return path.read_text(encoding=enc, errors="ignore")


def load_json_file(path: Path) -> dict[str, Any]:
  if not path.exists():
    return {}
  try:
    data = json.loads(read_text(path, enc="utf-8-sig"))
    return data if isinstance(data, dict) else {}
  except Exception:
    return {}


def as_int(value: Any) -> int | None:
  if isinstance(value, bool):
    return None
  if isinstance(value, int):
    return value
  if isinstance(value, float):
    return int(value)
  if isinstance(value, str):
    m = re.search(r"\d+", value)
    return int(m.group(0)) if m else None
  return None


def get_aplus_module_count(metadata: dict[str, Any], report: dict[str, Any]) -> int | None:
  media = metadata.get("media") if isinstance(metadata.get("media"), dict) else {}
  candidates = [
    as_int(media.get("aplus_module_count")),
    as_int(media.get("aplus_module_top_level")),
  ]
  aplus = report.get("aplus") if isinstance(report.get("aplus"), dict) else {}
  candidates.extend([
    as_int(aplus.get("group_count")),
    len(aplus.get("groups") or []) if isinstance(aplus.get("groups"), list) else None,
  ])
  values = [v for v in candidates if v is not None]
  return max(values) if values else None


def parse_float_from_text(text: str) -> float | None:
  m = re.search(r"([0-9]+(?:\.[0-9])?)", text)
  return float(m.group(1)) if m else None


def get_summary_total_from_visual(data: dict[str, Any]) -> float | None:
  for c in data.get("summary") or []:
    if c.get("label") == "加权总分":
      return parse_float_from_text(str(c.get("value", "")))
  return None


def get_md_total(md: str) -> float | None:
  m = re.search(r"\|\s*\*\*加权总分\*\*\s*\|\s*\*\*([0-9]+(?:\.[0-9])?)\s*/\s*5\.0\*\*", md)
  if m:
    return float(m.group(1))
  m2 = re.search(r"加权总分[^\\n]*([0-9]+(?:\.[0-9])?)\s*/\s*5\.0", md)
  return float(m2.group(1)) if m2 else None


def get_html_total(html: str) -> float | None:
  m = re.search(r"加权总分</div><div class=\"v\">([0-9]+(?:\.[0-9])?)\s*/\s*5\.0</div>", html)
  return float(m.group(1)) if m else None


def get_logo_count_from_visual(data: dict[str, Any]) -> int | None:
  ev = data.get("evidence") or {}
  mentions = ev.get("logo_mentions")
  if isinstance(mentions, list):
    return len(mentions)
  # fallback: 从 metric-grid 文本提取
  for sec in data.get("sections") or []:
    if sec.get("type") != "metric-grid":
      continue
    for item in sec.get("items") or []:
      if item.get("label") == "Logo 出现位置":
        n = parse_float_from_text(str(item.get("value", "")))
        return int(n) if n is not None else None
  return None


def get_logo_count_from_html(html: str) -> int | None:
  m = re.search(r"Logo 出现位置</div>\\s*<div class=\"metric-value\">([0-9]+)\s*次", html)
  return int(m.group(1)) if m else None


def has_utf8_bom(path: Path) -> bool:
  raw = path.read_bytes()
  return raw.startswith(b"\xef\xbb\xbf")


def parse_dashboard_meta(path: Path) -> dict[str, Any] | None:
  if not path.exists():
    return None
  text = read_text(path)
  marker = "window.__REVIEW_META__ = "
  start = text.find(marker)
  if start < 0:
    return None
  start += len(marker)
  decoder = json.JSONDecoder()
  try:
    payload, _ = decoder.raw_decode(text[start:])
    return payload if isinstance(payload, dict) else None
  except json.JSONDecodeError:
    return None


def section_items(section: dict[str, Any], *keys: str) -> list[Any]:
  for key in keys:
    val = section.get(key)
    if isinstance(val, list):
      return val
  return []


def _hist_map(rows: Any) -> dict[int, float]:
  if not isinstance(rows, list):
    return {}
  out: dict[int, float] = {}
  for row in rows:
    if not isinstance(row, dict):
      continue
    try:
      star = int(float(row.get("star")))
      percent = round(float(row.get("percent")), 1)
    except (TypeError, ValueError):
      continue
    out[star] = percent
  return out


def has_cjk(text: str) -> bool:
  return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def ascii_word_count(text: str) -> int:
  return len(re.findall(r"[A-Za-z]{3,}", text or ""))


def compact_text(value: Any) -> str:
  return re.sub(r"\s+", " ", str(value or "")).strip()


def count_highlight_marks(value: Any) -> int:
  if isinstance(value, str):
    return value.count("==") // 2
  if isinstance(value, list):
    return sum(count_highlight_marks(v) for v in value)
  if isinstance(value, dict):
    return sum(count_highlight_marks(v) for v in value.values())
  return 0


def main() -> int:
  args = parse_args()
  root = Path(args.dir).expanduser().resolve()
  md_path = root / "competitor_analysis.md"
  json_path = root / "visual.json"
  # HTML 报告默认输出为 index.html；兼容历史版本的 competitor_analysis.html。
  html_path = root / "index.html"
  if not html_path.exists():
    legacy_html = root / "competitor_analysis.html"
    if legacy_html.exists():
      html_path = legacy_html

  for p in (md_path, json_path, html_path):
    if not p.exists():
      raise FileNotFoundError(f"缺少文件: {p}")

  md = read_text(md_path)
  html = read_text(html_path)
  visual = json.loads(read_text(json_path, enc="utf-8-sig"))
  metadata = load_json_file(root / "metadata.json")
  report = load_json_file(root / "report.json")
  keyword_arch = load_json_file(root / "keyword_arch.json")
  traffic_source = load_json_file(root / "traffic_source.json")

  errs: list[str] = []

  # 1) 总分一致
  v_total = get_summary_total_from_visual(visual)
  m_total = get_md_total(md)
  h_total = get_html_total(html)
  if v_total is None or m_total is None or h_total is None:
    errs.append("无法解析总分（visual/md/html 之一缺失）")
  else:
    if abs(v_total - m_total) > 0.05:
      errs.append(f"总分不一致：visual={v_total} / md={m_total}")
    if abs(v_total - h_total) > 0.05:
      errs.append(f"总分不一致：visual={v_total} / html={h_total}")

  # 2) Logo 次数一致
  v_logo = get_logo_count_from_visual(visual)
  h_logo = get_logo_count_from_html(html)
  if v_logo is not None and h_logo is not None and v_logo != h_logo:
    errs.append(f"Logo 次数不一致：visual={v_logo} / html={h_logo}")

  # 3) BOM
  if has_utf8_bom(json_path):
    errs.append("visual.json 含 UTF-8 BOM（可能触发渲染回退）")

  # 4) 回退渲染痕迹
  if "class=\"content-card\"" in html:
    errs.append("HTML 检测到 content-card，疑似回退到 markdown 全文模式")
  if "未识别的 section type" in html:
    errs.append("HTML 检测到未识别 section type 黄框；请补 render_report_html.py 的 SECTION_RENDERERS 或改 visual.json type")

  # 4.1) 评论看板必须保留智能问题归类。没有 aspects 时前端会隐藏整块。
  dashboard_path = root / "review_dashboard.html"
  if dashboard_path.exists():
    dash_meta = parse_dashboard_meta(dashboard_path)
    aspects = (dash_meta or {}).get("aspects") or {}
    if not isinstance(aspects, dict) or not aspects:
      errs.append("review_dashboard.html 缺少智能问题归类 aspects；生成看板时请传 --aspects <aspects.json>")
    keywords = (dash_meta or {}).get("keywords") or {}
    if not isinstance(keywords, dict) or not keywords:
      errs.append("review_dashboard.html 缺少中文策展关键词云 keywords；生成看板时请传 --keywords <keywords.json>")
    else:
      for band in ("pos", "neg"):
        items = keywords.get(band) or []
        if not isinstance(items, list) or not items:
          errs.append(f"review_dashboard.html 的 keywords.{band} 不能为空")
          continue
        bad_terms = [
          str(item.get("term", ""))
          for item in items
          if isinstance(item, dict) and not has_cjk(str(item.get("term", "")))
        ]
        if bad_terms:
          errs.append(
              f"review_dashboard.html 的 keywords.{band} 存在非中文标签：{bad_terms[:5]}；请用中文业务词显示词云"
          )

  # 4.2) 关键词圈画密度：整份结构化报告不能只在首屏画一个词。
  highlight_count = count_highlight_marks(visual)
  if highlight_count < 12:
    errs.append(
      f"visual.json 关键词圈画不足：当前 {highlight_count} 处，至少需要 12 处 ==关键词== 高亮，覆盖问题本质/用户视角/评论差异/评分/行动结论"
    )

  # 5) Sections 编排顺序硬约束（V2.2 升级 · 章节六/七/八三联硬锁）
  sections = visual.get("sections") or []
  if sections:
    types = [s.get("type") for s in sections if isinstance(s, dict)]
    unknown_types = sorted({str(t) for t in types if t not in SUPPORTED_SECTION_TYPES})
    if unknown_types:
      errs.append(f"visual.json 存在渲染器不支持的 section type：{unknown_types}")
    n = len(types)
    has_review = "review-sentiment" in types
    aplus_module_count = get_aplus_module_count(metadata, report)
    needs_info_layers = aplus_module_count is not None and aplus_module_count >= 3
    required_style_labels = ["色彩应用", "模特/受众", "摄影风格", "整体调性", "拍摄方式"]
    if "tag-cards" not in types:
      errs.append(
        "风格五标签缺失：visual.json.sections 必须包含 tag-cards（章节「二 · 风格五标签 · 视觉摘要」）"
      )
    if "step-ladder" not in types:
      errs.append(
        "卖点排序缺失：visual.json.sections 必须包含 step-ladder（章节「三-1 · 卖点排序 · 三层递进」）"
      )
    if needs_info_layers and "info-layers" not in types:
      errs.append(
        f"信息层级缺失：A+ 模块数为 {aplus_module_count}，visual.json.sections 必须包含 info-layers（章节「三-2 · 信息层级 · A+ 分层拆解」）"
      )
    if keyword_arch and "keyword-arch" not in types:
      errs.append(
        "关键词架构缺失：目录存在 keyword_arch.json，visual.json.sections 必须包含 keyword-arch（章节「三-3 · 关键词架构」）"
      )
    if traffic_source and "traffic-entry" not in types:
      errs.append(
        "流量入口结构缺失：目录存在 traffic_source.json，visual.json.sections 必须包含 traffic-entry（章节「三-4 · 流量入口结构」）"
      )
    required_customer_insight = ["w5h2-grid", "persona-cards", "kano-model", "dev-watchpoints"]
    missing_customer_insight = [t for t in required_customer_insight if t not in types]
    if missing_customer_insight:
      errs.append(
        "V4 客户洞察四块缺失："
        f"{missing_customer_insight}。单 SKU 报告必须同时包含 5W2H 购买行为 / 客户画像 / Kano 真实需求 / 产品开发注意点"
      )
    if "best-for-grid" in types and "metric-grid" in types:
      i_best = types.index("best-for-grid")
      i_metric = types.index("metric-grid")
      for t in required_customer_insight:
        if t in types:
          i_t = types.index(t)
          if not (i_best < i_t < i_metric):
            errs.append(
              f"V4 客户洞察位置错位：'{t}' (idx={i_t}) 必须位于 "
              f"'best-for-grid' (idx={i_best}) 之后、'metric-grid' (idx={i_metric}) 之前"
            )
    elif any(t in types for t in required_customer_insight):
      errs.append("V4 客户洞察需要 best-for-grid 与 metric-grid 作为前后锚点")

    # 5.1 sections[0] 必须是 verdict-headline
    if n >= 1 and types[0] != "verdict-headline":
      errs.append(
        f"Sections 顺序错位：sections[0] 应为 'verdict-headline'（〇 问题本质），实为 '{types[0]}'"
      )

    # 5.2 sections[1] 必须是 kv-table（基础信息卡严禁末位）
    if n >= 2 and types[1] != "kv-table":
      errs.append(
        f"Sections 顺序错位：sections[1] 应为 'kv-table'（一 基础信息卡），实为 '{types[1]}'"
      )

    # 5.2.1 sections[2] 必须是 tag-cards（风格五标签 · 视觉摘要）
    if n >= 3 and types[2] != "tag-cards":
      errs.append(
        f"Sections 顺序错位：sections[2] 应为 'tag-cards'（二 · 风格五标签 · 视觉摘要），实为 '{types[2]}'"
      )

    # 5.2.2 sections[3] 必须是 step-ladder（三层递进卖点摘要）
    if n >= 4 and types[3] != "step-ladder":
      errs.append(
        f"Sections 顺序错位：sections[3] 应为 'step-ladder'（三-1 · 卖点排序 · 三层递进），实为 '{types[3]}'"
      )

    # 5.2.3 A+ 足够时，sections[4] 必须是 info-layers（信息层级拆解）
    if needs_info_layers and n >= 5 and types[4] != "info-layers":
      errs.append(
        f"Sections 顺序错位：sections[4] 应为 'info-layers'（三-2 · 信息层级 · A+ 分层拆解），实为 '{types[4]}'"
      )
    if "step-ladder" in types and "info-layers" in types:
      i_step = types.index("step-ladder")
      i_info = types.index("info-layers")
      if i_info != i_step + 1:
        errs.append(
          f"Sections 顺序错位：'info-layers' (idx={i_info}) 必须紧跟 'step-ladder' (idx={i_step}) 之后"
        )
    if "info-layers" in types and "keyword-arch" in types:
      i_info = types.index("info-layers")
      i_kw = types.index("keyword-arch")
      if i_kw != i_info + 1:
        errs.append(
          f"Sections 顺序错位：'keyword-arch' (idx={i_kw}) 必须紧跟 'info-layers' (idx={i_info}) 之后，作为三-3"
        )
    if "keyword-arch" in types and "traffic-entry" in types:
      i_kw = types.index("keyword-arch")
      i_tr = types.index("traffic-entry")
      if i_tr != i_kw + 1:
        errs.append(
          f"Sections 顺序错位：'traffic-entry' (idx={i_tr}) 必须紧跟 'keyword-arch' (idx={i_kw}) 之后，作为三-4"
        )

    # 5.3 sections[-1] 必须是 action-cards（章节「八」行动结论收尾）
    if n >= 1 and types[-1] != "action-cards":
      errs.append(
        f"Sections 顺序错位：sections[-1] 应为 'action-cards'（八 · 行动结论），实为 '{types[-1]}'"
      )

    # 5.4 sections[-2] 必须是 score-cards（章节「七」关键评分紧贴 action-cards 之前）
    if n >= 2 and types[-2] != "score-cards":
      errs.append(
        f"Sections 顺序错位：sections[-2] 应为 'score-cards'（七 · 关键评分，紧贴 action-cards 之前），"
        f"实为 '{types[-2]}'"
      )

    # 5.5 sections[-3]：评论可用时应为 review-sentiment（六 · 评论情感解析）；
    #     允许在其后、score-cards 之前插入「优缺点证据分布」two-column-list，
    #     此时 sections[-3] 为该 two-column-list、sections[-4] 为 review-sentiment。
    #     当评论不可用时，sections[-3] 应为 metric-grid（收尾三联）。
    if n >= 3:
      if has_review:
        ok_minus3 = (
          types[-3] == "review-sentiment"
          or (types[-3] == "two-column-list" and n >= 4 and types[-4] == "review-sentiment")
        )
        if not ok_minus3:
          errs.append(
            f"Sections 顺序错位：sections[-3] 应为 'review-sentiment'（六 · 评论情感解析），"
            f"或紧随其后的「优缺点证据分布」two-column-list，实为 '{types[-3]}'"
          )
      elif types[-3] != "metric-grid":
        errs.append(
          f"Sections 顺序错位（评论不可用降级模式）：sections[-3] 应为 'metric-grid'"
          f"（紧贴 score-cards 之前），实为 '{types[-3]}'"
        )

    # 5.6 收尾四联硬序：metric-grid → review-sentiment → score-cards → action-cards 必须严格相邻
    if has_review and "metric-grid" in types:
      i_metric = types.index("metric-grid")
      i_review = types.index("review-sentiment")
      if i_review != i_metric + 1:
        errs.append(
          f"Sections 顺序错位：'review-sentiment' (idx={i_review}) 必须紧跟 'metric-grid' "
          f"(idx={i_metric}) 之后，中间不得插入其他 section"
        )

    # 5.7 review-sentiment 与 score-cards 之间仅允许 0 或 1 个「优缺点证据分布」two-column-list
    if has_review and "score-cards" in types:
      i_review = types.index("review-sentiment")
      i_score = types.index("score-cards")
      gap = types[i_review + 1:i_score]
      if gap not in ([], ["two-column-list"]):
        errs.append(
          f"Sections 顺序错位：'review-sentiment' (idx={i_review}) 与 'score-cards' (idx={i_score}) "
          f"之间仅允许 0 或 1 个 'two-column-list'（优缺点证据分布），实为 {gap}"
        )

    # 5.8 score-cards 必须紧跟 metric-grid（评论不可用降级模式）
    if not has_review and "score-cards" in types and "metric-grid" in types:
      i_metric = types.index("metric-grid")
      i_score = types.index("score-cards")
      if i_score != i_metric + 1:
        errs.append(
          f"Sections 顺序错位（评论不可用降级模式）：'score-cards' (idx={i_score}) 必须紧跟 "
          f"'metric-grid' (idx={i_metric}) 之后"
        )

    # 5.9 kv-table 严禁排到末三位
    if "kv-table" in types:
      i_kv = types.index("kv-table")
      if n >= 5 and i_kv >= n - 3:
        errs.append(
          f"Sections 顺序错位：'kv-table' (idx={i_kv}/{n}) 不得排在末三位，"
          "基础信息卡必须靠前作为事实锚点"
        )

    # 5.10 内容完整性：关键卡片不能结构存在但内容为空。
    for idx, sec in enumerate(sections):
      if not isinstance(sec, dict):
        continue
      stype = sec.get("type")
      if stype == "verdict-headline":
        headline = str(sec.get("headline") or sec.get("text") or "")
        if "==" not in headline:
          errs.append(
            f"Sections 内容问题：verdict-headline(idx={idx}) 必须用 ==关键词== 圈画核心风险/承诺词"
          )
      if stype == "tag-cards":
        items = section_items(sec, "items")
        if len(items) != 5:
          errs.append(
            f"Sections 内容缺失：tag-cards(idx={idx}) 必须恰好 5 个风格标签卡，当前 {len(items)} 个"
          )
        names = [str(item.get("name", "")).strip() for item in items if isinstance(item, dict)]
        missing_labels = [label for label in required_style_labels if label not in names]
        if missing_labels:
          errs.append(
            f"Sections 内容缺失：tag-cards(idx={idx}) 缺少风格五标签维度 {missing_labels}；必须覆盖 色彩应用/模特或受众/摄影风格/整体调性/拍摄方式"
          )
        for ti, item in enumerate(items):
          if not isinstance(item, dict):
            errs.append(f"Sections 内容问题：tag-cards(idx={idx}) 第 {ti} 项必须是 object")
            continue
          if not item.get("name") or not item.get("desc") or not section_items(item, "pills"):
            errs.append(
              f"Sections 内容缺失：tag-cards(idx={idx}) 第 {ti} 项必须包含 name、pills[]、desc"
            )
          if item.get("name") == "色彩应用" and not section_items(item, "swatches"):
            errs.append(
              f"Sections 内容缺失：tag-cards(idx={idx}) 色彩应用卡必须包含 swatches[] 色卡"
            )
      elif stype == "step-ladder":
        items = section_items(sec, "items")
        if len(items) != 3:
          errs.append(
            f"Sections 内容问题：step-ladder(idx={idx}) 必须恰好 3 条卖点，形成三层递进，当前 {len(items)} 条"
          )
        for si, item in enumerate(items):
          if not isinstance(item, dict):
            errs.append(f"Sections 内容问题：step-ladder(idx={idx}) 第 {si} 项必须是 object")
            continue
          name = compact_text(item.get("name"))
          desc = compact_text(item.get("desc"))
          if not name or not desc:
            errs.append(f"Sections 内容缺失：step-ladder(idx={idx}) 第 {si} 项必须包含 name 与 desc")
            continue
          if not has_cjk(name) or not has_cjk(desc):
            errs.append(
              f"Sections 内容问题：step-ladder(idx={idx}) 第 {si} 项必须是中文摘要，禁止直接粘贴英文 bullet"
            )
          if len(name) > 32:
            errs.append(
              f"Sections 内容过长：step-ladder(idx={idx}) 第 {si} 项 name 超过 32 字，应压缩成中文短标题"
            )
          if len(desc) > 90:
            errs.append(
              f"Sections 内容过长：step-ladder(idx={idx}) 第 {si} 项 desc 超过 90 字，应压缩成一句中文副说明"
            )
          if ascii_word_count(name) > 5 or ascii_word_count(desc) > 8:
            errs.append(
              f"Sections 内容问题：step-ladder(idx={idx}) 第 {si} 项英文词过多，应保留 MagSafe/N52/96 LBS 等术语但用中文组织"
            )
      elif stype == "info-layers":
        items = section_items(sec, "items")
        if len(items) != 3:
          errs.append(
            f"Sections 内容问题：info-layers(idx={idx}) 必须恰好 3 层：第一层/第二层/第三层，当前 {len(items)} 层"
          )
        required_layers = ["第一层", "第二层", "第三层"]
        for li, item in enumerate(items):
          if not isinstance(item, dict):
            errs.append(f"Sections 内容问题：info-layers(idx={idx}) 第 {li} 项必须是 object")
            continue
          layer = compact_text(item.get("layer"))
          name = compact_text(item.get("name"))
          desc = compact_text(item.get("desc"))
          if li < len(required_layers) and required_layers[li] not in layer:
            errs.append(
              f"Sections 内容问题：info-layers(idx={idx}) 第 {li} 项 layer 应标为 {required_layers[li]}"
            )
          if not name or not desc:
            errs.append(f"Sections 内容缺失：info-layers(idx={idx}) 第 {li} 项必须包含 name 与 desc")
            continue
          if not has_cjk(name) or not has_cjk(desc):
            errs.append(
              f"Sections 内容问题：info-layers(idx={idx}) 第 {li} 项必须是中文层级拆解，禁止英文原文堆叠"
            )
          if len(name) > 28:
            errs.append(
              f"Sections 内容过长：info-layers(idx={idx}) 第 {li} 项 name 超过 28 字，应压缩成层级标题"
            )
          if len(desc) > 90:
            errs.append(
              f"Sections 内容过长：info-layers(idx={idx}) 第 {li} 项 desc 超过 90 字，应压缩成一句中文说明"
            )
          if ascii_word_count(name) > 4 or ascii_word_count(desc) > 8:
            errs.append(
              f"Sections 内容问题：info-layers(idx={idx}) 第 {li} 项英文词过多，应中文化表达信息层级"
            )
      elif stype == "keyword-arch":
        keywords = section_items(sec, "keywords")
        metrics = section_items(sec, "metrics")
        if not keywords:
          errs.append(f"Sections 内容缺失：keyword-arch(idx={idx}) 的 keywords 不能为空")
        if not metrics:
          errs.append(f"Sections 内容缺失：keyword-arch(idx={idx}) 的 metrics 不能为空")
      elif stype == "traffic-entry":
        composition = section_items(sec, "composition")
        metrics = section_items(sec, "metrics")
        if not composition:
          errs.append(f"Sections 内容缺失：traffic-entry(idx={idx}) 的 composition 不能为空")
        if not metrics:
          errs.append(f"Sections 内容缺失：traffic-entry(idx={idx}) 的 metrics 不能为空")
      elif stype == "best-for-grid":
        best_items = section_items(sec, "best_for", "best")
        not_items = section_items(sec, "not_for", "notfor", "avoid")
        if not best_items:
          errs.append(
            f"Sections 内容缺失：best-for-grid(idx={idx}) 的 best_for/best 不能为空，否则适合人群左栏为空"
          )
        if not not_items:
          errs.append(
            f"Sections 内容缺失：best-for-grid(idx={idx}) 的 not_for 不能为空，否则不适合人群右栏为空"
          )
      elif stype == "action-cards" and not section_items(sec, "items"):
        errs.append(f"Sections 内容缺失：action-cards(idx={idx}) 的 items 不能为空")
      elif stype == "score-cards" and not section_items(sec, "items"):
        errs.append(f"Sections 内容缺失：score-cards(idx={idx}) 的 items 不能为空")
      elif stype == "review-sentiment":
        if not section_items(sec, "positive_keywords") and not section_items(sec, "critical_keywords"):
          errs.append(
            f"Sections 内容缺失：review-sentiment(idx={idx}) 至少需要 positive_keywords 或 critical_keywords"
          )
        global_hist = ((load_json_file(root / "reviews_aggregate.json").get("global") or {}).get("histogram") or [])
        if global_hist:
          expected_hist = _hist_map(global_hist)
          actual_hist = _hist_map(sec.get("histogram"))
          if expected_hist and actual_hist != expected_hist:
            errs.append(
              f"全局星级分布口径错误：review-sentiment(idx={idx}).histogram 必须使用 "
              f"reviews_aggregate.json.global.histogram，当前={actual_hist}，应为={expected_hist}"
            )
        for key in ("positive_keywords", "critical_keywords", "word_cloud"):
          bad_terms: list[str] = []
          for item in section_items(sec, key):
            text = item if isinstance(item, str) else (item.get("text", "") if isinstance(item, dict) else "")
            if text and not has_cjk(str(text)):
              bad_terms.append(str(text))
          if bad_terms:
            errs.append(
              f"Sections 内容问题：review-sentiment(idx={idx}) 的 {key} 存在非中文关键词 {bad_terms[:5]}，请同步 keywords.json 的中文策展词"
            )
      elif stype == "two-column-list":
        cols = section_items(sec, "columns")
        if not cols and (section_items(sec, "left") or section_items(sec, "right")):
          cols = [
            {"bullets": section_items(sec, "left")},
            {"bullets": section_items(sec, "right")},
          ]
        if not cols:
          errs.append(
            f"Sections 内容缺失：two-column-list(idx={idx}) 的 columns 不能为空，否则只显示标题"
          )
        else:
          empty_cols = [
            i for i, col in enumerate(cols)
            if not isinstance(col, dict) or not section_items(col, "bullets")
          ]
          if empty_cols:
            errs.append(
              f"Sections 内容缺失：two-column-list(idx={idx}) 存在空列 {empty_cols}，每列 bullets 不能为空"
            )
      elif stype == "w5h2-grid":
        items = section_items(sec, "items")
        keys = {str(it.get("key", "")).strip().lower() for it in items if isinstance(it, dict)}
        required_keys = {"who", "what", "when", "where", "why", "how", "how much"}
        if not items:
          errs.append(f"Sections 内容缺失：w5h2-grid(idx={idx}) 的 items 不能为空")
        elif not required_keys.issubset(keys):
          errs.append(
            f"Sections 内容缺失：w5h2-grid(idx={idx}) 必须覆盖 Who/What/When/Where/Why/How/How much，当前={sorted(keys)}"
          )
        for wi, item in enumerate(items):
          if not isinstance(item, dict):
            errs.append(f"Sections 内容问题：w5h2-grid(idx={idx}) 第 {wi} 项必须是 object")
            continue
          label = compact_text(item.get("zh") or item.get("label") or item.get("title"))
          value = compact_text(
            item.get("finding")
            or item.get("value")
            or item.get("desc")
            or item.get("text")
            or item.get("answer")
          )
          if not label or not value:
            errs.append(
              f"Sections 内容缺失：w5h2-grid(idx={idx}) 第 {wi} 项必须包含中文标题 label/zh 与正文 value/finding"
            )
          elif not has_cjk(label + value):
            errs.append(
              f"Sections 内容问题：w5h2-grid(idx={idx}) 第 {wi} 项应使用中文解释购买行为，不能只保留英文 key"
            )
      elif stype == "persona-cards":
        items = section_items(sec, "items")
        if not items:
          errs.append(f"Sections 内容缺失：persona-cards(idx={idx}) 的 items 不能为空")
        elif len(items) > 3:
          errs.append(f"Sections 内容问题：persona-cards(idx={idx}) 最多 3 个画像，避免雷同堆砌")
        for pi, item in enumerate(items):
          if not isinstance(item, dict):
            errs.append(f"Sections 内容问题：persona-cards(idx={idx}) 第 {pi} 项必须是 object")
            continue
          if not item.get("name") or not section_items(item, "tags") or not (item.get("motivation") or item.get("pain")):
            errs.append(
              f"Sections 内容缺失：persona-cards(idx={idx}) 第 {pi} 项必须包含 name、tags，并至少包含 motivation 或 pain"
            )
      elif stype == "kano-model":
        groups = section_items(sec, "groups")
        if not groups:
          errs.append(f"Sections 内容缺失：kano-model(idx={idx}) 的 groups 不能为空")
        kanos = {str(g.get("kano") or g.get("category") or "").strip().lower() for g in groups if isinstance(g, dict)}
        required_kanos = {"must-be", "one-dimensional", "attractive"}
        if groups and not required_kanos.issubset(kanos):
          errs.append(
            f"Sections 内容缺失：kano-model(idx={idx}) 至少覆盖 must-be / one-dimensional / attractive，当前={sorted(kanos)}"
          )
      elif stype == "dev-watchpoints":
        items = section_items(sec, "items")
        if not items:
          errs.append(f"Sections 内容缺失：dev-watchpoints(idx={idx}) 的 items 不能为空")
        priorities = {str(it.get("priority", "")).strip().upper() for it in items if isinstance(it, dict)}
        if "P0" not in priorities:
            errs.append(f"Sections 内容缺失：dev-watchpoints(idx={idx}) 必须至少包含 1 条 P0 优先级注意点")

    if "w5h2-grid" in types and 'class="w5h2-finding w5h2-value"' not in html:
      errs.append("HTML 渲染缺失：w5h2-grid 必须输出 w5h2-value 正文，不能只显示 who/what 等 key")

    specs = metadata.get("specs") if isinstance(metadata.get("specs"), list) else []
    bullets_text = " ".join(str(b) for b in (metadata.get("bullets") or []))
    bullet_has_specs = re.search(
      r"\b(?:gal/min|L/min|LB|mins?|batter(?:y|ies)|5V|USB|O-ring)\b",
      bullets_text,
      flags=re.I,
    )
    if bullet_has_specs and not specs:
      errs.append(
        "产品参数缺失：bullets 中存在续航/水流/重量/电池/充电等可结构化参数，metadata.specs 不得为空"
      )

  if errs:
    print("[FAIL] 报告一致性校验失败")
    for e in errs:
      print(f" - {e}")
    return 2

  print("[PASS] 报告一致性校验通过")
  print(f" - 总分一致：{v_total:.1f} / 5.0")
  if v_logo is not None:
    print(f" - Logo 次数一致：{v_logo} 次")
  sections = visual.get("sections") or []
  if sections:
    types = [s.get("type") for s in sections if isinstance(s, dict)]
    print(f" - Sections 顺序合规：{len(types)} 节，首位={types[0]}，末位={types[-1]}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
