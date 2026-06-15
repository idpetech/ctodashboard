"""Lightweight regex-based JS/TS symbol and import extraction (POC fallback)."""

from __future__ import annotations

import re
from typing import FrozenSet, List, Tuple

from services.repo_intelligence.ast_parsers.import_classifier import classify_import
from services.repo_intelligence.models.code_index import (
    ClassSymbol,
    FunctionSymbol,
    ImportEntry,
    MethodSymbol,
)

_IMPORT_RE = re.compile(
    r"^\s*import\s+(?:type\s+)?(?:(\w+)\s*,?\s*)?(?:\{([^}]+)\}\s*)?(?:\*\s+as\s+(\w+)\s*)?"
    r"(?:from\s+['\"]([^'\"]+)['\"])?\s*;?",
    re.MULTILINE,
)
_REQUIRE_RE = re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""")
_FUNCTION_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
    re.MULTILINE,
)
_ARROW_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
    re.MULTILINE,
)
_CLASS_RE = re.compile(r"^\s*(?:export\s+)?class\s+(\w+)", re.MULTILINE)
_METHOD_RE = re.compile(r"^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{", re.MULTILINE)


def _line_number(source: str, index: int) -> int:
    return source.count("\n", 0, index) + 1


def _extract_imports(source: str, repo_roots: FrozenSet[str]) -> List[ImportEntry]:
    entries: List[ImportEntry] = []
    for match in _IMPORT_RE.finditer(source):
        default_name = match.group(1)
        named_block = match.group(2)
        namespace = match.group(3)
        module = (match.group(4) or "").strip()
        names: List[str] = []
        if default_name:
            names.append(default_name)
        if namespace:
            names.append(f"*{namespace}")
        if named_block:
            for part in named_block.split(","):
                token = part.strip().split(" as ")[0].strip()
                if token:
                    names.append(token)
        if not module and not names:
            continue
        line = _line_number(source, match.start())
        entries.append(
            ImportEntry(
                module=module or "(side-effect)",
                names=sorted(set(names)),
                line=line,
                kind=classify_import(module, repo_roots=repo_roots),
            )
        )

    for match in _REQUIRE_RE.finditer(source):
        module = match.group(1).strip()
        entries.append(
            ImportEntry(
                module=module,
                names=["default"],
                line=_line_number(source, match.start()),
                kind=classify_import(module, repo_roots=repo_roots),
            )
        )

    entries.sort(key=lambda row: (row.line, row.module))
    return entries


def parse_js_ts(
    source: str,
    *,
    repo_roots: FrozenSet[str],
) -> Tuple[List[FunctionSymbol], List[ClassSymbol], List[ImportEntry]]:
    functions: List[FunctionSymbol] = []
    for pattern in (_FUNCTION_RE, _ARROW_RE):
        for match in pattern.finditer(source):
            functions.append(
                FunctionSymbol(name=match.group(1), line=_line_number(source, match.start()))
            )

    classes: List[ClassSymbol] = []
    for class_match in _CLASS_RE.finditer(source):
        class_line = _line_number(source, class_match.start())
        class_name = class_match.group(1)
        block_start = class_match.end()
        next_class = _CLASS_RE.search(source, block_start)
        block_end = next_class.start() if next_class else len(source)
        block = source[block_start:block_end]
        methods: List[MethodSymbol] = []
        for method_match in _METHOD_RE.finditer(block):
            name = method_match.group(1)
            if name in {"if", "for", "while", "switch", "catch"}:
                continue
            methods.append(
                MethodSymbol(
                    name=name,
                    line=class_line + block[: method_match.start()].count("\n"),
                )
            )
        classes.append(ClassSymbol(name=class_name, line=class_line, methods=methods))

    imports = _extract_imports(source, repo_roots)
    functions.sort(key=lambda row: (row.line, row.name))
    classes.sort(key=lambda row: (row.line, row.name))
    return functions, classes, imports
