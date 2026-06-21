#!/usr/bin/env python3
"""Fetch Amazon's global star distribution widget and patch metadata.json.

The product detail page often contains only the average rating plus a popover
URL for "Customer Reviews Ratings Summary". The actual 5/4/3/2/1-star
distribution is loaded from that widget. This script fetches the widget using
the saved product HTML as the source of truth, parses the histogram, and writes
it back to metadata.json under reviews.histogram.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch global Amazon star histogram widget and patch metadata.json."
    )
    p.add_argument("--html", required=True, help="Saved fetched_page.html")
    p.add_argument("--metadata", required=True, help="metadata.json to patch")
    p.add_argument("--url", default="", help="Product URL fallback for base domain")
    p.add_argument("--widget-html", default="", help="Optional saved review popover widget HTML; parse this instead of fetching.")
    p.add_argument("--timeout", type=int, default=20)
    return p.parse_args()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _parse_popover_url(product_html: str) -> str:
    soup = BeautifulSoup(product_html, "html.parser")
    pop = soup.select_one("[data-a-popover*='average-customer-review/popover']")
    if pop:
        raw = pop.get("data-a-popover") or ""
        raw = html.unescape(raw)
        try:
            data = json.loads(raw)
            url = data.get("url") or ""
            if url:
                return str(url)
        except Exception:
            m = re.search(r'"url"\s*:\s*"([^"]+)"', raw)
            if m:
                return m.group(1)

    m = re.search(
        r'average-customer-review/popover[^"\']+',
        html.unescape(product_html),
        flags=re.IGNORECASE,
    )
    return m.group(0) if m else ""


def _parse_histogram(widget_html: str) -> list[dict[str, float | int]]:
    soup = BeautifulSoup(widget_html, "html.parser")
    out: list[dict[str, float | int]] = []
    seen: set[int] = set()

    # Common widget aria-label variants:
    # - "5 stars represent 73% of rating" (current popover)
    # - "70 percent of reviews have 5 stars" (older histogram)
    nodes = list(soup.select(".histogram-row-container[aria-label]"))
    if not nodes:
        nodes = list(soup.select("[aria-label*='reviews'][aria-label*='star']"))
    for el in nodes:
        label = html.unescape(el.get("aria-label") or "")
        m_current = re.search(
            r"([1-5])\s+stars?\s+represent\s+([0-9]+(?:\.[0-9]+)?)\s*%\s+of\s+rating",
            label,
            flags=re.IGNORECASE,
        )
        if m_current:
            star = int(m_current.group(1))
            percent = float(m_current.group(2))
        else:
            m = re.search(
            r"([0-9]+(?:\.[0-9]+)?)\s*percent\s+of\s+reviews\s+have\s+([1-5])\s+stars?",
            label,
            flags=re.IGNORECASE,
            )
            if m:
                percent = float(m.group(1))
                star = int(m.group(2))
            else:
                m = re.search(
                    r"([1-5])\s+stars?.*?([0-9]+(?:\.[0-9]+)?)\s*%",
                    label,
                    flags=re.IGNORECASE,
                )
                if m:
                    star = int(m.group(1))
                    percent = float(m.group(2))
                else:
                    continue
        if star not in seen:
            out.append({"star": star, "percent": percent})
            seen.add(star)

    if len(out) < 5:
        text = soup.get_text(" ", strip=True)
        # Fallback snippets like "5 star 70% 4 star 16% ..."
        for star, pct in re.findall(
            r"([1-5])\s*star[s]?\s*([0-9]+(?:\.[0-9]+)?)\s*%",
            text,
            flags=re.IGNORECASE,
        ):
            s = int(star)
            if s not in seen:
                out.append({"star": s, "percent": float(pct)})
                seen.add(s)

    out.sort(key=lambda row: -int(row["star"]))
    return out


def main() -> int:
    args = parse_args()
    html_path = Path(args.html).expanduser().resolve()
    metadata_path = Path(args.metadata).expanduser().resolve()
    if not html_path.is_file():
        print(json.dumps({"success": False, "error": f"html_not_found: {html_path}"}, ensure_ascii=False))
        return 1
    if not metadata_path.is_file():
        print(json.dumps({"success": False, "error": f"metadata_not_found: {metadata_path}"}, ensure_ascii=False))
        return 1

    product_html = _read(html_path)
    full_url = ""
    if args.widget_html:
        widget_path = Path(args.widget_html).expanduser().resolve()
        if not widget_path.is_file():
            print(json.dumps({"success": False, "error": f"widget_html_not_found: {widget_path}"}, ensure_ascii=False))
            return 2
        widget_text = widget_path.read_text(encoding="utf-8", errors="ignore")
        full_url = str(widget_path)
    else:
        widget_url = _parse_popover_url(product_html)
        if not widget_url:
            print(json.dumps({"success": False, "error": "review_popover_url_not_found"}, ensure_ascii=False))
            return 2

        base = args.url or "https://www.amazon.com/"
        full_url = urljoin(base, html.unescape(widget_url))
        try:
            resp = requests.get(full_url, headers=DEFAULT_HEADERS, timeout=args.timeout)
            resp.raise_for_status()
            widget_text = resp.text
        except Exception as exc:
            print(json.dumps({"success": False, "error": f"fetch_failed: {exc}", "url": full_url}, ensure_ascii=False))
            return 3

    hist = _parse_histogram(widget_text)
    if not hist:
        debug_path = metadata_path.with_name("review_histogram_widget.html")
        debug_path.write_text(widget_text, encoding="utf-8")
        print(json.dumps({
            "success": False,
            "error": "histogram_not_found_in_widget",
            "url": full_url,
            "debug_html": str(debug_path),
        }, ensure_ascii=False))
        return 4

    pct_total = sum(float(row["percent"]) for row in hist)
    if len(hist) != 5 or not (95 <= pct_total <= 105):
        debug_path = metadata_path.with_name("review_histogram_widget.html")
        debug_path.write_text(widget_text, encoding="utf-8")
        print(json.dumps({
            "success": False,
            "error": "histogram_failed_sanity_check",
            "histogram": hist,
            "percent_total": round(pct_total, 2),
            "url": full_url,
            "debug_html": str(debug_path),
        }, ensure_ascii=False))
        return 5

    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    reviews = metadata.setdefault("reviews", {})
    reviews["histogram"] = hist
    reviews["available"] = True
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "success": True,
        "url": full_url,
        "histogram": hist,
        "output": str(metadata_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
