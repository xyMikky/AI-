"""Audit multi-ASIN Amazon competitor analysis outputs for data alignment.

This script validates that each ASIN directory in an amazon-competitor-analyzer
multi-SKU output folder uses matching metadata, reports, review aggregates,
review evidence and dashboards. It is intentionally read-only.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ASIN_RE = re.compile(r"\bB0[A-Z0-9]{8}\b")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit ASIN alignment in multi-ASIN competitor reports.")
    parser.add_argument(
        "--compare-dir",
        required=True,
        help="Multi-ASIN parent directory, for example 生成结果输出/amazon图片提取/_compare_YYYYMMDD_HHMMSS",
    )
    parser.add_argument(
        "--asins",
        default="",
        help="Optional comma-separated ASIN allowlist. Default: infer ASIN directories under compare-dir.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Audit JSON output path. Default: <compare-dir>/asin_alignment_audit.json",
    )
    parser.add_argument(
        "--strict-raw",
        action="store_true",
        help="Fail if raw review files contain non-target ASINs. Default: warn only when filtered artifacts align.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def asins_in_text(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(ASIN_RE.findall(path.read_text(encoding="utf-8", errors="ignore")))


def infer_asins(compare_dir: Path, explicit: str) -> list[str]:
    if explicit.strip():
        return [item.strip() for item in explicit.split(",") if item.strip()]
    asins = [path.name for path in compare_dir.iterdir() if path.is_dir() and ASIN_RE.fullmatch(path.name)]
    return sorted(asins)


def latest_review_file(directory: Path) -> Path | None:
    files = list(directory.glob("*reviews_linkfox_raw*.json"))
    retry_files = [path for path in files if "retry" in path.name]
    pool = retry_files or files
    if not pool:
        return None
    return max(pool, key=lambda path: path.stat().st_mtime)


def collect_raw_review_asins(raw_path: Path) -> dict[str, int]:
    data = load_json(raw_path)
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        records = data["data"]
    elif isinstance(data, list):
        records = data
    else:
        records = []

    counts: dict[str, int] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        asin = record.get("asin") or record.get("ASIN") or record.get("productAsin")
        if isinstance(asin, str) and ASIN_RE.fullmatch(asin):
            counts[asin] = counts.get(asin, 0) + 1
    return counts


def kv_asin_from_visual(visual: dict[str, Any]) -> str | None:
    for section in visual.get("sections", []):
        if section.get("type") != "kv-table":
            continue
        for row in section.get("rows", []):
            if isinstance(row, list) and len(row) >= 2 and row[0] == "ASIN":
                return str(row[1])
    return None


def image_assets(directory: Path, child: str) -> list[Path]:
    asset_dir = directory / child
    if not asset_dir.exists():
        return []
    return sorted(path for path in asset_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTS)


def report_gallery_files(report: dict[str, Any]) -> list[str]:
    return [str(item).replace("\\", "/") for item in (report.get("gallery") or {}).get("files") or []]


def report_aplus_files(report: dict[str, Any]) -> list[str]:
    files: list[str] = []
    for group in (report.get("aplus") or {}).get("groups") or []:
        files.extend(str(item).replace("\\", "/") for item in group.get("files") or [])
    return files


def rel_asset_exists(directory: Path, rel_path: str) -> bool:
    parts = [part for part in rel_path.replace("\\", "/").split("/") if part]
    return directory.joinpath(*parts).exists()


def metadata_media_count(metadata: dict[str, Any], key: str) -> int | None:
    media = metadata.get("media") or {}
    value = media.get(key)
    if isinstance(value, int):
        return value
    return None


def audit_one(compare_dir: Path, asin: str, strict_raw: bool) -> dict[str, Any]:
    directory = compare_dir / asin
    result: dict[str, Any] = {"asin": asin, "status": "PASS", "checks": [], "warnings": []}

    def check(name: str, ok: bool, detail: str) -> None:
        result["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            result["status"] = "FAIL"

    def warn(detail: str) -> None:
        result["warnings"].append(detail)

    check("directory_exists", directory.exists(), str(directory))
    if not directory.exists():
        return result

    metadata_path = directory / "metadata.json"
    visual_path = directory / "visual.json"
    md_path = directory / "competitor_analysis.md"
    # HTML 报告默认输出为 index.html；兼容历史版本的 competitor_analysis.html。
    html_path = directory / "index.html"
    if not html_path.exists() and (directory / "competitor_analysis.html").exists():
        html_path = directory / "competitor_analysis.html"
    image_report_path = directory / "report.json"
    aggregate_path = directory / "reviews_aggregate.json"
    evidence_path = directory / "review_evidence.json"
    dashboard_path = directory / "review_dashboard.html"

    for required in [metadata_path, visual_path, md_path, html_path]:
        check(f"{required.name}_exists", required.exists(), str(required))

    if not all(path.exists() for path in [metadata_path, visual_path, md_path, html_path]):
        return result

    metadata = load_json(metadata_path)
    meta_asin = metadata.get("asin")
    source_url = metadata.get("source_url", "")
    check("metadata_asin_matches_dir", meta_asin == asin, f"metadata.asin={meta_asin}")
    check("metadata_source_url_contains_asin", asin in source_url, f"source_url={source_url}")

    visual = load_json(visual_path)
    visual_asin = kv_asin_from_visual(visual)
    visual_asins = asins_in_text(visual_path)
    check("visual_kv_asin_matches_dir", visual_asin == asin, f"kv ASIN={visual_asin}")
    check("visual_contains_no_other_asins", visual_asins <= {asin}, f"visual_asins={sorted(visual_asins)}")

    md_asins = asins_in_text(md_path)
    html_asins = asins_in_text(html_path)
    html_text = html_path.read_text(encoding="utf-8", errors="ignore")
    check("markdown_contains_no_other_asins", md_asins <= {asin}, f"md_asins={sorted(md_asins)}")
    check("html_contains_no_other_asins", html_asins <= {asin}, f"html_asins={sorted(html_asins)}")

    gallery_assets = image_assets(directory, "gallery")
    aplus_assets = image_assets(directory, "aplus")
    has_image_assets = bool(gallery_assets or aplus_assets)
    check(
        "image_report_json_exists_when_assets_exist",
        (not has_image_assets) or image_report_path.exists(),
        f"report.json={image_report_path.exists()}, gallery_assets={len(gallery_assets)}, aplus_assets={len(aplus_assets)}",
    )
    if image_report_path.exists():
        image_report = load_json(image_report_path)
        gallery_files = report_gallery_files(image_report)
        aplus_files = report_aplus_files(image_report)
        check(
            "image_report_gallery_files_exist",
            all(rel_asset_exists(directory, item) for item in gallery_files),
            f"report_gallery_files={len(gallery_files)}",
        )
        check(
            "image_report_aplus_files_exist",
            all(rel_asset_exists(directory, item) for item in aplus_files),
            f"report_aplus_files={len(aplus_files)}",
        )
        if gallery_assets:
            check(
                "image_report_gallery_not_empty",
                bool(gallery_files),
                f"gallery_assets={len(gallery_assets)}, report_gallery_files={len(gallery_files)}",
            )
            check(
                "metadata_media_gallery_count_present",
                bool(metadata_media_count(metadata, "gallery_count")),
                f"metadata.media.gallery_count={metadata_media_count(metadata, 'gallery_count')}",
            )
            check(
                "html_gallery_src_not_empty",
                'class="gallery-main" src=""' not in html_text,
                "gallery-main src must not be empty",
            )
            first_gallery = gallery_files[0] if gallery_files else ""
            check(
                "html_references_report_gallery_asset",
                bool(first_gallery and first_gallery in html_text.replace("\\", "/")),
                f"first_gallery={first_gallery}",
            )
        if aplus_assets:
            check(
                "image_report_aplus_not_empty",
                bool(aplus_files),
                f"aplus_assets={len(aplus_assets)}, report_aplus_files={len(aplus_files)}",
            )
            check(
                "metadata_media_aplus_count_present",
                bool(metadata_media_count(metadata, "aplus_module_count")),
                f"metadata.media.aplus_module_count={metadata_media_count(metadata, 'aplus_module_count')}",
            )
            first_aplus = aplus_files[0] if aplus_files else ""
            check(
                "html_references_report_aplus_asset",
                bool(first_aplus and first_aplus in html_text.replace("\\", "/")),
                f"first_aplus={first_aplus}",
            )

    raw_path = latest_review_file(directory)
    raw_counts: dict[str, int] = {}
    if raw_path:
        check("raw_review_file_exists", True, raw_path.name)
        raw_counts = collect_raw_review_asins(raw_path)
        if raw_counts:
            check("raw_review_contains_target_asin", asin in raw_counts, f"raw_counts={raw_counts}")
            other_raw = {key: value for key, value in raw_counts.items() if key != asin}
            if other_raw:
                message = f"Raw review file contains non-target ASINs: {other_raw}. Filtered artifacts must still align."
                if strict_raw:
                    check("raw_review_contains_no_other_asins", False, message)
                else:
                    warn(message)
        else:
            warn("Raw review file has no parseable per-review ASIN field; downstream scoped artifacts carry the audit.")
    else:
        check("raw_review_file_exists", False, "missing")

    if aggregate_path.exists():
        aggregate = load_json(aggregate_path)
        scope = aggregate.get("scope") or aggregate.get("sample", {}).get("scope")
        distinct = aggregate.get("distinct_asin") or {}
        check("aggregate_scope_matches_target", scope == f"single_asin:{asin}", f"scope={scope}")
        if isinstance(distinct, dict):
            check("aggregate_distinct_asin_scoped", set(distinct) <= {asin}, f"distinct={distinct}")
        elif isinstance(distinct, list):
            check("aggregate_distinct_asin_scoped", set(distinct) <= {asin}, f"distinct={distinct}")
        else:
            warn(f"aggregate distinct_asin has unexpected type: {type(distinct).__name__}")
    else:
        warn("reviews_aggregate.json missing; skip aggregate checks.")

    if evidence_path.exists():
        evidence = load_json(evidence_path)
        evidence_asin = evidence.get("asin")
        evidence_scope = evidence.get("scope")
        evidence_count = evidence.get("overall", {}).get("count")
        check("evidence_asin_matches_target", evidence_asin == asin, f"evidence.asin={evidence_asin}")
        check("evidence_scope_matches_target", evidence_scope == f"single_asin:{asin}", f"scope={evidence_scope}")
        if raw_counts.get(asin):
            check(
                "evidence_count_matches_raw_target_count",
                evidence_count == raw_counts[asin],
                f"evidence_count={evidence_count}, raw_target_count={raw_counts[asin]}",
            )
    else:
        warn("review_evidence.json missing; skip evidence checks.")

    if dashboard_path.exists():
        dashboard_asins = asins_in_text(dashboard_path)
        check("dashboard_contains_no_other_asins", dashboard_asins <= {asin}, f"dashboard_asins={sorted(dashboard_asins)}")
    else:
        warn("review_dashboard.html missing; skip dashboard checks.")

    return result


def main() -> int:
    args = parse_args()
    compare_dir = Path(args.compare_dir).expanduser().resolve()
    asins = infer_asins(compare_dir, args.asins)
    results = [audit_one(compare_dir, asin, args.strict_raw) for asin in asins]
    output_path = Path(args.output).expanduser().resolve() if args.output else compare_dir / "asin_alignment_audit.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    fail_count = 0
    for result in results:
        failed = [check for check in result["checks"] if not check["ok"]]
        if failed:
            fail_count += 1
        print(f"{result['asin']}: {result['status']}")
        for check in result["checks"]:
            mark = "OK" if check["ok"] else "FAIL"
            print(f"  [{mark}] {check['name']} - {check['detail']}")
        for warning in result["warnings"]:
            print(f"  [WARN] {warning}")
    print(f"WROTE {output_path}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
