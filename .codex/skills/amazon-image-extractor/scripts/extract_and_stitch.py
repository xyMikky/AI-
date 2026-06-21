import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from PIL import Image


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MAX_CANVAS_DIM = 65000


def _parse_html(text: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(text, "lxml")
    except Exception:
        return BeautifulSoup(text, "html.parser")


def load_html(html_path: Path) -> Tuple[str, BeautifulSoup]:
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    return text, _parse_html(text)


def fetch_html(url: str, timeout: int, user_agent: str) -> Tuple[str, BeautifulSoup, str]:
    """
    Fetch an Amazon product page using a browser-like session.

    Returns: (html_text, soup, final_url)
    """
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
    )

    response = session.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()

    response.encoding = response.encoding or "utf-8"
    text = response.text
    return text, _parse_html(text), response.url


def detect_anti_bot(html_text: str) -> Optional[str]:
    """
    Detect common Amazon anti-bot pages. Returns a short reason string when triggered.
    """
    if not html_text:
        return "empty_response"
    sample = html_text[:6000].lower()
    if "to discuss automated access to amazon data please contact" in sample:
        return "robot_check_page"
    if "/errors/validatecaptcha" in sample or "captcha" in sample and "amazon" in sample and "robot" in sample:
        return "captcha_page"
    if "sorry, we just need to make sure you're not a robot" in sample:
        return "robot_check_page"
    return None


