#!/usr/bin/env python3
"""
Run Analysis Layer v1 on pipeline artifacts (files) or persisted snapshot (DB).

Examples:
  # From E2E --out files
  ./venv/bin/python scripts/run_analysis.py --dir /tmp/repo-intel

  # From Postgres (after E2E --persist)
  ./venv/bin/python scripts/run_analysis.py --snapshot-id YOUR_SNAPSHOT_ID

  # Via Flask API + DB
  ENABLE_ANALYSIS_LAYER=true ./venv/bin/python scripts/run_analysis.py \\
    --snapshot-id YOUR_SNAPSHOT_ID --api http://localhost:8520
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()
if not os.getenv("RAILWAY_ENVIRONMENT"):
    load_dotenv(ROOT / ".env.local", override=True)


def build_pipeline_result_from_files(artifact_dir: Path) -> Dict[str, Any]:
    snapshot_path = artifact_dir / "snapshot.json"
    index_path = artifact_dir / "code_index.json"
    metrics_path = artifact_dir / "metrics.json"

    for path in (snapshot_path, index_path, metrics_path):
        if not path.is_file():
            raise SystemExit(f"Missing required file: {path}")

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    code_index: List[Dict[str, Any]] = json.loads(index_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    repo = snapshot.get("repository") or {}
    return {
        "snapshot_id": str(snapshot.get("snapshot_id") or ""),
        "repository_id": "",
        "repo_full_name": str(repo.get("full_name") or ""),
        "head_commit_sha": str(repo.get("head_commit_sha") or ""),
        "file_count": int((metrics.get("repo_size") or {}).get("total_files") or 0),
        "index_eligible": len(code_index),
        "indexed_files": len(code_index),
        "result_fingerprint": "",
        "snapshot": snapshot,
        "code_index": code_index,
        "metrics": metrics,
    }


def post_analysis_api(
    api_base: str,
    *,
    pipeline_result: Dict[str, Any] | None = None,
    snapshot_id: str | None = None,
    workspace_id: str | None = None,
) -> Dict[str, Any]:
    url = api_base.rstrip("/") + "/analysis/run"
    payload: Dict[str, Any] = {}
    if snapshot_id:
        payload["snapshot_id"] = snapshot_id
        if workspace_id:
            payload["workspace_id"] = workspace_id
    else:
        payload["pipeline_result"] = pipeline_result
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach {url}. Is Flask running? Set ENABLE_ANALYSIS_LAYER=true.\n{exc}"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CTO Lens analysis")
    parser.add_argument("--dir", type=Path, help="E2E artifact dir (snapshot/code_index/metrics JSON)")
    parser.add_argument("--snapshot-id", help="Load persisted data from Postgres by snapshot_id")
    parser.add_argument("--workspace", help="Optional workspace guard when using --snapshot-id")
    parser.add_argument("--out", type=Path, help="Write pipeline_result.json + analysis_result.json")
    parser.add_argument("--api", help="POST to Flask (e.g. http://localhost:8520)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.snapshot_id and not args.dir:
        parser.error("Provide --snapshot-id (DB) or --dir (JSON files)")

    pipeline_result: Dict[str, Any] | None = None
    if args.snapshot_id:
        if args.api:
            result = post_analysis_api(
                args.api,
                snapshot_id=args.snapshot_id,
                workspace_id=args.workspace,
            )
        else:
            from analysis.engine import AnalysisEngine
            from analysis.pipeline_loader import load_pipeline_result_from_db

            pipeline_result = load_pipeline_result_from_db(
                args.snapshot_id,
                workspace_id=args.workspace,
            )
            result = AnalysisEngine().run(pipeline_result)
    else:
        pipeline_result = build_pipeline_result_from_files(args.dir)
        if args.api:
            result = post_analysis_api(args.api, pipeline_result=pipeline_result)
        else:
            from analysis.engine import AnalysisEngine

            result = AnalysisEngine().run(pipeline_result)

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        if pipeline_result is None and args.snapshot_id:
            from analysis.pipeline_loader import load_pipeline_result_from_db

            pipeline_result = load_pipeline_result_from_db(
                args.snapshot_id,
                workspace_id=args.workspace,
            )
        if pipeline_result is not None:
            (args.out / "pipeline_result.json").write_text(
                json.dumps(pipeline_result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        (args.out / "analysis_result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {args.out / 'analysis_result.json'}")

    print("\n=== Analysis summary ===")
    print(f"  risk_score: {result['summary']['risk_score']}")
    print(f"  findings:   {len(result.get('findings') or [])}")
    if result.get("snapshot_id"):
        print(f"  snapshot_id:{result['snapshot_id']}")
    for row in result["summary"].get("top_risks") or []:
        print(f"  - [{row.get('severity')}] {row.get('title')}")

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
