#!/usr/bin/env python3
"""Offline deterministic checks for Analysis Layer v1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from analysis.engine import AnalysisEngine, AnalysisEngineError, validate_pipeline_result

FIXTURE = {
    "snapshot_id": "snap1",
    "repository_id": "repo1",
    "repo_full_name": "acme/demo",
    "head_commit_sha": "abc123",
    "file_count": 50,
    "index_eligible": 10,
    "indexed_files": 4,
    "result_fingerprint": "fp",
    "snapshot": {
        "snapshot_id": "snap1",
        "repository": {"full_name": "acme/demo", "last_synced_at": "2026-06-01T00:00:00Z"},
        "commits": [{"hash": "c1", "author": "alice", "timestamp": "2026-06-01T00:00:00Z", "files_changed_count": 1}],
    },
    "code_index": [
        {
            "file_path": "controllers/api.py",
            "language": "Python",
            "symbols": {"functions": [{"name": f"fn{i}", "line": i} for i in range(25)], "classes": []},
            "imports": [
                {"module": "services.database", "names": ["db"], "line": 1, "kind": "internal"},
                *[{"module": f"pkg.m{i}", "names": [], "line": i, "kind": "external"} for i in range(30)],
            ],
        },
        {
            "file_path": "services/database.py",
            "language": "Python",
            "symbols": {"functions": [], "classes": []},
            "imports": [{"module": "controllers.api", "names": ["api"], "line": 1, "kind": "internal"}],
        },
        *[
            {
                "file_path": f"services/shared/hub{i}.py",
                "language": "Python",
                "symbols": {"functions": [], "classes": []},
                "imports": [{"module": "services.database", "names": [], "line": 1, "kind": "internal"}],
            }
            for i in range(6)
        ],
    ],
    "metrics": {
        "metrics_version": 2,
        "repo_size": {"total_files": 50, "total_loc": 12000},
        "contributors": {
            "total": 2,
            "commits_per_contributor": [
                {"author": "alice", "commit_count": 70},
                {"author": "bob", "commit_count": 30},
            ],
        },
        "activity": {
            "commits_last_30_days": 25,
            "commits_last_7_days": 8,
            "churn_rate_files_per_commit": 1.2,
            "last_commit_timestamp": "2026-06-01T00:00:00Z",
        },
    },
}


def main() -> int:
    try:
        validate_pipeline_result({"snapshot": {}, "metrics": {}})
        raise AssertionError("expected validation failure")
    except AnalysisEngineError:
        pass

    engine = AnalysisEngine()
    first = engine.run(FIXTURE)
    second = engine.run(FIXTURE)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True), "non-deterministic output"

    categories = {row["category"] for row in first["findings"]}
    assert "architecture" in categories
    assert "code_health" in categories
    assert "delivery" in categories

    score = first["summary"]["risk_score"]
    assert 0 <= score <= 100
    assert len(first["summary"]["top_risks"]) <= 5

    print("PASS: analysis layer deterministic")
    print("risk_score:", score)
    print("findings:", len(first["findings"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
