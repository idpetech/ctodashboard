"""Unit tests for Analysis Layer v1.1 calibration."""

from __future__ import annotations

from analysis.calibration import calibrate_findings, is_infra_coupling_hotspot
from analysis.models import Finding
from analysis.scorer import RiskScorer


def _finding(finding_id: str, *, severity: str = "high", evidence: str = "") -> Finding:
    return Finding(
        id=finding_id,
        category="architecture",
        severity=severity,  # type: ignore[arg-type]
        title="test",
        evidence=evidence or "evidence",
        confidence=0.9,
        impact="impact",
        recommendation="recommendation",
    )


def test_infra_coupling_allowlist():
    assert is_infra_coupling_hotspot("services/config/logging_config.py")
    assert not is_infra_coupling_hotspot("services/security/credential_service.py")


def test_calibrate_suppresses_infra_coupling():
    findings = [
        _finding(
            "architecture.coupling_hotspot.logging_config",
            evidence="Internal module target 'services/config/logging_config.py' is imported by 23 indexed files (threshold 5).",
        ),
        _finding(
            "architecture.coupling_hotspot.credentials",
            evidence="Internal module target 'services/security/credential_service.py' is imported by 20 indexed files (threshold 5).",
        ),
    ]
    calibrated = calibrate_findings(findings, strict=False)
    assert len(calibrated) == 1
    assert calibrated[0].id.endswith("credentials")


def test_scorer_calibrated_mode_avoids_easy_saturation():
    findings = tuple(
        Finding(
            id=f"architecture.coupling_hotspot.hub{i}",
            category="architecture",
            severity="high",
            title="High coupling hotspot detected",
            evidence=f"Internal module target 'services/hub{i}.py' is imported by 10 indexed files (threshold 5).",
            confidence=0.9,
            impact="impact",
            recommendation="recommendation",
        )
        for i in range(10)
    )
    strict_score, _ = RiskScorer().score(findings, strict=True)
    calibrated_score, _ = RiskScorer().score(findings, strict=False)
    assert strict_score == 100
    assert calibrated_score < strict_score


def test_pattern_severity_downgrades_coupling_in_modular_monolith():
    from analysis.calibration import apply_pattern_severity
    from analysis.models import Finding

    finding = Finding(
        id="architecture.coupling_hotspot.credentials",
        category="architecture",
        severity="high",
        title="High coupling hotspot detected",
        evidence="Internal module target 'services/security/credential_service.py' is imported by 20 indexed files (threshold 5).",
        confidence=0.9,
        impact="impact",
        recommendation="recommendation",
    )
    adjusted = apply_pattern_severity([finding], "modular_monolith", strict=False)
    assert adjusted[0].severity == "medium"
