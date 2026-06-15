#!/usr/bin/env python3
"""
Local Repo Intelligence CLI — scan working tree without GitHub API.

Runs: local snapshot → code index → baseline metrics → optional analysis/report.

Examples:
  # Scan current repo checkout (uses local git log when .git exists)
  ./venv/bin/python scripts/repo_intelligence_local.py --out /tmp/repo-intel

  # Full local stack through CTO report JSON
  ./venv/bin/python scripts/repo_intelligence_local.py \\
    --root . --out /tmp/repo-intel --analyze --report

  # Ignore extra paths (comma-separated path segments)
  REPO_INTEL_IGNORE_SEGMENTS=_attic,exports \\
    ./venv/bin/python scripts/repo_intelligence_local.py --out /tmp/repo-intel
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.repo_intelligence.local_pipeline import (  # noqa: E402
    LocalPipelineError,
    run_local_repo_ingestion,
)
from services.repo_intelligence.pipeline import PipelineOptions  # noqa: E402


def _print_summary(result) -> None:
    print("\n=== Local repository snapshot ===")
    print(f"  snapshot_id:   {result.snapshot_id}")
    print(f"  full_name:     {result.repo_full_name}")
    print(f"  head_commit:   {result.head_commit_sha[:12]}...")
    print(f"  total_files:   {result.file_count}")
    print(f"  index_eligible:{result.index_eligible}")
    print(f"  indexed_files: {result.indexed_files}")
    print(f"  fingerprint:   {result.result_fingerprint}")

    metrics = result.metrics or {}
    if metrics:
        size = metrics.get("repo_size") or {}
        activity = metrics.get("activity") or {}
        print("\n=== Baseline metrics ===")
        print(f"  total_loc:       {size.get('total_loc')}")
        print(f"  commits 30d:     {activity.get('commits_last_30_days')}")
        contrib = metrics.get("contributors") or {}
        print(f"  contributors:    {contrib.get('total')}")


def _write_artifacts(out_dir: Path, result) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = out_dir / "snapshot.json"
    index_path = out_dir / "code_index.json"
    metrics_path = out_dir / "metrics.json"
    pipeline_path = out_dir / "pipeline_result.json"

    snapshot_path.write_text(
        json.dumps(result.snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    index_path.write_text(
        json.dumps(result.code_index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(result.metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pipeline_path.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {snapshot_path}")
    print(f"Wrote {index_path}")
    print(f"Wrote {metrics_path}")
    print(f"Wrote {pipeline_path}")


def _build_pipeline_result(artifact_dir: Path) -> dict:
    snapshot = json.loads((artifact_dir / "snapshot.json").read_text(encoding="utf-8"))
    code_index = json.loads((artifact_dir / "code_index.json").read_text(encoding="utf-8"))
    metrics = json.loads((artifact_dir / "metrics.json").read_text(encoding="utf-8"))
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


def _run_analysis(artifact_dir: Path) -> dict:
    from analysis.engine import AnalysisEngine

    pipeline_result = _build_pipeline_result(artifact_dir)
    analysis_result = AnalysisEngine().run(pipeline_result)
    out_path = artifact_dir / "analysis_result.json"
    out_path.write_text(json.dumps(analysis_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    summary = analysis_result.get("summary") or {}
    print(f"  risk_score: {summary.get('risk_score')}")
    print(f"  findings:   {len(analysis_result.get('findings') or [])}")
    return analysis_result


def _run_report(artifact_dir: Path, analysis_result: dict | None = None) -> dict:
    from reporting.agent import CTOReportAgent

    if analysis_result is None:
        analysis_result = json.loads((artifact_dir / "analysis_result.json").read_text(encoding="utf-8"))
    report = CTOReportAgent().run(analysis_result)
    out_path = artifact_dir / "cto_report.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    summary = report.get("executive_summary") or {}
    print(f"  health:     {summary.get('overall_health')}")
    print(f"  risk_score: {summary.get('risk_score')}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Repo Intelligence pipeline (no GitHub)")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help=f"Repository root to scan (default: {ROOT})",
    )
    parser.add_argument(
        "--name",
        help="Synthetic repo full name (default: local/<directory-name>)",
    )
    parser.add_argument("--out", type=Path, help="Write snapshot/code_index/metrics JSON here")
    parser.add_argument("--skip-index", action="store_true", help="Only build folder snapshot")
    parser.add_argument("--skip-metrics", action="store_true", help="Skip baseline metrics")
    parser.add_argument("--analyze", action="store_true", help="Run analysis layer on artifacts")
    parser.add_argument("--report", action="store_true", help="Generate CTO report (implies --analyze)")
    parser.add_argument("--json", action="store_true", help="Print pipeline_result JSON to stdout")
    args = parser.parse_args()

    if args.report:
        args.analyze = True

    options = PipelineOptions(
        persist=False,
        skip_index=bool(args.skip_index),
        skip_metrics=bool(args.skip_metrics),
    )

    try:
        result = run_local_repo_ingestion(
            args.root,
            repo_full_name=args.name,
            options=options,
        )
    except (LocalPipelineError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    _print_summary(result)

    out_dir = args.out
    if out_dir:
        _write_artifacts(out_dir, result)
    elif args.analyze or args.report:
        parser.error("--analyze/--report require --out")

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))

    analysis_result = None
    if args.analyze and out_dir:
        print("\n=== Analysis ===")
        analysis_result = _run_analysis(out_dir)

    if args.report and out_dir and analysis_result is not None:
        print("\n=== CTO report ===")
        _run_report(out_dir, analysis_result)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
