#!/usr/bin/env python3
"""Re-extract dashboard inline JS from rollback tag into static/js/dashboard modules."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "js" / "dashboard"
ROLLBACK = "rollback/pre-dashboard-js-split-2026-06-10:templates/dashboard.html"

# (filename, start_marker inclusive, end_marker exclusive)
MODULES: list[tuple[str, str | None, str | None]] = [
    ("00-state.js", None, "function formatTrialDate"),
    ("01-auth-billing.js", "function formatTrialDate", "// ===== Product analytics"),
    ("02-analytics.js", "// ===== Product analytics", "async function retryWithExponentialBackoff"),
    (
        "03-workspace-core.js",
        "async function retryWithExponentialBackoff",
        "// ===== Overview executive panels",
    ),
    (
        "04-overview-briefing.js",
        "// ===== Overview executive panels",
        "function showTab(tabId)",
    ),
    ("05-chatbot.js", "function showTab(tabId)", "async function editAssignment"),
    ("06-profile-loading.js", "async function editAssignment", "function showSearchOverlay"),
    ("07-search-import-ui.js", "function showSearchOverlay", "async function showAssignmentHistory"),
    ("08-history-backup.js", "async function showAssignmentHistory", "function BackgroundMonitor"),
    ("09-cache-monitor.js", "function BackgroundMonitor", "// Initialize authentication when page loads"),
    ("10-bootstrap.js", "// Initialize authentication when page loads", None),
]


def git_show(ref_path: str) -> str:
    return subprocess.check_output(["git", "show", ref_path], cwd=ROOT, text=True)


def extract_first_script(html: str) -> list[str]:
    lines = html.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "<script>") + 1
    end = next(i for i, line in enumerate(lines) if line.strip() == "</script>")
    return lines[start:end]


def extract_second_script(html: str) -> list[str]:
    lines = html.splitlines()
    hits = [i for i, line in enumerate(lines) if line.strip() == "<script>"]
    if len(hits) < 2:
        raise RuntimeError("Expected two inline script blocks in dashboard.html")
    start = hits[1] + 1
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == "</script>")
    return lines[start:end]


def dedent(lines: list[str]) -> str:
    out: list[str] = []
    for line in lines:
        if line.startswith("            "):
            out.append(line[12:])
        elif line.strip() == "":
            out.append("")
        else:
            out.append(line.lstrip())
    return "\n".join(out)


def slice_text(text: str, start: str | None, end: str | None) -> str:
    chunk = text if start is None else text[text.index(start) :]
    if end is not None:
        chunk = chunk[: chunk.index(end)]
    return chunk.rstrip() + "\n"


def write_module(name: str, body: str) -> None:
    path = OUT / name
    content = f"/* CTO Lens dashboard module: {name} */\n{body}"
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path.name}: {content.count(chr(10))} lines")


def main() -> None:
    html = git_show(ROLLBACK)
    main_text = dedent(extract_first_script(html))
    export_text = dedent(extract_second_script(html)).rstrip() + "\n"

    for name, start, end in MODULES:
        write_module(name, slice_text(main_text, start, end))

    write_module("11-export-import.js", export_text)


if __name__ == "__main__":
    main()
