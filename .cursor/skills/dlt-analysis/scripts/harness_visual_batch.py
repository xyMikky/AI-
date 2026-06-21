#!/usr/bin/env python3
"""L2 visual harness 批量辅助：列出待测、落盘预测、批量 record.

⚠️ 默认强制单期隔离：pending 默认 limit=1；record-batch 需 --unsafe-allow-batch。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness_isolation import MAX_ISSUES_PER_DISPATCH
from harness_visual import DEFAULT_RUNS_DIR, record_prediction, status_run

SKILL_ROOT = Path(__file__).resolve().parent.parent


def period_paths(run_id: str, issue: str) -> dict[str, str]:
    pdir = DEFAULT_RUNS_DIR / run_id / "periods" / issue
    return {
        "period_dir": str(pdir.resolve()),
        "trend_50": str((pdir / "trend-50.png").resolve()),
        "local_15": str((pdir / "local-trend-15.png").resolve()),
        "agent_prompt": str((pdir / "agent_prompt.md").resolve()),
        "stats": str((pdir / "stats.txt").resolve()),
    }


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("未找到 JSON")
    return json.loads(m.group(0))


def record_raw(run_id: str, issue: str, raw: dict) -> None:
    pdir = DEFAULT_RUNS_DIR / run_id / "periods" / issue
    tmp = pdir / "_incoming.json"
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    record_prediction(DEFAULT_RUNS_DIR / run_id, issue, tmp)


def main() -> int:
    ap = argparse.ArgumentParser(description="L2 batch helper（默认单期隔离）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_run(p: argparse.ArgumentParser) -> None:
        p.add_argument("--run-id", required=True)

    p_st = sub.add_parser("status", help="同 harness_visual status")
    add_run(p_st)

    p_list = sub.add_parser("pending", help="列出未完成期号 JSON（默认最多 1 期）")
    add_run(p_list)
    p_list.add_argument("--limit", type=int, default=1, help="默认 1，禁止批量派发")
    p_list.add_argument(
        "--unsafe-allow-multi",
        action="store_true",
        help="允许 limit>1（不推荐；易导致 subagent 批内污染）",
    )

    p_path = sub.add_parser("paths", help="单期路径（供 Task 附件）")
    add_run(p_path)
    p_path.add_argument("--issue", required=True)

    p_rec = sub.add_parser("record-json", help="从文件或 stdin 落盘（单期）")
    add_run(p_rec)
    p_rec.add_argument("--issue", required=True)
    p_rec.add_argument("--file", type=Path)

    p_batch = sub.add_parser("record-batch", help="批量落盘（默认禁止）")
    add_run(p_batch)
    p_batch.add_argument("--file", type=Path, required=True)
    p_batch.add_argument(
        "--unsafe-allow-batch",
        action="store_true",
        help="显式允许批量落盘（仅调试；不能替代逐期看图）",
    )

    p_fin = sub.add_parser("finalize", help="扫描已有 prediction.json 并 record")
    add_run(p_fin)

    args = ap.parse_args()
    run_dir = DEFAULT_RUNS_DIR / args.run_id

    if args.cmd == "status":
        print(json.dumps(status_run(run_dir), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "pending":
        limit = args.limit
        if limit > MAX_ISSUES_PER_DISPATCH and not args.unsafe_allow_multi:
            print(
                json.dumps(
                    {
                        "error": (
                            f"pending --limit={limit} 违反单期隔离（max={MAX_ISSUES_PER_DISPATCH}）。"
                            "请逐期 next 派发，或加 --unsafe-allow-multi（不推荐）。"
                        ),
                        "max_issues_per_dispatch": MAX_ISSUES_PER_DISPATCH,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2
        st = status_run(run_dir)
        pending = [x["target_issue"] for x in st["items"] if not x["done"]]
        if limit:
            pending = pending[:limit]
        print(
            json.dumps(
                {
                    "pending": pending,
                    "count": len(pending),
                    "isolation": "single" if limit <= 1 else "multi-unsafe",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.cmd == "paths":
        print(json.dumps(period_paths(args.run_id, args.issue), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "record-json":
        raw_text = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
        raw = extract_json(raw_text)
        record_raw(args.run_id, args.issue, raw)
        print(json.dumps({"ok": True, "issue": args.issue}, ensure_ascii=False))
        return 0

    if args.cmd == "record-batch":
        if not args.unsafe_allow_batch:
            print(
                json.dumps(
                    {
                        "error": (
                            "record-batch 默认禁止（批量落盘不能证明逐期看图）。"
                            "请改用 harness_visual.py record --issue 单期落盘，"
                            "或加 --unsafe-allow-batch 仅作调试。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2
        data = extract_json(args.file.read_text(encoding="utf-8"))
        items = data.get("results") or data
        if len(items) > MAX_ISSUES_PER_DISPATCH:
            print(
                json.dumps(
                    {
                        "error": (
                            f"批量 {len(items)} 期违反单期隔离。"
                            "禁止用 transcript 批量 ingest 替代逐期 subagent。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2
        ok = []
        for item in items:
            issue = str(item["issue"])
            pred = item.get("prediction") or item
            if "predictions" not in pred and "target_issue" in pred:
                pass
            elif "prediction" in pred:
                pred = pred["prediction"]
            record_raw(args.run_id, issue, pred)
            ok.append(issue)
        print(json.dumps({"ok": True, "recorded": ok, "count": len(ok)}, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "finalize":
        recorded = []
        periods_dir = run_dir / "periods"
        for pdir in sorted(periods_dir.iterdir()):
            pred = pdir / "prediction.json"
            if not pred.is_file():
                continue
            issue = pdir.name
            meta_path = pdir / "meta.json"
            if meta_path.is_file():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta.get("status") == "done":
                    continue
            record_prediction(run_dir, issue, pred)
            recorded.append(issue)
        st = status_run(run_dir)
        print(json.dumps({"ok": True, "newly_recorded": recorded, "status": st}, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
