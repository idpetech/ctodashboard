#!/usr/bin/env python3
"""Offline deterministic checks for repository snapshot tree building (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from services.repo_intelligence.github_client import GitHubRepoClient
from services.repo_intelligence.tree_builder import build_folder_tree, should_ignore_path

SAMPLE_TREE = [
    {"path": "node_modules/pkg/index.js", "type": "blob", "sha": "x", "size": 10},
    {"path": "src/main.py", "type": "blob", "sha": "aaa", "size": 120},
    {"path": "src", "type": "tree", "sha": "bbb"},
    {"path": "README.md", "type": "blob", "sha": "ccc", "size": 40},
    {"path": "build/output.js", "type": "blob", "sha": "ddd", "size": 5},
]


def main() -> int:
    assert should_ignore_path("foo/node_modules/bar")
    assert should_ignore_path("target/classes/App.class")
    assert not should_ignore_path("src/main.py")

    owner, name = GitHubRepoClient.parse_repo_identifier("https://github.com/octocat/Hello-World.git")
    assert owner == "octocat" and name == "Hello-World"
    owner2, name2 = GitHubRepoClient.parse_repo_identifier("octocat/Hello-World")
    assert owner2 == "octocat" and name2 == "Hello-World"

    tree = build_folder_tree(list(reversed(SAMPLE_TREE)))
    child_names = [c["name"] for c in tree["children"]]
    assert child_names == ["src", "README.md"], f"unexpected order: {child_names}"
    src_children = [c["name"] for c in next(c for c in tree["children"] if c["name"] == "src")["children"]]
    assert src_children == ["main.py"]

    flattened = str(tree)
    assert "node_modules" not in flattened
    assert "build" not in flattened

    tree2 = build_folder_tree(SAMPLE_TREE)
    assert tree == tree2, "tree build must be deterministic"

    print("PASS: repository snapshot tree builder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
