"""Git commit metadata aggregation (deterministic, numerical only)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from services.repo_intelligence.models.baseline_metrics import (
    ActivityMetrics,
    ContributorCount,
    ContributorMetrics,
)


def _parse_timestamp(value: str) -> Optional[datetime]:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _reference_time(commits: Sequence[Dict[str, Any]], fallback_iso: str) -> datetime:
    parsed = [_parse_timestamp(str(c.get("timestamp") or "")) for c in commits]
    valid = [dt for dt in parsed if dt is not None]
    if valid:
        return max(valid)
    fallback = _parse_timestamp(fallback_iso)
    if fallback:
        return fallback
    return datetime.now(timezone.utc).replace(microsecond=0)


def analyze_contributors(commits: Sequence[Dict[str, Any]]) -> ContributorMetrics:
    counts: Counter[str] = Counter()
    for commit in commits:
        author = str(commit.get("author") or "unknown").strip() or "unknown"
        counts[author] += 1

    rows = [
        ContributorCount(author=author, commit_count=count)
        for author, count in sorted(counts.items(), key=lambda row: (-row[1], row[0]))
    ]
    return ContributorMetrics(total=len(counts), commits_per_contributor=rows)


def analyze_activity(
    commits: Sequence[Dict[str, Any]],
    *,
    reference_iso: str,
) -> ActivityMetrics:
    reference = _reference_time(commits, reference_iso)
    window_7 = reference - timedelta(days=7)
    window_30 = reference - timedelta(days=30)

    commits_7 = 0
    commits_30 = 0
    last_commit = ""
    file_counts: List[int] = []

    for commit in commits:
        ts = _parse_timestamp(str(commit.get("timestamp") or ""))
        if ts is None:
            continue
        if ts >= window_7:
            commits_7 += 1
        if ts >= window_30:
            commits_30 += 1
        iso = ts.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if not last_commit or iso > last_commit:
            last_commit = iso

        files_changed = int(commit.get("files_changed_count") or 0)
        if files_changed >= 0:
            file_counts.append(files_changed)

    churn = 0.0
    if file_counts:
        churn = round(sum(file_counts) / len(file_counts), 4)

    return ActivityMetrics(
        commits_last_7_days=commits_7,
        commits_last_30_days=commits_30,
        last_commit_timestamp=last_commit,
        churn_rate_files_per_commit=churn,
    )
