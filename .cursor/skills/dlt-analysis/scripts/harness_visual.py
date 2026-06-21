#!/usr/bin/env python3
"""
大乐透预测评测框架（L2 visual harness · 子 agent 看图盲测）

流程（由父 agent 编排，本脚本负责落盘/计分）：
  1. prepare  — 为每期生成 50 期大图 + 15 期小图 + 基准统计；答案封存 answers_sealed.json
  2. 父 agent 对每期派空白子 agent（readonly），只喂该期目录内素材 + agent_prompt.md
  3. record   — 写入子 agent 返回的 prediction.json（预测落定后才可 score）
  4. score    — 揭晓答案、计分、对比随机基线；可选 --compare-algo 与 L1 同台 PK
  5. status   — 查看 pending / done

用法：
  python scripts/harness_visual.py prepare --periods 10 --run-id demo10
  python scripts/harness_visual.py status --run-id demo10
  python scripts/harness_visual.py next --run-id demo10          # 输出下一期待测 bundle
  python scripts/harness_visual.py record --run-id demo10 --issue 26058 --file pred.json
  python scripts/harness_visual.py score --run-id demo10 --compare-algo
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import dlt_data as D
from harness_common import (
    FORMATS,
    aggregate_scores,
    parse_formats,
    random_pool_baseline,
    score_pool,
    validate_prediction_numbers,
)
from harness_fusion import fuse_prediction_block
from harness_isolation import (
    SEALED_FILENAME,
    assert_answers_not_in_run_dir,
    build_dispatch_policy,
    is_strict_run,
    restore_answers_for_score,
    seal_answers_out,
    validate_run_for_score,
    validate_prediction_meta,
)
from local_trend_chart import DEFAULT_LOCAL_COUNT, render_local_trend_png
from stats_report import format_report as format_stats_report
from trend_chart import render_png as render_trend_png

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS_DIR = SKILL_ROOT / "assets" / "visual_runs"
TREND_COUNT = 50
LOCAL_COUNT = 15
MANIFEST_FILENAME = "manifest.json"


def _runs_dir(run_id: str | None) -> Path:
    rid = run_id or datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")
    return DEFAULT_RUNS_DIR / rid


def _period_dir(run_dir: Path, target_issue: str) -> Path:
    return run_dir / "periods" / target_issue


def _load_manifest(run_dir: Path) -> dict[str, Any]:
    path = run_dir / MANIFEST_FILENAME
    if not path.is_file():
        raise SystemExit(f"未找到 manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_sealed(run_dir: Path) -> dict[str, Any]:
    path = run_dir / SEALED_FILENAME
    if not path.is_file():
        raise SystemExit(f"未找到封存答案: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _test_indices(records: list[dict[str, Any]], periods: int) -> list[int]:
    start = max(15, len(records) - periods)
    return list(range(start, len(records)))


def _build_agent_prompt(
    *,
    target_issue: str,
    base_issue: str,
    formats: dict[str, tuple[int, int]],
    stats_text: str,
) -> str:
    fmt_lines = []
    for name, (fc, bc) in formats.items():
        fmt_lines.append(
            f"- **{name}**：前区 {fc} 个不重复号（1–35），后区 {bc} 个不重复号（1–12）"
        )
    fmt_block = "\n".join(fmt_lines)
    pred_schema = {
        "target_issue": target_issue,
        "method": "visual",
        "predictions": {
            name: {
                "front": ["1–35 共 fc 个整数"],
                "back": ["1–12 共 bc 个整数"],
                "reasoning": "基于两张趋势图的视觉判断，中文简述",
            }
            for name in formats
        },
        "reviewed_charts": ["trend-50.png", "local-trend-15.png"],
    }
    return f"""# 大乐透看图盲测任务

## 你的角色
你是**空白上下文**的视觉分析子 agent。你只能依据本目录内素材做判断，**不得**查阅历史对话、全库 JSON、或其他期号文件夹。

