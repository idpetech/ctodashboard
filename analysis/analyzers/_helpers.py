"""Shared deterministic helpers for analyzers (no I/O)."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Set


def slug(value: str, *, max_len: int = 80) -> str:
    text = "".join(char if char.isalnum() else "_" for char in (value or "").lower())
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")[:max_len] or "unknown"


def module_path_hint(module: str) -> str:
    normalized = (module or "").strip().lstrip(".")
    if not normalized:
        return ""
    return normalized.replace(".", "/") + ".py"


def internal_imports(entry: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in entry.get("imports") or []:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("kind") or "") != "internal":
            continue
        rows.append(dict(item))
    rows.sort(key=lambda row: (str(row.get("module") or ""), int(row.get("line") or 0)))
    return rows


def import_targets(entry: Mapping[str, Any]) -> Set[str]:
    targets: Set[str] = set()
    for item in internal_imports(entry):
        hint = module_path_hint(str(item.get("module") or ""))
        if hint:
            targets.add(hint)
    return targets


def file_matches_import_hint(file_path: str, hint: str) -> bool:
    if not file_path or not hint:
        return False
    return file_path == hint or file_path.endswith("/" + hint) or file_path.endswith(hint)


def importer_targets_file(importer: Mapping[str, Any], target_path: str) -> bool:
    for hint in import_targets(importer):
        if file_matches_import_hint(target_path, hint):
            return True
    return False


def symbol_count(entry: Mapping[str, Any]) -> int:
    symbols = entry.get("symbols") or {}
    functions = symbols.get("functions") or []
    classes = symbols.get("classes") or []
    method_count = 0
    for cls in classes:
        if isinstance(cls, Mapping):
            method_count += len(cls.get("methods") or [])
    return len(functions) + len(classes) + method_count


def path_segments(file_path: str) -> Iterable[str]:
    return (segment.lower() for segment in (file_path or "").split("/") if segment)
