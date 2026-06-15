#!/usr/bin/env python3
"""Offline deterministic checks for code index builder (no network, no DB)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from services.repo_intelligence.indexer import index_file_content

PYTHON_SAMPLE = '''
import os
from services.repo_intelligence import indexer

class Worker:
    def run(self):
        return True

def main():
  return 1
'''

JS_SAMPLE = '''
import React from "react";
import { helper } from "./helper";

export class App {
  render() {
    return null;
  }
}

export function mount() {
  return true;
}

const run = async () => {};
'''


def main() -> int:
    indexed_at = "2026-06-15T12:00:00Z"
    repo_paths = ["services/repo_intelligence/indexer.py", "src/helper.js"]

    py_entry = index_file_content(
        "services/repo_intelligence/sample.py",
        PYTHON_SAMPLE,
        language="Python",
        repo_file_paths=repo_paths,
        indexed_at=indexed_at,
        git_sha="abc",
    )
    py_dict = py_entry.to_dict()
    assert py_dict["symbols"]["functions"] == [{"name": "main", "line": 9}]
    assert py_dict["symbols"]["classes"][0]["name"] == "Worker"
    assert py_dict["symbols"]["classes"][0]["methods"] == [{"name": "run", "line": 6}]
    internal = [row for row in py_dict["imports"] if row["kind"] == "internal"]
    external = [row for row in py_dict["imports"] if row["kind"] == "external"]
    assert any(row["module"] == "services.repo_intelligence" for row in internal)
    assert any(row["module"] == "os" for row in external)

    js_entry = index_file_content(
        "src/App.jsx",
        JS_SAMPLE,
        language="JavaScript",
        repo_file_paths=repo_paths,
        indexed_at=indexed_at,
        git_sha="def",
    )
    js_dict = js_entry.to_dict()
    fn_names = {row["name"] for row in js_dict["symbols"]["functions"]}
    assert "mount" in fn_names
    assert js_dict["symbols"]["classes"][0]["name"] == "App"
    assert any(row["module"] == "react" and row["kind"] == "external" for row in js_dict["imports"])
    assert any(row["module"] == "./helper" for row in js_dict["imports"])

    py_again = index_file_content(
        "services/repo_intelligence/sample.py",
        PYTHON_SAMPLE,
        language="Python",
        repo_file_paths=repo_paths,
        indexed_at=indexed_at,
        git_sha="abc",
    ).to_dict()
    assert py_again == py_dict
    assert json.dumps(py_again, sort_keys=True) == json.dumps(py_dict, sort_keys=True)

    print("PASS: code index builder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