## ⚠️ 单期隔离（强制）
- 你**只**处理 **{target_issue} 期**这一期，禁止在同一任务中预测其他期号
- 禁止读取 `answers_sealed.json`、`lotto_history.json`、父目录或其他 `periods/*`
- 禁止引用「已知开奖结果」或对话历史中的计分信息
- 输出 JSON 中建议包含 `"dispatch": {{"isolation": "single", "issues_count": 1}}`

## 任务
预测 **{target_issue} 期**开奖号（基准数据截止 **{base_issue} 期**，图表不含 {target_issue} 及之后任何信息）。

## 必读素材（按顺序）
1. `trend-50.png` — 50 期基本走势图（宏观）
2. `local-trend-15.png` — 15 期局部趋势图（微观，含趋势线/延长落点）
3. `stats.txt` — 基准窗口统计（冷热/超期/和值，辅助参考）

## 分析方法（视觉优先）
- 先看 50 期大图：分区分布、冷热、遗漏、斜向/纵向连线
- 再看 15 期小图：趋势落点、汇聚/发散、延长虚线指向
- 结合 stats 中的超期号与热号，但**以图为主**
- 禁止使用后验知识或「已知开奖结果」

## 输出规格
{fmt_block}

## 输出格式（严格 JSON，写入 prediction.json）
```json
{json.dumps(pred_schema, ensure_ascii=False, indent=2)}
```

