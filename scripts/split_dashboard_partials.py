#!/usr/bin/env python3
"""Split templates/dashboard.html into Jinja partials under templates/dashboard/."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "dashboard.html"
PARTIALS = ROOT / "templates" / "dashboard"

# (partial filename, start marker inclusive, end marker exclusive)
# Markers must be unique substrings in dashboard.html.
SECTIONS: list[tuple[str, str, str | None]] = [
    ("_head.html", "<!DOCTYPE html>", "<body class=\"bg-gray-100\">"),
    ("_auth_overlay.html", "<!-- Phase 4: Authentication Overlay", "<!-- Phase 5A: Profile Management Modal"),
    ("_profile_modal.html", "<!-- Phase 5A: Profile Management Modal", "<!-- Phase 5B: Assignment Edit Modal"),
    ("_assignment_edit_modal.html", "<!-- Phase 5B: Assignment Edit Modal", "<div class=\"container mx-auto px-4 py-8\">"),
    ("_header.html", "<div class=\"container mx-auto px-4 py-8\">", "<!-- Phase 5C: Search/Filtering Overlay"),
    ("_search_overlay.html", "<!-- Phase 5C: Search/Filtering Overlay", "<!-- Phase 5C: Import Dialog"),
    ("_import_dialog.html", "<!-- Phase 5C: Import Dialog", "<!-- Share Report Dialog"),
    ("_share_dialog.html", "<!-- Share Report Dialog", "<!-- Trial status banner"),
    ("_toolbar.html", "<!-- Trial status banner", "<main id=\"dashboard-content\""),
    ("_main_content.html", "<main id=\"dashboard-content\"", "<footer id=\"app-footer\""),
    ("_footer.html", "<footer id=\"app-footer\"", "<!-- Chatbot Button"),
    ("_chatbot.html", "<!-- Chatbot Button", "<script src=\"/static/js/dashboard/00-state.js\">"),
    ("_scripts.html", "<script src=\"/static/js/dashboard/00-state.js\">", "<!-- Credential Configuration Modal"),
    ("_credential_modal.html", "<!-- Credential Configuration Modal", "<!-- Create Assignment Modal"),
    ("_create_assignment_modal.html", "<!-- Create Assignment Modal", "<style>\n        .credential-form"),
    ("_credential_styles.html", "<style>\n        .credential-form", "<!-- Export Modal"),
    ("_export_modal.html", "<!-- Export Modal", "<!-- Import Modal"),
    ("_import_modal.html", "<!-- Import Modal", "</body>"),
]

SHELL = """<!DOCTYPE html>
<html lang="en">
{% include 'dashboard/_head.html' %}
<body class="bg-gray-100">
{% include 'dashboard/_auth_overlay.html' %}
{% include 'dashboard/_profile_modal.html' %}
{% include 'dashboard/_assignment_edit_modal.html' %}
{% include 'dashboard/_header.html' %}
{% include 'dashboard/_search_overlay.html' %}
{% include 'dashboard/_import_dialog.html' %}
{% include 'dashboard/_share_dialog.html' %}
{% include 'dashboard/_toolbar.html' %}
{% include 'dashboard/_main_content.html' %}
{% include 'dashboard/_footer.html' %}
{% include 'dashboard/_chatbot.html' %}
{% include 'dashboard/_scripts.html' %}
{% include 'dashboard/_credential_modal.html' %}
{% include 'dashboard/_create_assignment_modal.html' %}
{% include 'dashboard/_credential_styles.html' %}
{% include 'dashboard/_export_modal.html' %}
{% include 'dashboard/_import_modal.html' %}
</body>
</html>
"""


def slice_section(text: str, start: str, end: str | None) -> str:
    start_idx = text.index(start)
    chunk = text[start_idx:]
    if end is not None:
        end_idx = chunk.index(end)
        chunk = chunk[:end_idx]
    return chunk.rstrip() + "\n"


def main() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    PARTIALS.mkdir(parents=True, exist_ok=True)

    for name, start, end in SECTIONS:
        body = slice_section(text, start, end)
        if name == "_head.html":
            # Shell opens <html>; partial is head only.
            body = body.replace("<!DOCTYPE html>\n", "", 1)
            body = body.replace('<html lang="en">\n', "", 1)
        if name == "_header.html":
            # Keep container wrapper in shell flow via partial including opening tag.
            pass
        path = PARTIALS / name
        path.write_text(body, encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)} ({body.count(chr(10))} lines)")

    TEMPLATE.write_text(SHELL, encoding="utf-8")
    print(f"Wrote {TEMPLATE.relative_to(ROOT)} ({SHELL.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
