#!/usr/bin/env python3
"""L2 visual harness 防泄漏与单期隔离校验."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SEALED_FILENAME = "answers_sealed.json"
STRICT_MARKER = ".strict_run"
SEALED_EXTERNAL_PREFIX = "_sealed_"
MAX_ISSUES_PER_DISPATCH = 1

# 已知因批量 subagent / 答案未移出 / 父会话污染而失效的 run，score 时强制警告
CONTAMINATED_RUN_IDS: frozenset[str] = frozenset({"l2-100"})

# 权威严格单期盲测范例（供文档引用）
REFERENCE_STRICT_RUN_ID = "l2-100-single"


def external_sealed_path(run_dir: Path) -> Path:
    return run_dir.parent / f"{SEALED_EXTERNAL_PREFIX}{run_dir.name}.json"


def is_strict_run(manifest: dict[str, Any]) -> bool:
    iso = manifest.get("isolation") or {}
    return iso.get("mode") == "single-period-strict"


def seal_answers_out(run_dir: Path) -> Path:
    """预测阶段：将 answers_sealed.json 移出 run 目录，降低误读风险."""
    src = run_dir / SEALED_FILENAME
    if not src.is_file():
        raise FileNotFoundError(f"未找到待封存答案: {src}")
    dst = external_sealed_path(run_dir)
    if dst.is_file():
        dst.unlink()
    src.replace(dst)
    (run_dir / STRICT_MARKER).write_text(
        json.dumps(
            {
                "mode": "single-period-strict",
                "answers_external": str(dst.name),
                "max_issues_per_subagent": MAX_ISSUES_PER_DISPATCH,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return dst


def restore_answers_for_score(run_dir: Path) -> bool:
    """计分前：若答案在外部，移回 run 目录."""
    internal = run_dir / SEALED_FILENAME
    if internal.is_file():
        return False
    external = external_sealed_path(run_dir)
    if not external.is_file():
        raise FileNotFoundError(
            f"未找到封存答案：run 内无 {SEALED_FILENAME}，外部也无 {external.name}"
        )
    external.replace(internal)
    return True


def assert_answers_not_in_run_dir(run_dir: Path, *, context: str) -> None:
    if (run_dir / SEALED_FILENAME).is_file():
        raise SystemExit(
            f"[strict] {context}：answers_sealed.json 仍在 run 目录内。"
            f"预测阶段必须先移出（prepare --strict 会自动执行，或手动 seal-out）。"
        )


def prediction_fingerprint(pred: dict[str, Any]) -> str:
    preds = pred.get("predictions") or {}
    parts: list[str] = []
    for name in sorted(preds.keys()):
        block = preds[name]
        parts.append(
            f"{name}:"
            f"{','.join(map(str, block.get('front', [])))}|"
            f"{','.join(map(str, block.get('back', [])))}"
        )
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _period_dir(run_dir: Path, issue: str) -> Path:
    return run_dir / "periods" / issue


def validate_prediction_meta(
    pred: dict[str, Any],
    *,
    target_issue: str,
    strict: bool,
) -> list[str]:
    """record 阶段软校验，返回警告列表."""
    warnings: list[str] = []
    if pred.get("method") and pred.get("method") != "visual":
        warnings.append(f"{target_issue}: method 应为 visual，实际 {pred['method']}")
    dispatch = pred.get("dispatch") or {}
    if strict:
        if dispatch.get("issues_count", 1) != 1:
            warnings.append(
                f"{target_issue}: dispatch.issues_count 应为 1，实际 {dispatch.get('issues_count')}"
            )
        if dispatch.get("isolation") and dispatch.get("isolation") != "single":
            warnings.append(f"{target_issue}: dispatch.isolation 应为 single")
    reasoning = " ".join(
        str(block.get("reasoning", ""))
        for block in (pred.get("predictions") or {}).values()
    )
    if re.search(r"(?:开奖|开出|实际|结果).{0,12}\d{2}\s+\d{2}", reasoning):
        warnings.append(f"{target_issue}: reasoning 疑似含开奖后验表述，请人工复核")
    if str(pred.get("target_issue", target_issue)) != target_issue:
        warnings.append(f"{target_issue}: target_issue 字段不一致")
    return warnings


def validate_run_for_score(
    run_dir: Path,
    manifest: dict[str, Any],
    *,
    strict: bool,
) -> dict[str, Any]:
    """score 前完整性校验，返回 report；errors 非空时应中止计分."""
    errors: list[str] = []
    warnings: list[str] = []

    run_id = manifest.get("run_id", run_dir.name)
    if run_id in CONTAMINATED_RUN_IDS:
        errors.append(
            f"run_id={run_id} 在已知污染名单内（批量 subagent / 答案未隔离），"
            f"结果不可作为有效盲测证据。请用 --strict 重跑，参考 {REFERENCE_STRICT_RUN_ID}。"
        )

    if strict and not is_strict_run(manifest):
        errors.append("manifest 未声明 isolation.mode=single-period-strict，strict 计分被拒绝")

    iso = manifest.get("isolation") or {}
    if strict and iso.get("answers_during_prediction") != "external":
        warnings.append("manifest 未记录 answers_during_prediction=external（旧 run 可能未移出答案）")

    fingerprints: dict[str, str] = {}
    dup_groups: dict[str, list[str]] = defaultdict(list)
    missing: list[str] = []

    for p in manifest.get("periods", []):
        issue = p["target_issue"]
        pred_path = _period_dir(run_dir, issue) / "prediction.json"
        if not pred_path.is_file():
            missing.append(issue)
            continue
        pred = json.loads(pred_path.read_text(encoding="utf-8"))
        fp = prediction_fingerprint(pred)
        fingerprints[issue] = fp
        dup_groups[fp].append(issue)
        warnings.extend(
            validate_prediction_meta(pred, target_issue=issue, strict=strict)
        )

    if missing:
        errors.append(f"尚有 {len(missing)} 期未 record: {missing[:8]}{'...' if len(missing) > 8 else ''}")

    exact_dupes = {fp: issues for fp, issues in dup_groups.items() if len(issues) > 1}
    if exact_dupes:
        for fp, issues in exact_dupes.items():
            warnings.append(
                f"多期预测完全相同（疑似复制粘贴）: {', '.join(issues)} fingerprint={fp}"
            )

    return {
        "run_id": run_id,
        "strict": strict,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "duplicate_groups": {k: v for k, v in exact_dupes.items()},
        "recorded": len(fingerprints),
        "expected": len(manifest.get("periods", [])),
    }


def build_dispatch_policy(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": (manifest.get("isolation") or {}).get("mode", "legacy"),
        "max_issues_per_subagent": MAX_ISSUES_PER_DISPATCH,
        "forbidden_reads": [
            "answers_sealed.json",
            "assets/lotto_history.json",
            "其他 periods/* 目录",
            "父会话 score / 开奖结果",
            "local_trend_chart.py 的 final_recommendation stdout",
        ],
        "forbidden_orchestration": [
            "单 subagent 连续处理多期",
            "record-batch 批量落盘（除非 --unsafe-allow-batch 调试）",
            "从其他 run 复制 prediction.json",
            "transcript 批量 ingest 替代逐期看图",
        ],
        "subagent_template": (
            "Task generalPurpose readonly=true；仅附件本 period 四文件；"
            "只输出单期 JSON；禁止读取封存答案与其他期目录"
        ),
    }
