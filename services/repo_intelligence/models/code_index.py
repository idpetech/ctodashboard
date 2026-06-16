"""Structured per-file code index models (JSON-serializable, deterministic)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class MethodSymbol:
    name: str
    line: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FunctionSymbol:
    name: str
    line: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClassSymbol:
    name: str
    line: int
    methods: List[MethodSymbol] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "line": self.line,
            "methods": [
                m.to_dict() for m in sorted(self.methods, key=lambda row: (row.line, row.name))
            ],
        }


@dataclass(frozen=True)
class ImportEntry:
    module: str
    names: List[str]
    line: int
    kind: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module,
            "names": sorted(self.names),
            "line": self.line,
            "kind": self.kind,
        }


@dataclass
class FileCodeIndex:
    file_path: str
    language: str
    symbols: Dict[str, List[Dict[str, Any]]]
    imports: List[ImportEntry]
    last_indexed: str
    git_sha: str = ""

    def to_dict(self) -> Dict[str, Any]:
        functions = sorted(
            self.symbols.get("functions") or [],
            key=lambda row: (row.get("line", 0), row.get("name", "")),
        )
        classes = sorted(
            self.symbols.get("classes") or [],
            key=lambda row: (row.get("line", 0), row.get("name", "")),
        )
        return {
            "file_path": self.file_path,
            "language": self.language,
            "symbols": {"functions": functions, "classes": classes},
            "imports": [
                entry.to_dict()
                for entry in sorted(self.imports, key=lambda row: (row.line, row.module))
            ],
            "last_indexed": self.last_indexed,
            "git_sha": self.git_sha,
        }

    @classmethod
    def empty(
        cls,
        file_path: str,
        language: str,
        *,
        last_indexed: str,
        git_sha: str = "",
    ) -> FileCodeIndex:
        return cls(
            file_path=file_path,
            language=language,
            symbols={"functions": [], "classes": []},
            imports=[],
            last_indexed=last_indexed,
            git_sha=git_sha,
        )
