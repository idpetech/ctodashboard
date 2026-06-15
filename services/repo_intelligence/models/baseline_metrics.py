"""Numerical models for baseline repository metrics (no interpretation)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class RepoSizeMetrics:
    total_files: int
    total_loc: int
    measured_loc: int
    projected_loc: int
    measured_files: int
    projected_files: int
    estimation_method: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LocProfileMetrics:
    """Repo-specific LOC measurements from sampled file content."""

    sample_files: int
    avg_bytes_per_line: float
    avg_loc_per_file: float
    max_loc_per_file: int
    max_loc_file_path: str
    max_line_length: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LanguageShare:
    file_count: int
    percent: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContributorCount:
    author: str
    commit_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContributorMetrics:
    total: int
    commits_per_contributor: List[ContributorCount] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "commits_per_contributor": [row.to_dict() for row in self.commits_per_contributor],
        }


@dataclass
class ActivityMetrics:
    commits_last_7_days: int
    commits_last_30_days: int
    last_commit_timestamp: str
    churn_rate_files_per_commit: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BaselineMetrics:
    snapshot_id: str
    repo_full_name: str
    computed_at: str
    metrics_version: int
    repo_size: RepoSizeMetrics
    loc_profile: LocProfileMetrics
    language_distribution: Dict[str, LanguageShare]
    contributors: ContributorMetrics
    activity: ActivityMetrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "repo_full_name": self.repo_full_name,
            "computed_at": self.computed_at,
            "metrics_version": self.metrics_version,
            "repo_size": self.repo_size.to_dict(),
            "loc_profile": self.loc_profile.to_dict(),
            "language_distribution": {
                lang: share.to_dict() for lang, share in sorted(self.language_distribution.items())
            },
            "contributors": self.contributors.to_dict(),
            "activity": self.activity.to_dict(),
        }