def normalize_url(url: str, base_url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = urljoin(base_url, url)
    elif not url.startswith("http://") and not url.startswith("https://"):
        # Local relative links in saved html (./xxx_files/...) are not stable web URLs.
        # Skip them to avoid polluting extraction with page asset cache files.
        return ""

    parsed = urlparse(url)
    clean = parsed._replace(fragment="")
    return urlunparse(clean)


def upgrade_amazon_image_url(url: str) -> str:
    if not url:
        return ""
    upgraded = re.sub(r"\._[^./]+\.", ".", url)
    upgraded = upgraded.replace("%7C", "|")
    return upgraded


def parse_dynamic_image(value: str) -> List[str]:
    if not value:
        return []
    raw = html.unescape(value)
    urls: List[str] = []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            urls.extend(list(data.keys()))
    except Exception:
        pass
    return urls


def parse_srcset(value: str) -> List[str]:
    if not value:
        return []
    candidates = []
    for item in value.split(","):
        part = item.strip().split(" ")[0].strip()
        if part:
            candidates.append(part)
    return candidates


def extract_urls_from_tag(tag, base_url: str) -> List[str]:
    urls: List[str] = []
    for attr in ("data-old-hires", "data-src", "src", "data-srcset", "srcset"):
        val = tag.get(attr)
        if not val:
            continue
        if attr in ("srcset", "data-srcset"):
            urls.extend(parse_srcset(val))
        else:
            urls.append(val)

    dyn = tag.get("data-a-dynamic-image")
    if dyn:
        urls.extend(parse_dynamic_image(dyn))

    normalized = []
    for u in urls:
        n = normalize_url(upgrade_amazon_image_url(u), base_url)
        if n:
            normalized.append(n)
    return normalized


def unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def media_key_from_url(url: str) -> str:
    """
    Amazon image URLs of the same asset may differ by size suffix.
    Example:
      .../81abcXYZ._AC_SL1500_.jpg
      .../81abcXYZ._AC_SY355_.jpg
    They should share one media key: 81abcXYZ
    """
    path = urlparse(url).path
    name = Path(path).name
    if not name:
        return url
    stem = name.rsplit(".", 1)[0]
    key = stem.split("._")[0]
    return key or stem or url


def unique_by_media_key(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        k = media_key_from_url(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def detect_base_url(html_text: str, soup: BeautifulSoup) -> str:
    base_tag = soup.find("base", href=True)
    if base_tag:
        return base_tag["href"]
    og_url = soup.find("meta", attrs={"property": "og:url"})
    if og_url and og_url.get("content"):
        return og_url["content"]
    m = re.search(r"https://www\.amazon\.[a-z.]+/[^\"' <]+", html_text)
    if m:
        return m.group(0)
    return "https://www.amazon.com/"


def detect_current_asin(html_text: str, base_url: str) -> str:
    for text in (base_url, html_text):
        m = re.search(r"/dp/([A-Z0-9]{10})", text, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper()
    m = re.search(r'"asin"\s*:\s*"([A-Z0-9]{10})"', html_text, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return ""


def regex_gallery_fallback(html_text: str, base_url: str) -> List[str]:
    urls = []
    for pat in (
        r'"hiRes":"(https:[^"]+)"',
        r'"large":"(https:[^"]+)"',
        r'"mainUrl":"(https:[^"]+)"',
    ):
        for hit in re.findall(pat, html_text):
            hit = hit.replace("\\/", "/")
            n = normalize_url(upgrade_amazon_image_url(hit), base_url)
            if n:
                urls.append(n)
    return unique_keep_order(urls)


def extract_gallery_from_color_images_block(
    html_text: str, base_url: str, allowed_variants: Optional[set] = None
) -> List[str]:
    """
    Prefer Amazon media state block: colorImages.initial
    This maps to the left-side gallery for current selected variant.
    """
    start = html_text.find("'colorImages': { 'initial': [")
    end = -1
    if start != -1:
        end = html_text.find("'colorToAsin'", start)
    if start == -1 or end == -1:
        start = html_text.find('"colorImages":{"initial":[')
        if start != -1:
            end = html_text.find('"colorToAsin"', start)

    if start == -1 or end == -1 or end <= start:
        return []

    block = html_text[start:end]
    block = block.replace('\\"', '"').replace("\\/", "/")
    hires_items: List[Tuple[str, str]] = []
    large_items: List[Tuple[str, str]] = []

    for hit, variant in re.findall(
        r'"hiRes"\s*:\s*"([^"]+)".*?"variant"\s*:\s*"([^"]+)"', block, flags=re.S
    ):
        if allowed_variants and variant not in allowed_variants:
            continue
        n = normalize_url(upgrade_amazon_image_url(hit), base_url)
        if n:
            hires_items.append((n, variant))

    for hit, variant in re.findall(
        r'"large"\s*:\s*"([^"]+)".*?"variant"\s*:\s*"([^"]+)"', block, flags=re.S
    ):
        if allowed_variants and variant not in allowed_variants:
            continue
        n = normalize_url(upgrade_amazon_image_url(hit), base_url)
        if n:
            large_items.append((n, variant))

    # Prefer hiRes as canonical gallery source. Use large only when hiRes is absent.
    urls = [u for u, _ in hires_items] if hires_items else [u for u, _ in large_items]

    max_alts = None
    m = re.search(r'"maxAlts"\s*:\s*(\d+)', html_text)
    if not m:
        m = re.search(r"'maxAlts'\s*:\s*(\d+)", html_text)
    if m:
        try:
            max_alts = int(m.group(1))
        except Exception:
            max_alts = None

    urls = unique_keep_order(urls)
    if max_alts and max_alts > 0:
        urls = urls[: max_alts + 1]
    return urls


def detect_altimage_variants(soup: BeautifulSoup) -> set:
    variants = set()
    for li in soup.select("#altImages li.imageThumbnail"):
        classes = li.get("class", [])
        for cls in classes:
            if cls.startswith("variant-"):
                variants.add(cls.replace("variant-", ""))
    return variants


def extract_gallery_images(
    html_text: str, soup: BeautifulSoup, base_url: str
) -> Tuple[List[str], Dict[str, int]]:
    selectors_hit: Dict[str, int] = {}
    urls: List[str] = []
    allowed_variants = detect_altimage_variants(soup)

    # Priority 1: parse the canonical colorImages.initial gallery payload.
    color_images_urls = extract_gallery_from_color_images_block(
        html_text, base_url, allowed_variants=allowed_variants or None
    )
    selectors_hit["colorImages.initial"] = len(color_images_urls)

    if color_images_urls:
        urls = unique_by_media_key(unique_keep_order(color_images_urls))
        selectors = [
            "#landingImage",
            "#altImages li.image.item img",
            "#altImages img",
            "#altImages [data-old-hires]",
            "#altImages [data-a-dynamic-image]",
        ]
        for sel in selectors:
            selectors_hit[sel] = 0
        return urls, selectors_hit

    selectors = [
        "#landingImage",
        "#altImages li.image.item img",
        "#altImages img",
        "#altImages [data-old-hires]",
        "#altImages [data-a-dynamic-image]",
    ]
    for sel in selectors:
        tags = soup.select(sel)
        selectors_hit[sel] = len(tags)
        for tag in tags:
            urls.extend(extract_urls_from_tag(tag, base_url))

    urls = unique_by_media_key(unique_keep_order(urls))

    # Priority 3: broad regex fallback only when previous strategies are empty
    if not urls:
        urls.extend(regex_gallery_fallback(html_text, base_url))
    urls = unique_by_media_key(unique_keep_order(urls))
    return urls, selectors_hit


APLUS_MEDIA_URL_RE = re.compile(
    r"https://m\.media-amazon\.com/images/S/aplus-media-library-service-media/[^\"'\s)]+"
)
APLUS_VIDEO_IMAGE_FIELD_RE = re.compile(
    r'"(?:imageUrl|posterUrl|posterImage|thumbnailUrl|videoIngressATFSlateThumbURL)"\s*:\s*"([^"]+)"',
    flags=re.IGNORECASE,
)


def _make_aplus_tag_filter(current_asin: str):
    """Return a callable(tag) -> bool, filtering placeholders and cross-ASIN navigations."""

    def is_tag_allowed(tag) -> bool:
        for raw in (
            tag.get("src", ""),
            tag.get("data-src", ""),
            tag.get("srcset", ""),
            tag.get("data-srcset", ""),
        ):
            low = (raw or "").lower()
            if "grey-pixel" in low or low.endswith(".gif"):
                return False

        if current_asin:
            a = tag.find_parent("a", href=True)
            if a:
                href = a.get("href", "")
                if "ref=emc_p_m_5_" in href:
                    return False
                m = re.search(r"/dp/([A-Z0-9]{10})", href, flags=re.IGNORECASE)
                if m and m.group(1).upper() != current_asin:
                    return False

            for attr in ("data-asin", "asin"):
                p = tag.find_parent(attrs={attr: True})
                if p:
                    asin = str(p.get(attr, "")).upper()
                    if re.fullmatch(r"[A-Z0-9]{10}", asin) and asin != current_asin:
                        return False

        return True

    return is_tag_allowed


def _is_script_url_relevant(context: str) -> bool:
    """A+ JS configs of comparison-table / cross-product cards must be skipped."""
    ctx = context.lower()
    if "emc_p_m_5" in ctx or "comparison-table" in ctx or "_atc" in ctx:
        return False
    return True


def _collect_video_cover_urls_from_module(module, base_url: str) -> List[str]:
    """
    Collect video-cover style image URLs from A+ script states.

    Some A+ video modules don't expose <img> tags and only keep the clickable
    cover image in JSON config fields such as "imageUrl".
    """
    urls: List[str] = []
    for script in module.find_all("script"):
        raw = script.string or script.get_text() or ""
        if not raw:
            continue
        for m in APLUS_VIDEO_IMAGE_FIELD_RE.finditer(raw):
            n = normalize_url(upgrade_amazon_image_url(m.group(1)), base_url)
            if n:
                urls.append(n)
    return unique_by_media_key(unique_keep_order(urls))


def _collect_module_urls(module, base_url: str, is_tag_allowed) -> List[str]:
    """Collect every A+ image URL inside a single aplus-module, preserving order."""
    urls: List[str] = []

    for tag in module.find_all(["img"]):
        if not is_tag_allowed(tag):
            continue
        urls.extend(extract_urls_from_tag(tag, base_url))

    for tag in module.find_all(attrs={"data-src": True}):
        if not is_tag_allowed(tag):
            continue
        urls.extend(extract_urls_from_tag(tag, base_url))

    inner_html = str(module)
    for match in APLUS_MEDIA_URL_RE.finditer(inner_html):
        start = match.start()
        context = inner_html[max(0, start - 220) : min(len(inner_html), match.end() + 220)]
        if not _is_script_url_relevant(context):
            continue
        urls.append(match.group(0))

    # A+ video module cover image (play-slate) is often only in script JSON.
    urls.extend(_collect_video_cover_urls_from_module(module, base_url))

    return unique_by_media_key(unique_keep_order(urls))


def extract_aplus_image_groups(
    soup: BeautifulSoup, base_url: str
) -> Tuple[List[List[str]], Dict[str, int]]:
    """
    Return A+ images grouped by visual module (1 carousel = 1 group, 1 single-image card = 1 group).

    Groups follow page order. Empty modules are dropped.
    """
    selectors_hit: Dict[str, int] = {}
    current_asin = detect_current_asin(str(soup), base_url)
    is_tag_allowed = _make_aplus_tag_filter(current_asin)

    root = soup.select_one("#aplus_feature_div") or soup.select_one("#aplus")
    if not root:
        selectors_hit["aplus_root"] = 0
        return [], selectors_hit
    selectors_hit["aplus_root"] = 1

    top_level_modules = []
    for node in root.select(".aplus-module"):
        if node.find_parent(class_="aplus-module") is None:
            top_level_modules.append(node)
    selectors_hit["aplus_module_top_level"] = len(top_level_modules)

    groups: List[List[str]] = []
    seen_media_keys = set()

    if top_level_modules:
        for module in top_level_modules:
            urls = _collect_module_urls(module, base_url, is_tag_allowed)
            deduped: List[str] = []
            for u in urls:
                k = media_key_from_url(u)
                if k in seen_media_keys:
                    continue
                seen_media_keys.add(k)
                deduped.append(u)
            if deduped:
                groups.append(deduped)
        selectors_hit["groups_built_from_modules"] = len(groups)
        return groups, selectors_hit

    flat_urls: List[str] = []
    for tag in root.find_all(["img"]):
        if not is_tag_allowed(tag):
            continue
        flat_urls.extend(extract_urls_from_tag(tag, base_url))

    inner = str(root)
    for match in APLUS_MEDIA_URL_RE.finditer(inner):
        start = match.start()
        context = inner[max(0, start - 220) : min(len(inner), match.end() + 220)]
        if not _is_script_url_relevant(context):
            continue
        flat_urls.append(match.group(0))

    flat_urls = unique_by_media_key(unique_keep_order(flat_urls))
    selectors_hit["groups_built_from_fallback_flat"] = 1 if flat_urls else 0
    if flat_urls:
        groups = [[u] for u in flat_urls]
    return groups, selectors_hit


def extract_aplus_images(soup: BeautifulSoup, base_url: str) -> Tuple[List[str], Dict[str, int]]:
    """Backward-compatible flat list, derived from grouped extraction."""
    groups, hits = extract_aplus_image_groups(soup, base_url)
    flat = [u for grp in groups for u in grp]
    flat = unique_by_media_key(unique_keep_order(flat))
    hits["aplus_flat_count"] = len(flat)
    hits["aplus_group_count"] = len(groups)
    return flat, hits


def guess_ext(url: str, content_type: str) -> str:
    if content_type:
        if "png" in content_type.lower():
            return ".png"
        if "webp" in content_type.lower():
            return ".webp"
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in (".jpg", ".jpeg", ".png", ".webp"):
        return suffix
    return ".jpg"


def download_images(
    urls: List[str],
    output_dir: Path,
    min_width: int,
    timeout: int,
    user_agent: str,
    errors: List[str],
) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []
    hash_seen = set()
    headers = {"User-Agent": user_agent}

    for idx, url in enumerate(urls, 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            content = r.content
            digest = hashlib.md5(content).hexdigest()
            if digest in hash_seen:
                continue
            hash_seen.add(digest)

            ext = guess_ext(url, r.headers.get("Content-Type", ""))
            out_path = output_dir / f"{idx:02d}_{digest[:10]}{ext}"
            out_path.write_bytes(content)

            with Image.open(out_path) as im:
                if im.width < min_width:
                    out_path.unlink(missing_ok=True)
                    continue

            downloaded.append(out_path)
        except Exception as exc:
            errors.append(f"download_failed: {url} | {exc}")
    return downloaded


def download_image_groups(
    groups: List[List[str]],
    output_dir: Path,
    min_width: int,
    timeout: int,
    user_agent: str,
    errors: List[str],
) -> List[List[Path]]:
    """
    Download images preserving group structure.

    Files are named:  g{group:02d}_{idx:02d}_{digest}.{ext}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": user_agent}
    hash_seen = set()
    group_files: List[List[Path]] = []

    for g_idx, group in enumerate(groups, 1):
        files_in_group: List[Path] = []
        for i_idx, url in enumerate(group, 1):
            try:
                r = requests.get(url, headers=headers, timeout=timeout)
                r.raise_for_status()
                content = r.content
                digest = hashlib.md5(content).hexdigest()
                if digest in hash_seen:
                    continue
                hash_seen.add(digest)

                ext = guess_ext(url, r.headers.get("Content-Type", ""))
                out_path = output_dir / f"g{g_idx:02d}_{i_idx:02d}_{digest[:10]}{ext}"
                out_path.write_bytes(content)

                with Image.open(out_path) as im:
                    if im.width < min_width:
                        out_path.unlink(missing_ok=True)
                        continue

                files_in_group.append(out_path)
            except Exception as exc:
                errors.append(f"download_failed: {url} | {exc}")

        if files_in_group:
            group_files.append(files_in_group)

    return group_files


def _row_from_group(image_paths: List[Path], spacing: int) -> Optional[Image.Image]:
    """Compose one row by placing all images side-by-side, normalized to a common height.

    Uses an RGBA canvas with a fully transparent background, so any spacing
    between images becomes transparent in the final PNG.
    """
    if not image_paths:
        return None

    images: List[Image.Image] = []
    for p in image_paths:
        with Image.open(p) as im:
            images.append(im.convert("RGBA"))

    target_h = min(im.height for im in images)
    resized: List[Image.Image] = []
    for im in images:
        if im.height == target_h:
            resized.append(im)
            continue
        new_w = max(1, int(im.width * (target_h / im.height)))
        resized.append(im.resize((new_w, target_h), Image.Resampling.LANCZOS))

    total_w = sum(im.width for im in resized) + spacing * (len(resized) - 1)
    row = Image.new("RGBA", (total_w, target_h), color=(255, 255, 255, 0))
    x = 0
    for im in resized:
        row.paste(im, (x, 0), im)
        x += im.width + spacing
    return row


def stitch_grouped(
    group_files: List[List[Path]], out_path: Path, spacing: int
) -> Optional[Path]:
    """
    Each group becomes a horizontally-tiled row; rows are stacked vertically.

    Rows are NOT scaled to a common width — every image keeps its original size,
    so a single-image module renders at native width and a carousel of N images
    renders side-by-side at the same native size. The canvas is as wide as the
    widest row; narrower rows are left-aligned with white padding on the right.
    """
    if not group_files:
        return None

    rows: List[Image.Image] = []
    for group in group_files:
        row = _row_from_group(group, spacing)
        if row is not None:
            rows.append(row)

    if not rows:
        return None

    canvas_w = max(r.width for r in rows)
    total_h = sum(r.height for r in rows) + spacing * (len(rows) - 1)

    scale = min(1.0, MAX_CANVAS_DIM / canvas_w, MAX_CANVAS_DIM / total_h)
    if scale < 1.0:
        scaled: List[Image.Image] = []
        for r in rows:
            new_w = max(1, int(r.width * scale))
            new_h = max(1, int(r.height * scale))
            scaled.append(r.resize((new_w, new_h), Image.Resampling.LANCZOS))
        rows = scaled
        canvas_w = max(r.width for r in rows)
        total_h = sum(r.height for r in rows) + spacing * (len(rows) - 1)

    canvas = Image.new("RGBA", (canvas_w, total_h), color=(255, 255, 255, 0))
    y = 0
    for r in rows:
        canvas.paste(r, (0, y), r)
        y += r.height + spacing

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG")
    return out_path


def stitch_vertical(image_paths: List[Path], out_path: Path, spacing: int) -> Optional[Path]:
    if not image_paths:
        return None

    images = []
    for p in image_paths:
        with Image.open(p) as im:
            images.append(im.convert("RGBA"))

    target_w = max(im.width for im in images)
    resized = []
    for im in images:
        if im.width == target_w:
            resized.append(im)
            continue
        new_h = int(im.height * (target_w / im.width))
        resized.append(im.resize((target_w, new_h), Image.Resampling.LANCZOS))

    total_h = sum(im.height for im in resized) + spacing * (len(resized) - 1)

    # Keep a generous practical canvas cap to avoid runaway memory; PNG itself supports larger.
    scale = min(1.0, MAX_CANVAS_DIM / target_w, MAX_CANVAS_DIM / total_h)
    if scale < 1.0:
        scaled = []
        for im in resized:
            new_w = max(1, int(im.width * scale))
            new_h = max(1, int(im.height * scale))
            scaled.append(im.resize((new_w, new_h), Image.Resampling.LANCZOS))
        resized = scaled
        target_w = resized[0].width
        total_h = sum(im.height for im in resized) + spacing * (len(resized) - 1)

    canvas = Image.new("RGBA", (target_w, total_h), color=(255, 255, 255, 0))

    y = 0
    for im in resized:
        canvas.paste(im, (0, y), im)
        y += im.height + spacing

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG")
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从亚马逊 URL 或本地 HTML 提取套图和 A+ 图，并分别纵向拼接。"
    )
    parser.add_argument("--url", help="亚马逊商品页 URL（推荐使用）")
    parser.add_argument("--html-path", help="本地 HTML 文件路径（URL 模式失败时兜底）")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--spacing", type=int, default=20, help="拼接间距，默认20")
    parser.add_argument("--min-width", type=int, default=200, help="过滤最小宽度，默认200")
    parser.add_argument("--timeout", type=int, default=20, help="抓取与下载超时秒数，默认20")
    parser.add_argument("--user-agent", default=DEFAULT_UA, help="抓取与下载用 UA")
    parser.add_argument(
        "--save-fetched-html",
        action="store_true",
        help="抓取 URL 后，把原始 HTML 保存到输出目录（便于排查）",
    )
    return parser.parse_args()


def _slugify_for_path(text: str, fallback: str = "amazon_extract") -> str:
    text = text or fallback
    text = re.sub(r"https?://", "", text)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")
    return (text[:60] or fallback).lower()


def main() -> int:
    args = parse_args()

    if not args.url and not args.html_path:
        print(
            json.dumps(
                {"success": False, "error": "missing_input: 必须提供 --url 或 --html-path"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    errors: List[str] = []
    html_text = ""
    soup: Optional[BeautifulSoup] = None
    source_kind = ""
    source_value = ""
    final_url = ""
    asin_for_dir = ""

    if args.url:
        source_kind = "url"
        source_value = args.url
        try:
            html_text, soup, final_url = fetch_html(
                args.url, timeout=args.timeout, user_agent=args.user_agent
            )
        except Exception as exc:
            print(
                json.dumps(
                    {"success": False, "error": f"fetch_failed: {exc}"},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1

        block = detect_anti_bot(html_text)
        if block:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": f"blocked_by_amazon: {block}",
                        "hint": "亚马逊触发了风控页。请稍后重试，或改用 --html-path 传入本地保存的 HTML。",
                        "final_url": final_url,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2

        m = re.search(r"/dp/([A-Z0-9]{10})", final_url or args.url, flags=re.IGNORECASE)
        if m:
            asin_for_dir = m.group(1).upper()
    else:
        html_path = Path(args.html_path).expanduser().resolve()
        if not html_path.exists():
            print(
                json.dumps(
                    {"success": False, "error": f"html_not_found: {html_path}"},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
        source_kind = "html"
        source_value = str(html_path)
        html_text, soup = load_html(html_path)

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else Path("生成结果输出").resolve()
        / "amazon图片提取"
        / f"{asin_for_dir or _slugify_for_path(source_value)}_{timestamp}"
    )
    gallery_dir = output_dir / "gallery"
    aplus_dir = output_dir / "aplus"

    if args.url and args.save_fetched_html:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "fetched_page.html").write_text(html_text, encoding="utf-8")

    if args.url and final_url:
        base_url = final_url
    elif args.url and args.url:
        base_url = args.url
    else:
        base_url = detect_base_url(html_text, soup) if soup else ""

    gallery_urls, gallery_hits = extract_gallery_images(html_text, soup, base_url)
    aplus_groups, aplus_hits = extract_aplus_image_groups(soup, base_url)
    aplus_flat = [u for grp in aplus_groups for u in grp]

    gallery_files = download_images(
        gallery_urls,
        gallery_dir,
        min_width=args.min_width,
        timeout=args.timeout,
        user_agent=args.user_agent,
        errors=errors,
    )
    aplus_group_files = download_image_groups(
        aplus_groups,
        aplus_dir,
        min_width=args.min_width,
        timeout=args.timeout,
        user_agent=args.user_agent,
        errors=errors,
    )
    aplus_files_flat = [p for grp in aplus_group_files for p in grp]

    gallery_vertical = None
    aplus_vertical = None
    try:
        gallery_vertical = stitch_vertical(gallery_files, output_dir / "gallery_vertical.png", args.spacing)
    except Exception as exc:
        errors.append(f"stitch_failed: gallery | {exc}")
    try:
        aplus_vertical = stitch_grouped(aplus_group_files, output_dir / "aplus_vertical.png", args.spacing)
    except Exception as exc:
        errors.append(f"stitch_failed: aplus | {exc}")

    # 所有路径写成相对 output_dir 的形式（report.json 本身就在 output_dir 内），
    # 这样整个目录拷贝/转发给他人后路径依然有效，不依赖生成机器的绝对路径。
    def _rel(p: Optional[Path]) -> Optional[str]:
        if p is None:
            return None
        try:
            return Path(p).relative_to(output_dir).as_posix()
        except ValueError:
            return Path(p).as_posix()

    report = {
        "success": True,
        "source": {"kind": source_kind, "value": source_value, "final_url": final_url},
        "base_url": base_url,
        "output_dir": ".",
        "selectors_hit": {"gallery": gallery_hits, "aplus": aplus_hits},
        "gallery": {
            "url_count": len(gallery_urls),
            "downloaded_count": len(gallery_files),
            "files": [_rel(p) for p in gallery_files],
            "vertical_image": _rel(gallery_vertical),
        },
        "aplus": {
            "group_count": len(aplus_groups),
            "groups": [
                {
                    "index": i + 1,
                    "url_count": len(g),
                    "downloaded_count": len(aplus_group_files[i]) if i < len(aplus_group_files) else 0,
                    "files": [
                        _rel(p) for p in (aplus_group_files[i] if i < len(aplus_group_files) else [])
                    ],
                }
                for i, g in enumerate(aplus_groups)
            ],
            "url_count": len(aplus_flat),
            "downloaded_count": len(aplus_files_flat),
            "vertical_image": _rel(aplus_vertical),
        },
        "errors": errors,
    }

    report_path = output_dir / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # stdout 版保留绝对 output_dir，便于调用方据此定位目录执行后续步骤（不写入文件）
    stdout_report = dict(report)
    stdout_report["output_dir"] = str(output_dir)
    print(json.dumps(stdout_report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
