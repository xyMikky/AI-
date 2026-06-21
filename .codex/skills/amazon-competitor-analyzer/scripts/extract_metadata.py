"""
Amazon 商品页面元数据抽取器 —— amazon-competitor-analyzer Skill 配套工具。

输入：本地保存的 fetched_page.html（由 amazon-image-extractor 抓取得到）
输出：标准化 JSON（asin / brand / title / rating / rating_count / price / bsr / variants / bullets ...）

设计原则：
- 每个字段独立抽取，任何字段抽取失败都不阻塞其他字段（缺则置 None / 空列表）
- 不主动联网（即不会因网络抖动失败）
- 输出永远是合法 JSON，便于下游 Skill 流程消费
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup


def _read_html(path: Path) -> BeautifulSoup:
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        return BeautifulSoup(text, "lxml")
    except Exception:
        return BeautifulSoup(text, "html.parser")


def _text(node) -> str:
    if node is None:
        return ""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def _attr(node, name: str) -> str:
    if node is None:
        return ""
    return (node.get(name) or "").strip()


def extract_asin(soup: BeautifulSoup, fallback_url: str = "") -> str:
    m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", fallback_url, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()
    for li in soup.select("#detailBullets_feature_div li, #detailBulletsWrapper_feature_div li"):
        text = li.get_text(" ", strip=True)
        m = re.search(r"\bASIN\s*[:：]?\s*([A-Z0-9]{10})\b", text)
        if m:
            return m.group(1).upper()
    el = soup.select_one("#ASIN, input[name='ASIN']")
    if el:
        v = (el.get("value") or el.get_text(" ", strip=True)).strip().upper()
        if re.fullmatch(r"[A-Z0-9]{10}", v):
            return v
    for el in soup.select("[data-asin]"):
        v = el.get("data-asin", "").strip().upper()
        if re.fullmatch(r"[A-Z0-9]{10}", v):
            return v
    return ""


def extract_title(soup: BeautifulSoup) -> str:
    return _text(soup.select_one("#productTitle"))


def extract_brand(soup: BeautifulSoup) -> str:
    a = soup.select_one("#bylineInfo")
    if a:
        txt = _text(a)
        for prefix in ("Visit the ", "Brand: "):
            if txt.startswith(prefix):
                txt = txt[len(prefix):]
        for suffix in (" Store", " store"):
            if txt.endswith(suffix):
                txt = txt[: -len(suffix)]
        if txt:
            return txt.strip()
    for row in soup.select(".voyager-ns-desktop-table tr, #productOverview_feature_div tr"):
        label = _text(row.select_one("th, td:nth-child(1)"))
        if label and re.search(r"^\s*brand( name)?\s*$", label, flags=re.IGNORECASE):
            value = _text(row.select_one("td:last-child"))
            if value:
                return value
    return ""


def extract_rating(soup: BeautifulSoup) -> Optional[float]:
    el = soup.select_one("#acrPopover")
    title = _attr(el, "title")
    m = re.match(r"\s*([0-9.]+)\s*out of\s*5", title, flags=re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    span = soup.select_one("#acrPopover .a-icon-alt")
    m = re.match(r"\s*([0-9.]+)\s*out of\s*5", _text(span), flags=re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def extract_rating_count(soup: BeautifulSoup) -> Optional[int]:
    el = soup.select_one("#acrCustomerReviewText")
    if el is None:
        return None
    candidates = [_attr(el, "aria-label"), _text(el)]
    for raw in candidates:
        m = re.search(r"([\d,]+)", raw)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def extract_price(soup: BeautifulSoup) -> Dict[str, Optional[Any]]:
    out: Dict[str, Optional[Any]] = {
        "current": None,
        "list": None,
        "currency": None,
        "main_offer_status": "",
        "variant_from_price": None,
        "variant_from_currency": None,
    }

    selectors_current = [
        "#corePriceDisplay_desktop_feature_div .a-price[data-a-color='base'] .a-offscreen",
        "#corePrice_feature_div .a-price .a-offscreen",
        "#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        ".a-price .a-offscreen",
    ]
    for sel in selectors_current:
        el = soup.select_one(sel)
        if not el:
            continue
        raw = _text(el)
        m = re.search(r"([\$\u20ac\u00a3\u00a5]|US\$)\s*([\d,]+(?:\.\d+)?)", raw)
        if m:
            sym = m.group(1)
            out["current"] = float(m.group(2).replace(",", ""))
            out["currency"] = {"$": "USD", "US$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}.get(sym, sym)
            break

    if out["current"] is not None:
        out["main_offer_status"] = "available"

    el = soup.select_one(".basisPrice .a-offscreen") or soup.select_one(
        "#corePriceDisplay_desktop_feature_div .a-text-strike"
    )
    if el:
        m = re.search(r"([\d,]+(?:\.\d+)?)", _text(el))
        if m:
            try:
                out["list"] = float(m.group(1).replace(",", ""))
            except ValueError:
                pass

    # 若主报价缺失，识别页面是否明确显示“无可用报价”
    full_text = soup.get_text(" ", strip=False)
    if out["current"] is None:
        if re.search(r"No featured offers available", full_text, flags=re.IGNORECASE):
            out["main_offer_status"] = "no_featured_offer"
        else:
            out["main_offer_status"] = "unknown"

    # 变体卡上的 from 价格（例如 from $19.98）
    variant_text_sources: List[str] = []
    for row in soup.select("#inline-twister-row-color_name, #variation_color_name"):
        variant_text_sources.append(row.get_text(" ", strip=True))
    variant_text_sources.append(full_text)
    for raw in variant_text_sources:
        m = re.search(r"from\s*(US\$|\$|€|£|¥)\s*([\d,]+(?:\.\d+)?)", raw, flags=re.IGNORECASE)
        if m:
            sym = m.group(1)
            out["variant_from_price"] = float(m.group(2).replace(",", ""))
            out["variant_from_currency"] = {"$": "USD", "US$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}.get(sym, sym)
            break

    return out


def extract_category_rank(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Return list of {rank, category}, primary first."""
    out: List[Dict[str, str]] = []

    container = soup.select_one(
        "#detailBulletsWrapper_feature_div, #detailBullets_feature_div, "
        "#productDetails_detailBullets_sections1, #prodDetails"
    )
    bsr_block = None
    if container is not None:
        for li in container.select("li, tr"):
            if "Best Sellers Rank" in li.get_text(" ", strip=True):
                bsr_block = li
                break
    if bsr_block is None:
        for el in soup.find_all(string=re.compile(r"Best Sellers Rank", re.IGNORECASE)):
            bsr_block = el.find_parent(["li", "tr", "td"])
            if bsr_block:
                break
    if bsr_block is None:
        return out

    raw_html = str(bsr_block).replace("&nbsp;", " ")
    text_block = re.sub(r"<[^>]+>", " ", raw_html)
    text_block = re.sub(r"\s+", " ", text_block).strip()

    for m in re.finditer(r"#([\d,]+)\s+in\s+(.+?)(?=\s*(?:#\d|See Top|\(See|$))", text_block):
        rank = m.group(1).strip()
        cat = m.group(2).strip().rstrip(".,;:")
        cat = re.sub(r"\s*\(.*$", "", cat).strip()
        cat = html.unescape(cat)
        if rank and cat:
            out.append({"rank": f"#{rank}", "category": cat})

    return out


