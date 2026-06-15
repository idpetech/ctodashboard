"""Build deterministic folder trees from GitHub recursive tree responses."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Set

from services.repo_intelligence.snapshot_models import FolderNode

IGNORED_SEGMENTS: frozenset[str] = frozenset(
    {
        "node_modules",
        "target",
        "build",
        ".git",
        "venv",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "_attic",
    }
)


def ignored_segments() -> frozenset[str]:
    extra = os.getenv("REPO_INTEL_IGNORE_SEGMENTS", "")
    if not extra.strip():
        return IGNORED_SEGMENTS
    merged = set(IGNORED_SEGMENTS)
    for part in extra.split(","):
        token = part.strip()
        if token:
            merged.add(token)
    return frozenset(merged)


def should_ignore_path(path: str) -> bool:
    if not path:
        return False
    blocked = ignored_segments()
    return any(segment in blocked for segment in path.split("/"))


def filter_tree_items(tree_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return sorted tree items with ignored paths removed."""
    filtered: List[Dict[str, Any]] = []
    for item in tree_items:
        path = (item.get("path") or "").strip()
        if not path or should_ignore_path(path):
            continue
        filtered.append(item)
    filtered.sort(key=lambda row: row.get("path") or "")
    return filtered


def build_folder_tree(tree_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a nested directory tree from flat GitHub tree entries.
    Deterministic: children sorted by name at every level.
    """
    filtered = filter_tree_items(tree_items)
    root = FolderNode(name="", path="", type="directory", children=[])
    dir_nodes: Dict[str, FolderNode] = {"": root}
    dir_paths: Set[str] = set()

    for item in filtered:
        path = item["path"]
        node_type = (item.get("type") or "").lower()
        parts = path.split("/")

        for depth in range(len(parts) - (0 if node_type == "tree" else 1)):
            dir_path = "/".join(parts[: depth + 1])
            if dir_path in dir_paths:
                continue
            parent_path = "/".join(parts[:depth]) if depth else ""
            parent = dir_nodes[parent_path]
            name = parts[depth]
            child = FolderNode(name=name, path=dir_path, type="directory", children=[])
            parent.children.append(child)
            dir_nodes[dir_path] = child
            dir_paths.add(dir_path)

        if node_type == "blob":
            parent_path = "/".join(parts[:-1]) if len(parts) > 1 else ""
            parent = dir_nodes[parent_path]
            parent.children.append(
                FolderNode(
                    name=parts[-1],
                    path=path,
                    type="file",
                    size_bytes=int(item.get("size") or 0),
                    git_sha=str(item.get("sha") or ""),
                )
            )

    _sort_tree_children(root)
    return root.to_dict()


def _sort_tree_children(node: FolderNode) -> None:
    node.children.sort(key=lambda child: (child.type != "directory", child.name))
    for child in node.children:
        if child.type == "directory":
            _sort_tree_children(child)
