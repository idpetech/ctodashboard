"""Python AST-based symbol and import extraction."""

from __future__ import annotations

import ast
from typing import FrozenSet, List, Tuple

from services.repo_intelligence.ast_parsers.import_classifier import classify_import
from services.repo_intelligence.models.code_index import (
    ClassSymbol,
    FunctionSymbol,
    ImportEntry,
    MethodSymbol,
)


def parse_python(
    source: str,
    *,
    repo_roots: FrozenSet[str],
) -> Tuple[List[FunctionSymbol], List[ClassSymbol], List[ImportEntry]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [], [], []

    functions: List[FunctionSymbol] = []
    classes: List[ClassSymbol] = []
    imports: List[ImportEntry] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(FunctionSymbol(name=node.name, line=node.lineno))
        elif isinstance(node, ast.ClassDef):
            methods: List[MethodSymbol] = []
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(MethodSymbol(name=child.name, line=child.lineno))
            classes.append(ClassSymbol(name=node.name, line=node.lineno, methods=methods))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                names = [alias.asname or alias.name.split(".")[-1]]
                imports.append(
                    ImportEntry(
                        module=module,
                        names=names,
                        line=node.lineno,
                        kind=classify_import(module, repo_roots=repo_roots),
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level and node.level > 0:
                module = f"{'.' * node.level}{module}"
            names = [alias.name for alias in node.names]
            imports.append(
                ImportEntry(
                    module=module,
                    names=names,
                    line=node.lineno,
                    kind=classify_import(module, repo_roots=repo_roots),
                )
            )

    functions.sort(key=lambda row: (row.line, row.name))
    classes.sort(key=lambda row: (row.line, row.name))
    imports.sort(key=lambda row: (row.line, row.module))
    return functions, classes, imports
