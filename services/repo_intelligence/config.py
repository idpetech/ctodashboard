"""Runtime configuration for repo intelligence (deterministic, bounded)."""

from __future__ import annotations

import os

INDEX_VERSION = 1

DEFAULT_MAX_TREE_ENTRIES = 50_000
DEFAULT_MAX_BLOB_BYTES = 262_144
DEFAULT_MAX_LINE_COUNT_FILES = 5_000
DEFAULT_GITHUB_TIMEOUT_SECONDS = 30
DEFAULT_GITHUB_PAGE_SIZE = 100
DEFAULT_MAX_COMMITS = 100
SNAPSHOT_VERSION = 1
CODE_INDEX_VERSION = 1
BASELINE_METRICS_VERSION = 2
DEFAULT_MAX_CODE_INDEX_FILES = 2_000
DEFAULT_MAX_CODE_INDEX_BYTES = 262_144
DEFAULT_INDEXABLE_LANGUAGES = "Python,JavaScript,TypeScript"
DEFAULT_LOC_BYTES_DIVISOR = 40
DEFAULT_LOC_SAMPLE_FILES = 100
DEFAULT_LOC_SAMPLE_MAX_BYTES = 262_144


def is_repo_intelligence_enabled() -> bool:
    return os.getenv("ENABLE_REPO_INTELLIGENCE", "false").lower() == "true"


def max_tree_entries() -> int:
    return _positive_int("REPO_INTEL_MAX_TREE_ENTRIES", DEFAULT_MAX_TREE_ENTRIES)


def max_blob_bytes() -> int:
    return _positive_int("REPO_INTEL_MAX_BLOB_BYTES", DEFAULT_MAX_BLOB_BYTES)


def max_line_count_files() -> int:
    return _positive_int("REPO_INTEL_MAX_LINE_COUNT_FILES", DEFAULT_MAX_LINE_COUNT_FILES)


def github_timeout_seconds() -> int:
    return _positive_int("REPO_INTEL_GITHUB_TIMEOUT", DEFAULT_GITHUB_TIMEOUT_SECONDS)


def max_commits() -> int:
    return _positive_int("REPO_SNAPSHOT_MAX_COMMITS", DEFAULT_MAX_COMMITS)


def max_code_index_files() -> int:
    return _positive_int("REPO_CODE_INDEX_MAX_FILES", DEFAULT_MAX_CODE_INDEX_FILES)


def max_code_index_bytes() -> int:
    return _positive_int("REPO_CODE_INDEX_MAX_BYTES", DEFAULT_MAX_CODE_INDEX_BYTES)


def indexable_languages() -> list[str]:
    raw = os.getenv("REPO_CODE_INDEX_LANGUAGES", DEFAULT_INDEXABLE_LANGUAGES)
    return [part.strip() for part in raw.split(",") if part.strip()]


def loc_bytes_divisor() -> int:
    return _positive_int("REPO_BASELINE_LOC_BYTES_DIVISOR", DEFAULT_LOC_BYTES_DIVISOR)


def loc_sample_files() -> int:
    return _positive_int("REPO_BASELINE_LOC_SAMPLE_FILES", DEFAULT_LOC_SAMPLE_FILES)


def loc_sample_max_bytes() -> int:
    return _positive_int("REPO_BASELINE_LOC_SAMPLE_MAX_BYTES", DEFAULT_LOC_SAMPLE_MAX_BYTES)


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return default
