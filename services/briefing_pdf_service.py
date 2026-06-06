"""
Generate a founder-friendly CTO Briefing PDF from existing briefing structures.

Reuses stored briefing output and live portfolio overview — no engine changes.
Pure stdlib PDF writer (no external dependencies).
"""

from __future__ import annotations

import textwrap
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Layout (points; letter = 612 x 792)
_PAGE_W = 612
_PAGE_H = 792
_MARGIN_L = 54
_MARGIN_R = 54
_MARGIN_T = 54
_MARGIN_B = 54
_CONTENT_W = _PAGE_W - _MARGIN_L - _MARGIN_R


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ")


def _fmt_money(value: Any) -> str:
    try:
        return f"${int(value):,}"
    except (TypeError, ValueError):
        return "$0"


def _fmt_date(iso_value: Optional[str]) -> str:
    if not iso_value:
        return datetime.utcnow().strftime("%B %d, %Y")
    try:
        dt = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except (TypeError, ValueError):
        return _safe_text(iso_value)


def _collect_attention_items(
    portfolio: Dict[str, Any],
    briefing: Dict[str, Any],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    ac = portfolio.get("attention_center") or {}
    for it in ac.get("items") or []:
        items.append({
            "severity": it.get("severity", "info"),
            "message": it.get("message") or it.get("name") or "",
        })

    if not items:
        for r in (briefing.get("risk_signals") or [])[:8]:
            items.append({
                "severity": r.get("severity", "warning"),
                "message": r.get("detail") or r.get("title") or "",
            })
    return items


class _PdfWriter:
    """Minimal single-font PDF writer using built-in Helvetica."""

    def __init__(self) -> None:
        self._pages: List[List[str]] = [[]]
        self._y = _PAGE_H - _MARGIN_T

    def _ops(self) -> List[str]:
        return self._pages[-1]

    def _ensure_space(self, needed: float) -> None:
        if self._y - needed < _MARGIN_B:
            self._page_break()

    def _page_break(self) -> None:
        self._pages.append([])
        self._y = _PAGE_H - _MARGIN_T

    def _move_top(self) -> None:
        self._y = _PAGE_H - _MARGIN_T

    def text(
        self,
        content: str,
        *,
        size: int = 10,
        bold: bool = False,
        indent: float = 0,
        leading: float = 14,
    ) -> None:
        font = "/F2" if bold else "/F1"
        wrapped = textwrap.wrap(_safe_text(content), width=92) or [""]
        self._ensure_space(leading * len(wrapped))
        for line in wrapped:
            self._y -= leading
            x = _MARGIN_L + indent
            escaped = (
                line.replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            ops = self._ops()
            ops.append("BT")
            ops.append(f"{font} {size} Tf")
            ops.append(f"1 0 0 1 {x:.2f} {self._y:.2f} Tm")
            ops.append(f"({escaped}) Tj")
            ops.append("ET")
        self._y -= 4

    def section(self, title: str) -> None:
        self._ensure_space(28)
        self._y -= 6
        self.text(title, size=12, bold=True, leading=16)
        y_line = self._y + 6
        self._ops().append(f"{_MARGIN_L:.2f} {y_line:.2f} m {_PAGE_W - _MARGIN_R:.2f} {y_line:.2f} l S")
        self._y -= 6

    def header_band(self, title: str, subtitle: str) -> None:
        self._move_top()
        band_h = 56
        self._ops().append("0.12 0.23 0.37 rg")
        self._ops().append(f"0 {_PAGE_H - band_h:.2f} {_PAGE_W:.2f} {band_h:.2f} re f")
        self._ops().append("1 1 1 rg")
        self.text(title, size=18, bold=True, leading=22)
        self.text(subtitle, size=11, leading=15)
        self._ops().append("0 0 0 rg")
        self._y = _PAGE_H - band_h - 16

    def health_box(self, score: Any, band: str) -> None:
        self._ensure_space(52)
        box_y = self._y - 40
        self._ops().append("0.94 0.97 1 rg")
        self._ops().append("0.15 0.39 0.92 RG")
        self._ops().append(
            f"{_MARGIN_L:.2f} {box_y:.2f} {_CONTENT_W:.2f} 40 re B"
        )
        self._ops().append("0 0 0 rg")
        self._y = box_y + 28
        self.text(f"Health Score: {score if score is not None else '--'}/100  ({band})", size=12, bold=True, leading=16)
        self._y = box_y - 8

    def build(self) -> bytes:
        objects: List[bytes] = []

        def add_obj(body) -> int:
            if isinstance(body, bytes):
                objects.append(body)
            else:
                objects.append(body.encode("latin-1", errors="replace"))
            return len(objects)

        font1 = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        font2 = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

        page_refs: List[str] = []
        pages_obj_idx = 2 + len(self._pages) * 2 + 1

        for page_ops in self._pages:
            stream = "\n".join(page_ops).encode("latin-1", errors="replace")
            content_body = (
                f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
                + stream
                + b"\nendstream"
            )
            content_idx = add_obj(content_body)
            page_idx = add_obj(
                f"<< /Type /Page /Parent {pages_obj_idx} 0 R "
                f"/MediaBox [0 0 {_PAGE_W} {_PAGE_H}] "
                f"/Contents {content_idx} 0 R "
                f"/Resources << /Font << /F1 {font1} 0 R /F2 {font2} 0 R >> >> >>"
            )
            page_refs.append(f"{page_idx} 0 R")

        kids = " ".join(page_refs)
        pages_idx = add_obj(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_refs)} >>")
        assert pages_idx == pages_obj_idx
        catalog = add_obj(f"<< /Type /Catalog /Pages {pages_idx} 0 R >>")

        pdf = b"%PDF-1.4\n"
        offsets = [0]
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

        xref_pos = len(pdf)
        pdf += f"xref\n0 {len(objects) + 1}\n".encode()
        pdf += b"0000000000 65535 f \n"
        for off in offsets[1:]:
            pdf += f"{off:010d} 00000 n \n".encode()
        pdf += (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode()
        return pdf


def generate_briefing_pdf(
    portfolio_name: str,
    briefing: Dict[str, Any],
    portfolio: Dict[str, Any],
) -> bytes:
    """Build PDF bytes from briefing + portfolio overview dicts."""
    writer = _PdfWriter()
    writer.header_band("Daily CTO Briefing", portfolio_name)
    writer.text(f"Generated {_fmt_date(briefing.get('generated_at'))}", size=9)

    health = briefing.get("system_health_score") or portfolio.get("health_score") or {}
    score = health.get("score") if "score" in health else health.get("overall_score")
    band = (health.get("band") or "healthy").replace("_", " ").title()
    writer.health_box(score, band)

    executive = briefing.get("executive_briefing") or {}
    writer.section("Executive Summary")
    headline = executive.get("headline")
    if headline:
        writer.text(headline, size=11, bold=True)
    for bullet in executive.get("bullets") or []:
        writer.text(f"• {bullet}", indent=8)
    narrative = briefing.get("cto_narrative")
    if narrative:
        writer.text(narrative)

    writer.section("Portfolio Metrics")
    summary = portfolio.get("summary") or {}
    metrics: List[Tuple[str, str]] = [
        ("Active Assignments", f"{summary.get('active_assignments', 0)} of {summary.get('total_assignments', 0)}"),
        ("Monthly Burn", _fmt_money(summary.get("total_monthly_burn"))),
        ("Target Burn", _fmt_money(summary.get("total_target_burn"))),
        ("Total Team", str(summary.get("total_team_size", 0))),
    ]
    comps = health.get("components") or {}
    if comps.get("financial") is not None:
        metrics.append(("Financial Score", f"{comps['financial']}/100"))
    if comps.get("connector") is not None:
        metrics.append(("Connector Score", f"{comps['connector']}/100"))
    if comps.get("delivery") is not None:
        metrics.append(("Delivery Score", f"{comps['delivery']}/100"))
    for label, value in metrics:
        writer.text(f"{label}: {value}", bold=False)

    writer.section("Needs Attention")
    attention_items = _collect_attention_items(portfolio, briefing)
    if not attention_items:
        writer.text("Nothing needs attention right now.")
    else:
        for item in attention_items:
            sev = (item.get("severity") or "info").upper()
            writer.text(f"[{sev}] {item.get('message', '')}", indent=4)

    writer.section("Risk Signals")
    risks = briefing.get("risk_signals") or []
    if not risks:
        writer.text("No risks flagged.")
    else:
        for risk in risks:
            detail = risk.get("detail") or risk.get("title") or ""
            sev = risk.get("severity")
            prefix = f"[{str(sev).upper()}] " if sev else ""
            writer.text(f"{prefix}{detail}", indent=4)

    writer.section("Opportunities")
    opps = briefing.get("opportunity_signals") or []
    if not opps:
        writer.text("None identified.")
    else:
        for opp in opps:
            detail = opp.get("detail") or opp.get("title") or ""
            writer.text(f"• {detail}", indent=4)

    return writer.build()
