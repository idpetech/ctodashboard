#!/usr/bin/env python3
"""Offline deterministic checks for baseline metrics engine."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from services.repo_intelligence.metrics_engine import (
    _build_loc_profile,
    _compute_repo_size,
    _sample_file_lines,
    compute_baseline_metrics,
)

FIXTURE = {
    "snapshot_id": "snap123",
    "repository": {
        "full_name": "acme/demo",
        "last_synced_at": "2026-06-15T12:00:00Z",
    },
    "folder_structure": {
        "type": "directory",
        "children": [
            {"type": "file", "path": "src/main.py", "size_bytes": 400, "git_sha": "1"},
            {"type": "file", "path": "src/app.js", "size_bytes": 200, "git_sha": "2"},
            {"type": "file", "path": "README.md", "size_bytes": 80, "git_sha": "3"},
        ],
    },
    "commits": [
        {"hash": "c1", "author": "alice", "timestamp": "2026-06-14T10:00:00Z", "files_changed_count": 4},
    ],
}

CONTENTS = {
    "1": b"short\n" + b"x" * 120 + b"\nline3\nline4\n",
    "2": b"a\nb\n",
    "3": b"# title\n",
}


def main() -> int:
    files = FIXTURE["folder_structure"]["children"]

    measured, sample_bytes, max_line_len = _sample_file_lines(files, None)
    fallback_profile = _build_loc_profile(measured, sample_bytes, max_line_len)
    fallback_size = _compute_repo_size(files, measured, fallback_profile)
    assert fallback_size.estimation_method.startswith("fixed_divisor_")
    assert fallback_profile.sample_files == 0
    assert fallback_profile.avg_bytes_per_line == 0.0

    def fetcher(sha: str) -> bytes:
        return CONTENTS[sha]

    measured, sample_bytes, max_line_len = _sample_file_lines(files, fetcher)
    profile = _build_loc_profile(measured, sample_bytes, max_line_len)
    size = _compute_repo_size(files, measured, profile)

    assert profile.sample_files == 3
    assert profile.avg_loc_per_file == 2.3333
    assert profile.max_loc_per_file == 4
    assert profile.max_loc_file_path == "src/main.py"
    assert profile.max_line_length == 120
    assert size.total_loc == 7
    assert size.measured_loc == 7

    metrics = compute_baseline_metrics(
        FIXTURE,
        computed_at="2026-06-15T12:00:00Z",
        content_fetcher=fetcher,
    ).to_dict()
    assert metrics["loc_profile"]["avg_loc_per_file"] == 2.3333
    assert metrics["loc_profile"]["max_loc_per_file"] == 4
    assert metrics["repo_size"]["total_files"] == 3

    again = compute_baseline_metrics(
        FIXTURE,
        computed_at="2026-06-15T12:00:00Z",
        content_fetcher=fetcher,
    ).to_dict()
    assert json.dumps(again, sort_keys=True) == json.dumps(metrics, sort_keys=True)

    print("PASS: baseline metrics engine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
