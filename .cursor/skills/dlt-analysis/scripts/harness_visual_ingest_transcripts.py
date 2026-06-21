#!/usr/bin/env python3
"""从 subagent jsonl transcript 提取 prediction JSON 并 record 到 visual run."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from harness_visual import DEFAULT_RUNS_DIR, record_prediction

JSON_RE = re.compile(
    r'\{\s*"target_issue"\s*:\s*"(?P<issue>\d+)"[\s\S]*?"predictions"\s*:\s*\{[\s\S]*?\}\s*,\s*"reviewed_charts"'
)


def extract_predictions(text: str) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for m in JSON_RE.finditer(text):
        block = m.group(0)
        # close brace for full object
        depth = 0
        end = 0
        for i, ch in enumerate(block):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if not end:
            continue
        try:
            obj = json.loads(block[:end])
        except json.JSONDecodeError:
            continue
        issue = obj.get("target_issue")
        if issue and "predictions" in obj:
            found[str(issue)] = obj
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("transcripts", nargs="+", type=Path)
    args = ap.parse_args()
    run_dir = DEFAULT_RUNS_DIR / args.run_id
    all_preds: dict[str, dict] = {}
    for tp in args.transcripts:
        if not tp.is_file():
            continue
        text = tp.read_text(encoding="utf-8", errors="replace")
        all_preds.update(extract_predictions(text))

    recorded = []
    for issue, pred in sorted(all_preds.items()):
        pdir = run_dir / "periods" / issue
        if not pdir.is_dir():
            continue
        tmp = pdir / "_from_transcript.json"
        tmp.write_text(json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8")
        record_prediction(run_dir, issue, tmp)
        recorded.append(issue)
    print(json.dumps({"recorded": recorded, "count": len(recorded)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