def extract_variations(soup: BeautifulSoup) -> Dict[str, Dict[str, Any]]:
    out = {
        "colors": {"count": 0, "values": []},
        "sizes": {"count": 0, "values": []},
    }

    color_row = soup.select_one("#inline-twister-row-color_name, #variation_color_name")
    if color_row:
        names: List[str] = []
        for el in color_row.select("li[data-defaultasin], li[data-csa-c-asin], li.swatchSelect, li.swatchAvailable"):
            label = _attr(el, "title") or _attr(el, "aria-label")
            label = re.sub(r"^Click to select ", "", label).strip()
            if label and not re.match(r"(Selected|There are|See \d+ option)", label, flags=re.IGNORECASE):
                names.append(label)
        if not names:
            for el in color_row.select("img[alt]"):
                t = _attr(el, "alt").strip()
                if t and t.lower() not in ("color", "swatch", ""):
                    names.append(t)
        if not names:
            for el in color_row.select(".swatch-title-text-display, .selection"):
                t = _text(el)
                if t:
                    names.append(t)
        clean = []
        for n in names:
            if re.search(r"(selected color|tap to|there are|see \d+ option)", n, flags=re.IGNORECASE):
                continue
            clean.append(n)
        clean = [n for n in dict.fromkeys(clean) if n]
        out["colors"] = {"count": len(clean), "values": clean}

    size_row = soup.select_one("#inline-twister-row-size_name, #variation_size_name")
    if size_row:
        names = []
        for el in size_row.select("[role='radio'], button, li"):
            t = _text(el)
            if not t:
                continue
            if re.fullmatch(r"[\w./\- ]{1,16}", t) and t.lower() not in ("size", "size chart"):
                names.append(t)
        names = [n for n in dict.fromkeys(names) if n]
        out["sizes"] = {"count": len(names), "values": names}

    return out