## 约束
- 号码必须为整数，升序排列
- 每种格式各一套，不可省略 manifest 中声明的格式
- `reasoning` 需说明你从图中看到的依据（趋势/超期/重号等）
- **只输出 JSON**，不要输出开奖结果以外的多余文件
"""


def prepare_run(
    *,
    run_id: str | None,
    periods: int,
    formats: dict[str, tuple[int, int]],
    data_path: Path | None,
    strict: bool = True,
) -> Path:
    records = D.load_records(D.resolve_data_path(data_path))
    issues = [r["issue"] for r in records]
    run_dir = _runs_dir(run_id)
    if run_dir.exists() and any(run_dir.iterdir()):
        raise SystemExit(f"run 目录已存在且非空: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "periods").mkdir(exist_ok=True)

    test_idx = _test_indices(records, periods)
    sealed: dict[str, Any] = {}
    manifest_periods: list[dict[str, Any]] = []

    data_file = D.resolve_data_path(data_path)
    for i in test_idx:
        base_issue = issues[i - 1]
        target_issue = issues[i]
        pdir = _period_dir(run_dir, target_issue)
        pdir.mkdir(parents=True, exist_ok=True)

        window50, _ = D.pick_window(records, base_issue, TREND_COUNT)
        window15, _ = D.pick_window(records, base_issue, LOCAL_COUNT)
        rows50 = D.build_chart_rows(records, window50)
        rows15 = D.build_chart_rows(records, window15)
        analysis15 = D.analyze_local_trends(window15)

        trend_png = pdir / "trend-50.png"
        local_png = pdir / "local-trend-15.png"
        render_trend_png(rows50, base_issue, TREND_COUNT, data_file, trend_png)
        render_local_trend_png(
            rows15, window15, analysis15, base_issue, LOCAL_COUNT, data_file, local_png
        )

        stats = D.window_stats(records, base_issue, TREND_COUNT)
        summary = D.data_summary(records)
        stats_text = format_stats_report(stats, summary, data_file)
        (pdir / "stats.txt").write_text(stats_text, encoding="utf-8")

        meta = {
            "target_issue": target_issue,
            "base_issue": base_issue,
            "charts": {
                "trend_50": "trend-50.png",
                "local_15": "local-trend-15.png",
            },
            "stats": "stats.txt",
            "formats": list(formats.keys()),
            "status": "pending",
        }
        (pdir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (pdir / "agent_prompt.md").write_text(
            _build_agent_prompt(
                target_issue=target_issue,
                base_issue=base_issue,
                formats=formats,
                stats_text=stats_text,
            ),
            encoding="utf-8",
        )

        sealed[target_issue] = {
            "main": [int(x) for x in records[i]["main"]],
            "bonus": [int(x) for x in records[i]["bonus"]],
        }
        manifest_periods.append(
            {
                "target_issue": target_issue,
                "base_issue": base_issue,
                "dir": str(pdir.relative_to(run_dir)).replace("\\", "/"),
            }
        )

    manifest = {
        "run_id": run_dir.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "visual",
        "periods_count": len(test_idx),
        "issue_range": [issues[test_idx[0]], issues[test_idx[-1]]] if test_idx else None,
        "formats": {k: {"front": v[0], "back": v[1]} for k, v in formats.items()},
        "periods": manifest_periods,
        "isolation": {
            "mode": "single-period-strict" if strict else "legacy",
            "max_issues_per_subagent": 1,
            "answers_during_prediction": "external" if strict else "in-run",
            "forbidden": [
                "batch multi-issue subagent",
                "record-batch without --unsafe-allow-batch",
                "reading answers_sealed.json during prediction",
                "copying predictions from other runs",
            ],
        },
        "instructions": {
            "subagent": (
                "readonly；仅读 periods/<issue>/ 内 4 文件；"
                "1 subagent = 1 issue；禁止 answers_sealed / 全库 JSON / 其他期"
            ),
            "parent": (
                "逐期 next → 派单期 subagent → record → 全部完成后 validate → score"
            ),
        },
    }
    (run_dir / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / SEALED_FILENAME).write_text(
        json.dumps(sealed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sealed_external: str | None = None
    if strict:
        ext = seal_answers_out(run_dir)
        sealed_external = ext.name
        manifest["isolation"]["answers_external_path"] = sealed_external
        (run_dir / MANIFEST_FILENAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    readme_lines = [
        "L2 visual harness run",
        f"run_id: {run_dir.name}",
        f"periods: {len(test_idx)}",
        f"isolation: {'single-period-strict' if strict else 'legacy (不推荐)'}",
        "",
        "⚠️ 预测阶段禁止读取 answers_sealed.json",
    ]
    if strict:
        readme_lines += [
            f"⚠️ 答案已移出至: assets/visual_runs/{sealed_external}",
            "⚠️ 禁止单 subagent 连续处理多期（见 references/VISUAL_HARNESS.md）",
        ]
    readme_lines += [
        "",
        "workflow:",
        "  1. harness_visual.py next --run-id ...",
        "  2. Task 子 agent（readonly，仅 1 期）读 agent_prompt.md + 两张 PNG + stats.txt",
        "  3. harness_visual.py record --issue ... --file prediction.json",
        "  4. harness_visual.py validate --run-id ...",
        "  5. harness_visual.py score --run-id ...",
    ]
    (run_dir / "README.txt").write_text("\n".join(readme_lines), encoding="utf-8")
    return run_dir


def _normalize_prediction(raw: dict[str, Any], formats: dict[str, tuple[int, int]]) -> dict[str, Any]:
    preds = raw.get("predictions") or raw
    out: dict[str, Any] = {"predictions": {}}
    for name, (fc, bc) in formats.items():
        block = preds.get(name) or preds.get(name.replace("+", "_"))
        if not block:
            raise ValueError(f"缺少格式 {name} 的预测")
        front = sorted(int(x) for x in block["front"])
        back = sorted(int(x) for x in block["back"])
        validate_prediction_numbers(front, back, fc, bc)
        out["predictions"][name] = {
            "front": front,
            "back": back,
            "reasoning": block.get("reasoning", ""),
        }
    out["target_issue"] = raw.get("target_issue")
    out["method"] = raw.get("method", "visual")
    out["reviewed_charts"] = raw.get("reviewed_charts", ["trend-50.png", "local-trend-15.png"])
    return out


def record_prediction(run_dir: Path, target_issue: str, pred_path: Path) -> None:
    manifest = _load_manifest(run_dir)
    strict = is_strict_run(manifest)
    if strict:
        assert_answers_not_in_run_dir(run_dir, context="record")
    formats = {k: (v["front"], v["back"]) for k, v in manifest["formats"].items()}
    pdir = _period_dir(run_dir, target_issue)
    if not pdir.is_dir():
        raise SystemExit(f"未知期号目录: {pdir}")
    raw = json.loads(pred_path.read_text(encoding="utf-8"))
    normalized = _normalize_prediction(raw, formats)
    if normalized.get("target_issue") and normalized["target_issue"] != target_issue:
        raise ValueError(
            f"prediction target_issue={normalized['target_issue']} 与 --issue={target_issue} 不一致"
        )
    normalized["target_issue"] = target_issue
    normalized["recorded_at"] = datetime.now(timezone.utc).isoformat()
    dispatch = raw.get("dispatch") or {}
    if strict and not dispatch:
        dispatch = {"isolation": "single", "issues_count": 1}
    normalized["dispatch"] = dispatch
    warnings = validate_prediction_meta(normalized, target_issue=target_issue, strict=strict)
    if warnings:
        normalized["_validation_warnings"] = warnings
    out = pdir / "prediction.json"
    out.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = json.loads((pdir / "meta.json").read_text(encoding="utf-8"))
    meta["status"] = "done"
    (pdir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def status_run(run_dir: Path) -> dict[str, Any]:
    manifest = _load_manifest(run_dir)
    items = []
    pending = done = 0
    for p in manifest["periods"]:
        issue = p["target_issue"]
        pred = _period_dir(run_dir, issue) / "prediction.json"
        ok = pred.is_file()
        if ok:
            done += 1
        else:
            pending += 1
        items.append({"target_issue": issue, "base_issue": p["base_issue"], "done": ok})
    return {
        "run_id": manifest["run_id"],
        "total": len(items),
        "done": done,
        "pending": pending,
        "items": items,
    }


def next_pending(run_dir: Path) -> dict[str, Any] | None:
    manifest = _load_manifest(run_dir)
    for p in manifest["periods"]:
        issue = p["target_issue"]
        pdir = _period_dir(run_dir, issue)
        if not (pdir / "prediction.json").is_file():
            policy = build_dispatch_policy(manifest)
            return {
                "run_id": manifest["run_id"],
                "target_issue": issue,
                "base_issue": p["base_issue"],
                "period_dir": str(pdir.resolve()),
                "agent_prompt": str((pdir / "agent_prompt.md").resolve()),
                "charts": [
                    str((pdir / "trend-50.png").resolve()),
                    str((pdir / "local-trend-15.png").resolve()),
                ],
                "stats": str((pdir / "stats.txt").resolve()),
                "isolation_policy": policy,
                "subagent_hint": policy["subagent_template"],
            }
    return None


def validate_run(run_dir: Path, *, strict: bool | None = None) -> dict[str, Any]:
    manifest = _load_manifest(run_dir)
    if strict is None:
        strict = is_strict_run(manifest)
    return validate_run_for_score(run_dir, manifest, strict=strict)


def refine_l1_for_period(
    run_dir: Path,
    target_issue: str,
    *,
    data_path: Path | None = None,
) -> dict[str, Any]:
    """对单期 L2 prediction.json 做 L1 融合，写入 prediction_fused.json."""
    manifest = _load_manifest(run_dir)
    formats = {k: (v["front"], v["back"]) for k, v in manifest["formats"].items()}
    pdir = _period_dir(run_dir, target_issue)
    pred_path = pdir / "prediction.json"
    if not pred_path.is_file():
        raise SystemExit(f"未找到 L2 预测: {pred_path}")

    pred = json.loads(pred_path.read_text(encoding="utf-8"))
    base_issue = None
    for p in manifest["periods"]:
        if p["target_issue"] == target_issue:
            base_issue = p["base_issue"]
            break
    if not base_issue:
        raise SystemExit(f"manifest 中无 target_issue={target_issue}")

    records = D.load_records(D.resolve_data_path(data_path))
    profile = D.load_deviation_profile()
    window, _ = D.pick_window(records, base_issue, LOCAL_COUNT)
    scored = D.compute_recommendation_scores(window, profile=profile, records=records)

    fused_preds: dict[str, Any] = {}
    for name, (fc, bc) in formats.items():
        visual_block = pred["predictions"][name]
        fused_block = fuse_prediction_block(
            visual_block,
            scored["front_scores"],
            scored["back_scores"],
            fc,
            bc,
        )
        fused_preds[name] = {
            "front": fused_block["front"],
            "back": fused_block["back"],
            "reasoning": fused_block.get("reasoning", ""),
            "fusion_meta": fused_block.get("fusion_meta"),
        }

    out = {
        "target_issue": target_issue,
        "base_issue": base_issue,
        "method": "l2_l1_fusion",
        "source_visual": "prediction.json",
        "predictions": fused_preds,
        "refined_at": datetime.now(timezone.utc).isoformat(),
    }
    out_path = pdir / "prediction_fused.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def refine_l1_run(
    run_dir: Path,
    *,
    data_path: Path | None = None,
    issue: str | None = None,
) -> dict[str, Any]:
    manifest = _load_manifest(run_dir)
    targets = [issue] if issue else [p["target_issue"] for p in manifest["periods"]]
    done: list[str] = []
    for target in targets:
        refine_l1_for_period(run_dir, target, data_path=data_path)
        done.append(target)
    return {"ok": True, "refined": done, "count": len(done)}


def score_run(
    run_dir: Path,
    *,
    baseline_trials: int,
    seed: int,
    compare_algo: bool,
    fuse_l1: bool,
    data_path: Path | None,
    skip_validation: bool = False,
) -> dict[str, Any]:
    manifest = _load_manifest(run_dir)
    strict = is_strict_run(manifest)
    if not skip_validation:
        vreport = validate_run(run_dir, strict=strict)
        if not vreport["valid"]:
            raise SystemExit(
                "score 前校验失败:\n"
                + "\n".join(f"  - {e}" for e in vreport["errors"])
            )
    restore_answers_for_score(run_dir)
    sealed = _load_sealed(run_dir)
    formats = {k: (v["front"], v["back"]) for k, v in manifest["formats"].items()}
    records = D.load_records(D.resolve_data_path(data_path))
    profile = D.load_deviation_profile()
    issues = [r["issue"] for r in records]
    rng = random.Random(seed) dict[str, list[dict[str, Any]]] = {k: [] for k in formats}
    fused_rows: dict[str, list[dict[str, Any]]] = {k: [] for k in formats} if fuse_l1 else {}
    algo_rows: dict[str, list[dict[str, Any]]] = {k: [] for k in formats} if compare_algo else {}

    missing: list[str] = []
    for p in manifest["periods"]:
        target = p["target_issue"]
        pred_path = _period_dir(run_dir, target) / "prediction.json"
        if not pred_path.is_file():
            missing.append(target)
            continue
        pred = json.loads(pred_path.read_text(encoding="utf-8"))
        actual = sealed[target]
        af = set(actual["main"])
        ab = set(actual["bonus"])
        base_issue = p["base_issue"]
        window, _ = D.pick_window(records, base_issue, LOCAL_COUNT)
        scored = D.compute_recommendation_scores(window, profile=profile, records=records)

        for name, (fc, bc) in formats.items():
            block = pred["predictions"][name]
            sc = score_pool(block["front"], block["back"], af, ab)
            base = random_pool_baseline(af, ab, fc, bc, baseline_trials, rng)
            row = {
                "issue": target,
                "base": base_issue,
                "front_hits": sc["front_hits"],
                "back_hits": sc["back_hits"],
                "tier": sc["tier"],
                "baseline_front_hits": base["front_hits"],
                "baseline_back_hits": base["back_hits"],
                "baseline_prize_rate": base["prize_rate"],
                "actual_main": actual["main"],
                "actual_bonus": actual["bonus"],
            }
            visual_rows[name].append(row)

            if fuse_l1:
                fused_block = fuse_prediction_block(
                    block, scored["front_scores"], scored["back_scores"], fc, bc
                )
                fsc = score_pool(fused_block["front"], fused_block["back"], af, ab)
                fused_rows[name].append({
                    "issue": target,
                    "base": base_issue,
                    "front_hits": fsc["front_hits"],
                    "back_hits": fsc["back_hits"],
                    "tier": fsc["tier"],
                    "baseline_front_hits": base["front_hits"],
                    "baseline_back_hits": base["back_hits"],
                    "baseline_prize_rate": base["prize_rate"],
                    "fusion_meta": fused_block.get("fusion_meta"),
                })

        if compare_algo:
            for name, (fc, bc) in formats.items():
                res = D.build_final_recommendation(
                    window, profile=profile, records=records,
                    front_count=fc, back_count=bc,
                )
                sc = score_pool(res["front"], res["back"], af, ab)
                algo_rows[name].append({
                    "issue": target,
                    "front_hits": sc["front_hits"],
                    "back_hits": sc["back_hits"],
                    "tier": sc["tier"],
                })

    if missing:
        raise SystemExit(f"尚有 {len(missing)} 期未 record: {missing[:5]}{'...' if len(missing) > 5 else ''}")

    validation = validate_run(run_dir, strict=strict) if not skip_validation else None
    summary: dict[str, Any] = {
        "run_id": manifest["run_id"],
        "mode": "visual",
        "isolation": manifest.get("isolation"),
        "validation": validation,
        "tested_periods": len(manifest["periods"]),
        "issue_range": manifest["issue_range"],
        "baseline_trials": baseline_trials,
        "formats": {},
    }
    for name in formats:
        summary["formats"][name] = {
            "visual": aggregate_scores(visual_rows[name], name),
        }
        if compare_algo:
            ar = algo_rows[name]
            n = len(ar)
            summary["formats"][name]["algo_same_periods"] = {
                "avg_front_hits": round(sum(r["front_hits"] for r in ar) / n, 4),
                "avg_back_hits": round(sum(r["back_hits"] for r in ar) / n, 4),
                "prize_rate": round(sum(1 for r in ar if r["tier"]) / n, 4),
            }
            vf = summary["formats"][name]["visual"]
            af = summary["formats"][name]["algo_same_periods"]
            summary["formats"][name]["visual_vs_algo"] = {
                "front_hits": round(vf["avg_front_hits"] - af["avg_front_hits"], 4),
                "back_hits": round(vf["avg_back_hits"] - af["avg_back_hits"], 4),
                "prize_rate": round(vf["prize_rate"] - af["prize_rate"], 4),
            }
        if fuse_l1:
            fr = fused_rows[name]
            summary["formats"][name]["l2_l1_fusion"] = aggregate_scores(fr, name)
            ff = summary["formats"][name]["l2_l1_fusion"]
            vf = summary["formats"][name]["visual"]
            summary["formats"][name]["fusion_vs_visual"] = {
                "front_hits": round(ff["avg_front_hits"] - vf["avg_front_hits"], 4),
                "back_hits": round(ff["avg_back_hits"] - vf["avg_back_hits"], 4),
                "prize_rate": round(ff["prize_rate"] - vf["prize_rate"], 4),
            }
            summary["formats"][name]["fusion_vs_random"] = ff["edge"]

    report_path = run_dir / "score_report.json"
    detail_path = run_dir / "score_detail.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    detail_path.write_text(
        json.dumps({
            "visual": visual_rows,
            "fused": fused_rows if fuse_l1 else None,
            "algo": algo_rows if compare_algo else None,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def format_score_report(summary: dict[str, Any]) -> str:
    lines = [
        "大乐透预测评测（L2 visual harness · 子 agent 看图盲测）",
        f"run_id: {summary['run_id']}  被测: {summary['tested_periods']} 期  "
        f"范围 {summary['issue_range'][0]}—{summary['issue_range'][1]}",
        f"随机基线蒙特卡洛/期: {summary['baseline_trials']}",
        "",
    ]
    for name, block in summary["formats"].items():
        v = block["visual"]
        rb = v["random_baseline"]
        e = v["edge"]
        lines += [
            f"■ 格式 {name}（号池 {v['pool']}）— 看图法",
            f"  前区命中/5 : {v['avg_front_hits']:.3f}  | 随机 {rb['avg_front_hits']:.3f}  | 净差 {e['front_hits']:+.3f}",
            f"  后区命中/2 : {v['avg_back_hits']:.3f}  | 随机 {rb['avg_back_hits']:.3f}  | 净差 {e['back_hits']:+.3f}",
            f"  中奖率     : {v['prize_rate']*100:.2f}% | 随机 {rb['prize_rate']*100:.2f}% | 净差 {e['prize_rate']*100:+.2f}%",
            f"  中奖等级分布: {v['prize_tiers'] or '（无）'}",
        ]
        if "algo_same_periods" in block:
            a = block["algo_same_periods"]
            vs = block["visual_vs_algo"]
            lines += [
                f"  同期 L1 算法: 前区 {a['avg_front_hits']:.3f}  后区 {a['avg_back_hits']:.3f}  中奖率 {a['prize_rate']*100:.2f}%",
                f"  看图 vs 算法: 前区 {vs['front_hits']:+.3f}  后区 {vs['back_hits']:+.3f}  中奖率 {vs['prize_rate']*100:+.2f}%",
            ]
        if "l2_l1_fusion" in block:
            f = block["l2_l1_fusion"]
            frb = f["random_baseline"]
            fe = f["edge"]
            fv = block["fusion_vs_visual"]
            lines += [
                f"■ 格式 {name} — L2+L1 融合修正",
                f"  前区命中/5 : {f['avg_front_hits']:.3f}  | 随机 {frb['avg_front_hits']:.3f}  | 净差 {fe['front_hits']:+.3f}",
                f"  后区命中/2 : {f['avg_back_hits']:.3f}  | 随机 {frb['avg_back_hits']:.3f}  | 净差 {fe['back_hits']:+.3f}",
                f"  中奖率     : {f['prize_rate']*100:.2f}% | 随机 {frb['prize_rate']*100:.2f}% | 净差 {fe['prize_rate']*100:+.2f}%",
                f"  融合 vs 看图: 前区 {fv['front_hits']:+.3f}  后区 {fv['back_hits']:+.3f}  中奖率 {fv['prize_rate']*100:+.2f}%",
            ]
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="L2 visual harness（子 agent 看图盲测）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="生成盲测 bundle（图表+统计+封存答案）")
    p_prep.add_argument("--run-id", help="run 目录名（默认时间戳）")
    p_prep.add_argument("-n", "--periods", type=int, default=10, help="最近 N 期（默认 10）")
    p_prep.add_argument("-f", "--format", default="both", help="7+3 / 15+5 / both")
    p_prep.add_argument("-d", "--data", type=Path)
    p_prep.add_argument(
        "--no-strict",
        action="store_true",
        help="关闭单期严格隔离（不推荐；答案留在 run 内，不阻止批量 subagent）",
    )

    p_st = sub.add_parser("status", help="查看 pending/done")
    p_st.add_argument("--run-id", required=True)

    p_nx = sub.add_parser("next", help="输出下一期待派子 agent 的 bundle（JSON）")
    p_nx.add_argument("--run-id", required=True)

    p_rec = sub.add_parser("record", help="落盘子 agent 预测")
    p_rec.add_argument("--run-id", required=True)
    p_rec.add_argument("--issue", required=True, help="被测 target_issue")
    p_rec.add_argument("--file", type=Path, required=True, help="prediction.json 路径")

    p_sc = sub.add_parser("score", help="揭晓并计分")
    p_sc.add_argument("--run-id", required=True)
    p_sc.add_argument("--baseline-trials", type=int, default=1000)
    p_sc.add_argument("--seed", type=int, default=42)
    p_sc.add_argument("--compare-algo", action="store_true", help="同期对比 L1 算法")
    p_sc.add_argument("--fuse-l1", action="store_true", help="计分 L2+L1 融合修正轨")
    p_sc.add_argument("-d", "--data", type=Path)
    p_sc.add_argument("--json", action="store_true")
    p_sc.add_argument(
        "--skip-validation",
        action="store_true",
        help="跳过 score 前校验（仅调试污染 run 时用）",
    )

    p_val = sub.add_parser("validate", help="校验 run 完整性 / 防泄漏（score 前自动执行）")
    p_val.add_argument("--run-id", required=True)
    p_val.add_argument("--json", action="store_true")

    p_seal = sub.add_parser("seal-out", help="手动将 answers_sealed.json 移出 run 目录")
    p_seal.add_argument("--run-id", required=True)

    p_rest = sub.add_parser("restore-answers", help="计分前将外部封存答案移回 run")
    p_rest.add_argument("--run-id", required=True)

    p_ref = sub.add_parser("refine-l1", help="L2 预测 + L1 算法融合，写入 prediction_fused.json")
    p_ref.add_argument("--run-id", required=True)
    p_ref.add_argument("--issue", help="仅修正单期（默认全 run）")
    p_ref.add_argument("-d", "--data", type=Path)

    args = ap.parse_args()
    run_dir = DEFAULT_RUNS_DIR / args.run_id if hasattr(args, "run_id") and args.run_id else None

    if args.cmd == "prepare":
        formats = parse_formats(args.format)
        path = prepare_run(
            run_id=args.run_id,
            periods=args.periods,
            formats=formats,
            data_path=args.data,
            strict=not args.no_strict,
        )
        st = status_run(path)
        print(json.dumps({"ok": True, "run_dir": str(path.resolve()), "status": st}, ensure_ascii=False, indent=2))
        return 0

    assert run_dir is not None
    if not run_dir.is_dir():
        raise SystemExit(f"run 不存在: {run_dir}")

    if args.cmd == "status":
        print(json.dumps(status_run(run_dir), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "next":
        nxt = next_pending(run_dir)
        if nxt is None:
            print(json.dumps({"ok": True, "pending": None, "message": "全部已完成"}, ensure_ascii=False))
        else:
            print(json.dumps({"ok": True, "pending": nxt}, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "record":
        record_prediction(run_dir, args.issue, args.file)
        print(json.dumps({"ok": True, "issue": args.issue, "status": status_run(run_dir)}, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "validate":
        report = validate_run(run_dir)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            status = "通过" if report["valid"] else "失败"
            print(f"校验 {status}: {report['run_id']} ({report['recorded']}/{report['expected']} 期)")
            for e in report["errors"]:
                print(f"  ERROR: {e}")
            for w in report["warnings"]:
                print(f"  WARN: {w}")
        return 0 if report["valid"] else 1

    if args.cmd == "seal-out":
        dst = seal_answers_out(run_dir)
        print(json.dumps({"ok": True, "external": str(dst.resolve())}, ensure_ascii=False))
        return 0

    if args.cmd == "restore-answers":
        restored = restore_answers_for_score(run_dir)
        print(json.dumps({"ok": True, "restored": restored}, ensure_ascii=False))
        return 0

    if args.cmd == "refine-l1":
        result = refine_l1_run(run_dir, data_path=args.data, issue=args.issue)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "score":
        summary = score_run(
            run_dir,
            baseline_trials=args.baseline_trials,
            seed=args.seed,
            compare_algo=args.compare_algo,
            fuse_l1=args.fuse_l1,
            data_path=args.data,
            skip_validation=args.skip_validation,
        )
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(format_score_report(summary))
            print(f"\n明细已写入: {run_dir / 'score_report.json'}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
