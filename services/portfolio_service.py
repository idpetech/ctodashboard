"""
Portfolio Dashboard MVP — on-demand portfolio intelligence.

This module is intentionally pure computation. It takes the list of assignment
dicts that already come from the Postgres store (no new tables, no extra I/O)
and derives six read-only views for a Fractional CTO:

    1. Portfolio Summary
    2. Portfolio Health Score
    3. Connector Health
    4. Attention Center
    5. Assignment Ranking
    6. Budget Variance

Hard constraints honored here:
    - Uses only existing data (status, team_size, monthly_burn_rate,
      target_monthly_burn, metrics_config, credentials).
    - No persistence, no snapshots, no history/trend, no schedulers,
      no AI recommendations. Everything is computed from the current rows
      each time it is requested.

All values are deterministic functions of the current input.
"""

from typing import Any, Dict, List, Optional

# Connectors we know how to reason about. "enabled" is read from each
# assignment's metrics_config; "configured" is read from the per-assignment
# credentials map that the store already returns.
CONNECTORS = ["github", "jira", "aws", "openai", "railway"]

# Variance thresholds (percent over target) used for severity classification.
VARIANCE_WARN_PCT = 10.0
VARIANCE_CRITICAL_PCT = 20.0

# Health-score band thresholds (0-100).
HEALTHY_MIN = 80
AT_RISK_MIN = 60

_SEVERITY_RANK = {"critical": 0, "warning": 1, "info": 2}


