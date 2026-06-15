"""Parse GitHub tree responses into deterministic file index entries."""

from __future__ import annotations

from typing import List

from services.repo_intelligence.config import max_tree_entries
from services.repo_intelligence.language_map import (
    extension_from_path,
    is_binary_extension,
    language_for_extension,
)
from services.repo_intelligence.models import FileIndexEntry, TreeNode, TreeStats


class TreeParseError(Exception):
    """Raised when tree data cannot be parsed within configured limits."""


def parse_tree_nodes(tree_items: List[dict]) -> List[TreeNode]:
    if len(tree_items) > max_tree_entries():
        raise TreeParseError(
            f"Tree has {len(tree_items)} entries; limit is {max_tree_entries()}"
        )

    nodes: List[TreeNode] = []
    for item in tree_items:
        path = (item.get("path") or "").strip()
        if not path:
            continue
        node_type = (item.get("type") or "").strip().lower()
        if node_type not in {"blob", "tree"}:
            continue
        nodes.append(
            TreeNode(
                path=path,
                git_sha=str(item.get("sha") or ""),
                size_bytes=int(item.get("size") or 0),
                node_type=node_type,
                mode=str(item.get("mode") or ""),
            )
        )

    # Deterministic ordering regardless of API sort guarantees.
    nodes.sort(key=lambda n: n.path)
    return nodes


def build_file_index_entries(nodes: List[TreeNode]) -> tuple[List[FileIndexEntry], TreeStats]:
    stats = TreeStats()
    entries: List[FileIndexEntry] = []

    for node in nodes:
        if node.node_type == "tree":
            stats.directory_count += 1
            continue

        stats.file_count += 1
        stats.total_blob_bytes += max(0, node.size_bytes)

        ext = extension_from_path(node.path)
        lang = language_for_extension(ext)
        if ext:
            stats.extension_counts[ext] = stats.extension_counts.get(ext, 0) + 1
        if lang:
            stats.language_counts[lang] = stats.language_counts.get(lang, 0) + 1

        depth = node.path.count("/")
        entries.append(
            FileIndexEntry(
                path=node.path,
                git_sha=node.git_sha,
                size_bytes=node.size_bytes,
                node_type=node.node_type,
                extension=ext,
                language=lang,
                depth=depth,
            )
        )

    entries.sort(key=lambda e: e.path)
    return entries, stats


def is_text_candidate(entry: FileIndexEntry) -> bool:
    if entry.node_type != "blob":
        return False
    if is_binary_extension(entry.extension):
        return False
    return True
