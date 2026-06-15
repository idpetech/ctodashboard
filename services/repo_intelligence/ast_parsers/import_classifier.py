"""Classify imports as internal (repo) vs external (third-party/stdlib)."""

from __future__ import annotations

from typing import FrozenSet, Iterable, List


def normalize_module_path(module: str) -> str:
    return (module or "").strip().lstrip(".")


def repo_module_roots(file_paths: Iterable[str]) -> FrozenSet[str]:
    """Top-level package/directory names present in the snapshot file list."""
    roots: set[str] = set()
    for path in file_paths:
        if not path or "/" not in path:
            continue
        roots.add(path.split("/", 1)[0])
    return frozenset(sorted(roots))


def classify_import(module: str, *, repo_roots: FrozenSet[str]) -> str:
    """
    Deterministic import classification.
    - Relative imports (leading dots) → internal
    - Module root matches a top-level repo directory → internal
    - Otherwise → external
    """
    raw = (module or "").strip()
    if not raw:
        return "external"
    if raw.startswith("."):
        return "internal"
    root = raw.split(".", 1)[0]
    if root in repo_roots:
        return "internal"
    return "external"


def sort_import_entries(entries: List[dict]) -> List[dict]:
    return sorted(entries, key=lambda row: (row.get("line", 0), row.get("module", "")))