def _to_number(value: Any) -> Optional[float]:
    """Coerce a stored value to a number, tolerating None/strings/empties."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_active(assignment: Dict[str, Any]) -> bool:
    return (assignment.get("status") or "active") == "active"


def _enabled_connectors(assignment: Dict[str, Any]) -> List[str]:
    cfg = assignment.get("metrics_config") or {}
    enabled = []
    for name in CONNECTORS:
        section = cfg.get(name) or {}
        if isinstance(section, dict) and section.get("enabled"):
            enabled.append(name)
    return enabled


def _configured_connectors(assignment: Dict[str, Any]) -> Dict[str, bool]:
    creds = assignment.get("credentials") or {}
    if not isinstance(creds, dict):
        return {}
    return {name: bool(creds.get(name)) for name in CONNECTORS}


def _band(score: int) -> str:
    if score >= HEALTHY_MIN:
        return "healthy"
    if score >= AT_RISK_MIN:
        return "at_risk"
    return "critical"


# --------------------------------------------------------------------------- #
# 1. Portfolio Summary
# --------------------------------------------------------------------------- #
def portfolio_summary(assignments: List[Dict[str, Any]]) -> Dict[str, Any]:
    status_counts: Dict[str, int] = {}
    for a in assignments:
        status = a.get("status") or "active"
        status_counts[status] = status_counts.get(status, 0) + 1

    active = [a for a in assignments if _is_active(a)]
    total_burn = sum(int(_to_number(a.get("monthly_burn_rate")) or 0) for a in active)
    total_target = sum(
        int(_to_number(a.get("target_monthly_burn")) or 0)
        for a in active
        if _to_number(a.get("target_monthly_burn")) is not None
    )
    total_team = sum(int(_to_number(a.get("team_size")) or 0) for a in active)
    with_target = sum(
        1 for a in active if _to_number(a.get("target_monthly_burn")) is not None
    )

    return {
        "total_assignments": len(assignments),
        "active_assignments": len(active),
        "status_counts": status_counts,
        "total_team_size": total_team,
        "total_monthly_burn": total_burn,
        "total_target_burn": total_target,
        "assignments_with_target": with_target,
        "assignments_missing_target": len(active) - with_target,
    }


# --------------------------------------------------------------------------- #
# 6. Budget Variance (computed early; feeds health + attention + ranking)
# --------------------------------------------------------------------------- #
def budget_variance(assignments: List[Dict[str, Any]]) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    missing_target: List[Dict[str, Any]] = []
    portfolio_actual = 0
    portfolio_target = 0

    for a in assignments:
        if not _is_active(a):
            continue
        actual = int(_to_number(a.get("monthly_burn_rate")) or 0)
        target_raw = _to_number(a.get("target_monthly_burn"))
        name = a.get("name") or a.get("id")

        if target_raw is None:
            missing_target.append({"assignment_id": a.get("id"), "name": name})
            continue

        target = int(target_raw)
        variance = actual - target
        variance_pct = round((variance / target) * 100, 1) if target > 0 else 0.0
        if variance_pct > VARIANCE_CRITICAL_PCT:
            status = "critical"
        elif variance_pct > VARIANCE_WARN_PCT:
            status = "over"
        elif variance < 0:
            status = "under"
        else:
            status = "on_track"

        portfolio_actual += actual
        portfolio_target += target
        items.append(
            {
                "assignment_id": a.get("id"),
                "name": name,
                "actual_monthly_burn": actual,
                "target_monthly_burn": target,
                "variance": variance,
                "variance_pct": variance_pct,
                "status": status,
            }
        )

    items.sort(key=lambda x: x["variance_pct"], reverse=True)
    portfolio_variance = portfolio_actual - portfolio_target
    portfolio_pct = (
        round((portfolio_variance / portfolio_target) * 100, 1)
        if portfolio_target > 0
        else None
    )

    return {
        "portfolio_actual_burn": portfolio_actual,
        "portfolio_target_burn": portfolio_target,
        "portfolio_variance": portfolio_variance,
        "portfolio_variance_pct": portfolio_pct,
        "tracked_assignments": len(items),
        "assignments": items,
        "missing_target": missing_target,
    }


# --------------------------------------------------------------------------- #
# 3. Connector Health
# --------------------------------------------------------------------------- #
def connector_health(assignments: List[Dict[str, Any]]) -> Dict[str, Any]:
    active = [a for a in assignments if _is_active(a)]
    connectors: List[Dict[str, Any]] = []
    total_enabled = 0
    total_ready = 0

    for name in CONNECTORS:
        enabled = 0
        ready = 0
        needs_credentials = 0
        for a in active:
            cfg = (a.get("metrics_config") or {}).get(name) or {}
            if isinstance(cfg, dict) and cfg.get("enabled"):
                enabled += 1
                if _configured_connectors(a).get(name):
                    ready += 1
                else:
                    needs_credentials += 1

        if enabled == 0:
            status = "disabled"
        elif needs_credentials == 0:
            status = "ready"
        elif ready > 0:
            status = "degraded"
        else:
            status = "needs_credentials"

        total_enabled += enabled
        total_ready += ready
        connectors.append(
            {
                "connector": name,
                "enabled_count": enabled,
                "ready_count": ready,
                "needs_credentials_count": needs_credentials,
                "status": status,
            }
        )

    readiness_pct = (
        round((total_ready / total_enabled) * 100, 1) if total_enabled > 0 else None
    )
    return {
        "connectors": connectors,
        "total_enabled": total_enabled,
        "total_ready": total_ready,
        "readiness_pct": readiness_pct,
    }


# --------------------------------------------------------------------------- #
# 2. Portfolio Health Score
# --------------------------------------------------------------------------- #
def portfolio_health_score(
    budget: Dict[str, Any],
    connectors: Dict[str, Any],
    attention: Dict[str, Any],
    active_count: int,
) -> Dict[str, Any]:
    """Deterministic 0-100 score from the current snapshot only."""
    components: Dict[str, Optional[int]] = {}

    # Financial: penalize portfolio budget overrun (only if any targets exist).
    pct = budget.get("portfolio_variance_pct")
    if pct is None:
        components["financial"] = None
    else:
        score = 100
        if pct > VARIANCE_CRITICAL_PCT:
            score -= 40
        elif pct > VARIANCE_WARN_PCT:
            score -= 20
        elif pct > 5:
            score -= 10
        components["financial"] = max(0, score)

    # Connector readiness.
    readiness = connectors.get("readiness_pct")
    components["connector"] = int(round(readiness)) if readiness is not None else None

    # Delivery: share of active assignments without budget/target attention flags.
    # Connector credential gaps are already reflected in the connector component —
    # do not double-penalize them here.
    _DELIVERY_ATTENTION_TYPES = frozenset({"budget_overrun", "missing_target"})
    if active_count > 0:
        flagged = len(
            {
                item["assignment_id"]
                for item in attention.get("items", [])
                if item.get("assignment_id")
                and item.get("type") in _DELIVERY_ATTENTION_TYPES
            }
        )
        delivery = max(0, round(((active_count - flagged) / active_count) * 100))
        components["delivery"] = int(delivery)
    else:
        components["delivery"] = None

    available = [v for v in components.values() if v is not None]
    overall = int(round(sum(available) / len(available))) if available else 100

    return {
        "overall_score": overall,
        "band": _band(overall),
        "components": components,
    }


# --------------------------------------------------------------------------- #
# 4. Attention Center
# --------------------------------------------------------------------------- #
def attention_center(
    assignments: List[Dict[str, Any]], budget: Dict[str, Any]
) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []

    # Budget overruns from the budget-variance view.
    for row in budget.get("assignments", []):
        if row["status"] == "critical":
            severity = "critical"
        elif row["status"] == "over":
            severity = "warning"
        else:
            continue
        items.append(
            {
                "assignment_id": row["assignment_id"],
                "name": row["name"],
                "type": "budget_overrun",
                "severity": severity,
                "message": (
                    f"{row['name']} is {row['variance_pct']}% over target "
                    f"(${row['actual_monthly_burn']:,} vs ${row['target_monthly_burn']:,}/mo)"
                ),
            }
        )

    # Connectors enabled but missing credentials.
    for a in assignments:
        if not _is_active(a):
            continue
        configured = _configured_connectors(a)
        for name in _enabled_connectors(a):
            if not configured.get(name):
                items.append(
                    {
                        "assignment_id": a.get("id"),
                        "name": a.get("name") or a.get("id"),
                        "type": "connector_needs_credentials",
                        "severity": "warning",
                        "message": (
                            f"{a.get('name') or a.get('id')}: {name} is enabled "
                            f"but has no credentials configured"
                        ),
                    }
                )

    # Active assignments with no budget target set.
    for row in budget.get("missing_target", []):
        items.append(
            {
                "assignment_id": row["assignment_id"],
                "name": row["name"],
                "type": "missing_target",
                "severity": "info",
                "message": (
                    f"{row['name']} has no target monthly burn set; "
                    f"budget variance cannot be tracked"
                ),
            }
        )

    items.sort(key=lambda x: _SEVERITY_RANK.get(x["severity"], 99))
    counts = {"critical": 0, "warning": 0, "info": 0}
    for item in items:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1

    return {"total": len(items), "counts": counts, "items": items}


# --------------------------------------------------------------------------- #
# 5. Assignment Ranking
# --------------------------------------------------------------------------- #
def assignment_ranking(assignments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank active assignments by current attention need (higher = needs CTO)."""
    ranked: List[Dict[str, Any]] = []

    for a in assignments:
        if not _is_active(a):
            continue
        actual = int(_to_number(a.get("monthly_burn_rate")) or 0)
        target_raw = _to_number(a.get("target_monthly_burn"))
        enabled = _enabled_connectors(a)
        configured = _configured_connectors(a)
        ready = [c for c in enabled if configured.get(c)]
        misconfigured = len(enabled) - len(ready)

        variance_pct: Optional[float] = None
        risk = 0.0
        if target_raw is not None and target_raw > 0:
            variance_pct = round(((actual - target_raw) / target_raw) * 100, 1)
            if variance_pct > 0:
                risk += variance_pct
        else:
            # No target set is a small, fixed attention cost (cannot be tracked).
            risk += 5
        risk += misconfigured * 15

        if risk >= VARIANCE_CRITICAL_PCT:
            attention_level = "critical"
        elif risk >= VARIANCE_WARN_PCT:
            attention_level = "at_risk"
        else:
            attention_level = "healthy"

        ranked.append(
            {
                "assignment_id": a.get("id"),
                "name": a.get("name") or a.get("id"),
                "status": a.get("status") or "active",
                "team_size": int(_to_number(a.get("team_size")) or 0),
                "monthly_burn": actual,
                "target_monthly_burn": int(target_raw) if target_raw is not None else None,
                "variance_pct": variance_pct,
                "enabled_connectors": len(enabled),
                "ready_connectors": len(ready),
                "risk_score": round(risk, 1),
                "attention_level": attention_level,
            }
        )

    ranked.sort(key=lambda x: x["risk_score"], reverse=True)
    return ranked


# --------------------------------------------------------------------------- #
# Aggregator
# --------------------------------------------------------------------------- #
def build_portfolio_overview(assignments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compose all six sections from the current assignment list."""
    assignments = assignments or []
    active_count = sum(1 for a in assignments if _is_active(a))

    summary = portfolio_summary(assignments)
    budget = budget_variance(assignments)
    connectors = connector_health(assignments)
    attention = attention_center(assignments, budget)
    health = portfolio_health_score(budget, connectors, attention, active_count)
    ranking = assignment_ranking(assignments)

    return {
        "summary": summary,
        "health_score": health,
        "connector_health": connectors,
        "attention_center": attention,
        "assignment_ranking": ranking,
        "budget_variance": budget,
    }
