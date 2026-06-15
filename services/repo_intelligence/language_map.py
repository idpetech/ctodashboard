"""Deterministic extension → language labels (no LLM, no GitHub Linguist)."""

from __future__ import annotations

from typing import Optional

# Sorted keys for stable iteration in downstream aggregates.
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".go": "Go",
    ".h": "C Header",
    ".hpp": "C++ Header",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".json": "JSON",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".md": "Markdown",
    ".mjs": "JavaScript",
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".scss": "SCSS",
    ".sh": "Shell",
    ".sql": "SQL",
    ".svg": "SVG",
    ".swift": "Swift",
    ".toml": "TOML",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".txt": "Text",
    ".xml": "XML",
    ".yaml": "YAML",
    ".yml": "YAML",
}

BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".7z",
        ".avi",
        ".bin",
        ".bmp",
        ".class",
        ".dll",
        ".dylib",
        ".eot",
        ".exe",
        ".gif",
        ".gz",
        ".ico",
        ".jar",
        ".jpeg",
        ".jpg",
        ".lockb",
        ".mp3",
        ".mp4",
        ".otf",
        ".pdf",
        ".png",
        ".so",
        ".tar",
        ".ttf",
        ".wasm",
        ".webp",
        ".woff",
        ".woff2",
        ".zip",
    }
)


def extension_from_path(path: str) -> str:
    if "/" in path:
        name = path.rsplit("/", 1)[-1]
    else:
        name = path
    if name.startswith(".") and name.count(".") == 1:
        return name.lower()
    dot = name.rfind(".")
    if dot <= 0:
        return ""
    return name[dot:].lower()


def language_for_extension(ext: str) -> Optional[str]:
    if not ext:
        return None
    return EXTENSION_LANGUAGE_MAP.get(ext.lower())


def is_binary_extension(ext: str) -> bool:
    return ext.lower() in BINARY_EXTENSIONS