def extract_bullets(soup: BeautifulSoup, limit: int = 8) -> List[str]:
    items: List[str] = []
    container = soup.select_one(
        "#featurebullets_feature_div, #feature-bullets, "
        "#productFactsDesktop_feature_div, #productFactsDesktopExpander"
    )
    if container is None:
        return items
    for li in container.select("li, .a-list-item"):
        t = _text(li)
        if not t:
            continue
        if t.lower().startswith("make sure this fits"):
            continue
        if t.lower() in ("about this item",):
            continue
        if t not in items:
            items.append(t)
        if len(items) >= limit:
            break
    return items


# 不同品类/卖家上传的参数表结构差异极大，这里做"格式自适应"：
#   - 标签别名归一：把含义相同、写法不同的标签折叠到同一规范键，避免重复行
#     （Brand / Brand Name / Manufacturer 都视为同一项）。
# 注意：归一只用于"去重判定"，最终展示仍保留首次出现的原始标签文本。
_SPEC_ALIAS: Dict[str, str] = {
    "brand name": "brand",
    "manufacturer": "brand",
    "item dimensions l x w x h": "product dimensions",
    "item dimensions lxwxh": "product dimensions",
    "package dimensions": "product dimensions",
    "manufacturer part number": "model number",
    "part number": "model number",
    "item model number": "model number",
    "item weight": "item weight",
    "product weight": "item weight",
    "weight": "item weight",
}

# 这些标签属于"非参数"噪声（已在 metadata 其它字段单独记录，或对竞品分析无意义），跳过。
_SPEC_SKIP: set = {
    "customer reviews",
    "best sellers rank",
    "asin",
    "date first available",
    "warranty & support",
    "feedback",
    "country of origin",
    "is discontinued by manufacturer",
}


def extract_specs(soup: BeautifulSoup, limit: int = 30) -> List[Dict[str, str]]:
    """解析产品基本参数，输出有序的 [{label, value}] 列表（**格式自适应**）。

    亚马逊不同品类/卖家的参数区结构差异很大，这里依次扫描 4 类常见布局，
    按出现顺序合并、按"标签别名归一"去重；**任何一类都没有时返回空列表**
    （由上层决定是否展示，绝不臆造参数）：
      1) 产品概览表 po-*：<tr class="po-xxx"> → 加粗 span 标签 + po-break-word 值
         （顶部 Brand / Power Source / Item Weight / Maximum Pressure / UPC 等）。
      2) Product information 键值表：table.prodDetTable / table.a-keyvalue 的 th/td
         （技术规格 Technical Details + 附加信息 Additional Information）。
      3) Detail bullets 列表：#detailBullets_feature_div 下 li 内
         "<span 加粗>Label :</span> <span>Value</span>" 结构（书籍/3C 常见）。
      4) Product facts 网格：#productFactsDesktop_feature_div 的左右两列 span
         （新版 A11Y 详情卡）。
    """
    specs: List[Dict[str, str]] = []
    seen: set = set()

    def _push(label: str, value: str) -> None:
        label = (label or "").strip().rstrip(":").strip()
        value = re.sub(r"\s+", " ", (value or "").strip())
        if not label or not value:
            return
        key_raw = label.lower()
        if key_raw in _SPEC_SKIP:
            return
        # 别名归一后判重，折叠 Brand / Brand Name / Manufacturer 等同义项
        key = _SPEC_ALIAS.get(key_raw, key_raw)
        if key in seen:
            return
        if len(value) > 200:  # 过滤退化的超长描述
            return
        seen.add(key)
        specs.append({"label": label, "value": value})

    # 1) 产品概览表 po-*
    for tr in soup.select('tr[class*="po-"]'):
        bold = tr.select_one("span.a-text-bold") or tr.select_one("td:first-child span")
        val = tr.select_one("span.po-break-word")
        if val is None:
            tds = tr.select("td")
            val = tds[1].select_one("span") if len(tds) >= 2 else None
        if bold is not None and val is not None:
            _push(_text(bold), _text(val))
        if len(specs) >= limit:
            return specs

    # 2) Product information 键值表（技术规格 + 附加信息）
    for table in soup.select("table.prodDetTable, table.a-keyvalue"):
        for row in table.select("tr"):
            th = row.select_one("th")
            td = row.select_one("td")
            if th is None or td is None:
                continue
            _push(_text(th), _text(td))
            if len(specs) >= limit:
                return specs

    # 3) Detail bullets 列表（"Label : Value" 结构）
    db = soup.select_one("#detailBullets_feature_div")
    if db is not None:
        for li in db.select("li"):
            spans = li.select("span.a-list-item > span") or li.select("span")
            if len(spans) >= 2:
                label = _text(spans[0]).replace("\u200e", "").replace("\u200f", "")
                value = _text(spans[1])
                _push(label, value)
            if len(specs) >= limit:
                return specs

    # 4) Product facts 网格（新版详情卡：左列标签 + 右列值）
    pf = soup.select_one("#productFactsDesktop_feature_div, #productFacts_feature_div")
    if pf is not None:
        for row in pf.select(".a-fixed-left-grid, .product-facts-detail"):
            left = row.select_one(".a-col-left, .a-fixed-left-grid-col.a-col-left")
            right = row.select_one(".a-col-right, .a-fixed-left-grid-col.a-col-right")
            if left is not None and right is not None:
                _push(_text(left), _text(right))
            if len(specs) >= limit:
                return specs

    return specs


def derive_specs_from_bullets(bullets: List[str], limit: int = 10) -> List[Dict[str, str]]:
    """从 Amazon bullet 中抽取可验证的产品参数，作为参数表缺失时的兜底。

    只提取带明确数值、配置或配件名的事实，避免把卖点文案改写成臆造参数。
    """
    joined = " ".join(bullets or [])
    specs: List[Dict[str, str]] = []
    seen: set[str] = set()

    def _push(label: str, value: str) -> None:
        value = re.sub(r"\s+", " ", (value or "").strip(" .;"))
        if not label or not value:
            return
        key = label.lower()
        if key in seen:
            return
        if len(value) > 120:
            return
        seen.add(key)
        specs.append({"label": label, "value": value})

    m = re.search(r"(\d+)\s+detachable batteries", joined, flags=re.I)
    if m:
        _push("Battery configuration", f"{m.group(1)} detachable batteries")

    m = re.search(r"(\d+\s*-\s*\d+)\s*mins?\s+of\s+continuous\s+use", joined, flags=re.I)
    if m:
        _push("Runtime", f"{m.group(1).replace(' ', '')} mins continuous use")
    else:
        m = re.search(r"(\d+\s*-\s*\d+)\s*mins?\s+runtime", joined, flags=re.I)
        if m:
            _push("Runtime", f"{m.group(1).replace(' ', '')} mins")

    m = re.search(r"output\s+of\s+([0-9VvAa/~\-\s]+)\)", joined, flags=re.I)
    if m:
        _push("Charging input", m.group(1).replace(" ", ""))
    elif re.search(r"direct charge from USB", joined, flags=re.I):
        _push("Charging method", "USB direct charge")

    m = re.search(r"([0-9.]+)\s*gal/min\s*\(([0-9.]+)\s*L/min\)", joined, flags=re.I)
    if m:
        _push("Flow rate", f"{m.group(1)} gal/min ({m.group(2)} L/min)")

    m = re.search(r"weigh(?:s|ts)?\s+only\s+([0-9.]+\s*LB)", joined, flags=re.I)
    if m:
        _push("Item weight", m.group(1).upper().replace(" ", " "))

    accessories: List[str] = []
    for text, name in (
        ("mesh storage bag", "mesh storage bag"),
        ("suction cup", "suction cup"),
        ("hook", "hook"),
        ("water filter", "water filter"),
        ("O-ring", "O-ring"),
        ("charging cable", "charging cable"),
    ):
        if re.search(re.escape(text), joined, flags=re.I):
            accessories.append(name)
    if accessories:
        _push("Included accessories", ", ".join(accessories))

    uses: List[str] = []
    for pat, name in (
        ("camping", "camping"),
        ("pet cleaning", "pet cleaning"),
        ("car washing", "car washing"),
        ("plants watering", "plant watering"),
        ("backyard cleaning", "backyard cleaning"),
    ):
        if re.search(pat, joined, flags=re.I):
            uses.append(name)
    if uses:
        _push("Use cases", ", ".join(uses[:5]))

    return specs[:limit]


def merge_specs(base: List[Dict[str, str]], extra: List[Dict[str, str]], limit: int = 30) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    seen: set[str] = set()
    for item in (base or []) + (extra or []):
        label = re.sub(r"\s+", " ", str(item.get("label") or "").strip())
        value = re.sub(r"\s+", " ", str(item.get("value") or "").strip())
        if not label or not value:
            continue
        key_raw = label.lower().rstrip(":")
        key = _SPEC_ALIAS.get(key_raw, key_raw)
        if key in seen:
            continue
        seen.add(key)
        merged.append({"label": label, "value": value})
        if len(merged) >= limit:
            break
    return merged


def _parse_star_from_alt(alt_text: str) -> Optional[float]:
  """从 'X out of 5 stars' 文本中解析星级。"""
  if not alt_text:
    return None
  m = re.search(r"([0-9.]+)\s*out\s*of\s*5", alt_text, flags=re.IGNORECASE)
  if not m:
    return None
  try:
    return float(m.group(1))
  except ValueError:
    return None


def extract_reviews(soup: BeautifulSoup) -> Dict[str, Any]:
  """从产品页 HTML 解析评论预览块（一般 8 条 + 星级直方图）。

  注意：产品页只展示头部精选评论，**不是全量评论**。完整评论需访问
  /product-reviews/<ASIN> 页（涉及二次抓取与风控）——本函数刻意保守，
  仅从已抓取的 fetched_page.html 中"零再请求"地抽取可见内容。

  Returns:
    {
      "available": bool,
      "histogram": [{star: 5, percent: 75}, ...],
      "items": [
        {
          "id": "R28MJO5T18B0SG",
          "title": "Lovely!",
          "body": "...",
          "stars": 5.0,
          "verified": True,
          "reviewer": "KMZ",
          "date_text": "Reviewed in the United States on April 12, 2026",
          "variation": {"size": "Medium", "color": "White"}
        },
        ...
      ],
      "positive_count": 6,
      "critical_count": 2
    }
  """
  out: Dict[str, Any] = {
    "available": False,
    "histogram": [],
    "items": [],
    "positive_count": 0,
    "critical_count": 0,
  }

  hist_root = soup.select_one("#cm_cr_dp_d_rating_histogram")
  if hist_root:
    for link in hist_root.select(".a-link-normal[aria-label*='star']"):
      label = (link.get("aria-label") or "").strip()
      m = re.match(r"\s*([\d.]+)\s*percent\s+of\s+reviews\s+have\s+([\d.]+)\s+stars?", label, flags=re.IGNORECASE)
      if m:
        try:
          percent = float(m.group(1))
          star = int(float(m.group(2)))
          out["histogram"].append({"star": star, "percent": percent})
        except ValueError:
          continue

  for r in soup.select('div[data-hook="review"]'):
    rid = (r.get("id") or "").strip()

    star_node = r.select_one('i[data-hook="review-star-rating"] span.a-icon-alt') \
      or r.select_one("i.a-icon-star span.a-icon-alt")
    stars = _parse_star_from_alt(_text(star_node)) if star_node else None

    title_node = r.select_one('[data-hook="reviewTitle"]') \
      or r.select_one("[class*='review-title']")
    title = _text(title_node)

    body_node = r.select_one('[data-hook="review-body"]') \
      or r.select_one("[class*='review-text']")
    body_raw = _text(body_node)
    body = re.sub(
      r"^(Brief content visible[^.]+\.\s*Full content visible[^.]+\.\s*)+",
      "",
      body_raw,
      flags=re.IGNORECASE,
    ).strip()

    verified = r.select_one('[data-hook="avp-badge"]') is not None

    reviewer_node = r.select_one(".a-profile-name")
    reviewer = _text(reviewer_node)

    date_node = r.select_one('[data-hook="review-date"]')
    date_text = _text(date_node)

    variation: Dict[str, str] = {}
    var_strip = r.select_one('[data-hook="format-strip"]')
    if var_strip:
      for sp in var_strip.select("span.a-size-base.a-color-secondary"):
        t = _text(sp)
        for label in ("Size", "Color", "Style", "Pattern"):
          m = re.match(rf"\s*{label}\s*:\s*(.+)", t, flags=re.IGNORECASE)
          if m:
            variation[label.lower()] = m.group(1).strip()

    if not (title or body):
      continue
    out["items"].append({
      "id": rid,
      "title": title,
      "body": body,
      "stars": stars,
      "verified": verified,
      "reviewer": reviewer,
      "date_text": date_text,
      "variation": variation,
    })

  for it in out["items"]:
    if it["stars"] is None:
      continue
    if it["stars"] >= 4:
      out["positive_count"] += 1
    elif it["stars"] <= 3:
      out["critical_count"] += 1

  out["available"] = bool(out["items"] or out["histogram"])
  return out


def load_extract_report(html_dir: Path) -> Dict[str, Any]:
    """Try to read sibling report.json produced by amazon-image-extractor."""
    out: Dict[str, Any] = {
        "gallery_count": None,
        "aplus_module_count": None,
        "aplus_image_count": None,
        "video_cover_count": None,
    }
    report_path = html_dir / "report.json"
    if not report_path.exists():
        return out
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return out

    out["gallery_count"] = (data.get("gallery") or {}).get("downloaded_count")
    aplus = data.get("aplus") or {}
    out["aplus_module_count"] = aplus.get("group_count")
    out["aplus_image_count"] = aplus.get("downloaded_count")
    selectors_hit = (data.get("selectors_hit") or {}).get("aplus") or {}
    out["aplus_module_top_level"] = selectors_hit.get("aplus_module_top_level")
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抽取亚马逊商品页元数据（HTML 离线解析）")
    parser.add_argument("--html", required=True, help="本地 fetched_page.html 路径")
    parser.add_argument("--url", default="", help="商品页 URL（用于 ASIN 兜底）")
    parser.add_argument("--output", default="", help="输出 JSON 路径，默认与 html 同目录的 metadata.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    html_path = Path(args.html).expanduser().resolve()
    if not html_path.exists():
        print(json.dumps({"success": False, "error": f"html_not_found: {html_path}"}, ensure_ascii=False))
        return 1

    soup = _read_html(html_path)

    out_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else html_path.parent / "metadata.json"
    )
    # source_html 写成相对 metadata.json 所在目录的路径（通常二者同目录，即 fetched_page.html），
    # 避免泄露生成机器的绝对路径、保证目录整体转发给他人后仍可用。
    try:
        source_html_rel = Path(os.path.relpath(html_path, out_path.parent)).as_posix()
    except ValueError:
        source_html_rel = html_path.name

    bullets = extract_bullets(soup)
    specs = merge_specs(extract_specs(soup), derive_specs_from_bullets(bullets))

    metadata: Dict[str, Any] = {
        "success": True,
        "source_html": source_html_rel,
        "source_url": args.url,
        "asin": extract_asin(soup, fallback_url=args.url),
        "title": extract_title(soup),
        "brand": extract_brand(soup),
        "rating": extract_rating(soup),
        "rating_count": extract_rating_count(soup),
        "price": extract_price(soup),
        "category_rank": extract_category_rank(soup),
        "variations": extract_variations(soup),
        "bullets": bullets,
        "specs": specs,
        "reviews": extract_reviews(soup),
        "media": load_extract_report(html_path.parent),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    metadata["output"] = str(out_path)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
