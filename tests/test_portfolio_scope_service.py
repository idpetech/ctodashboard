"""Unit tests for portfolio scope service (Act 1)."""

from services.portfolio_scope_service import (
    ASSIGNMENT_BRIEFINGS_KEY,
    DEFAULT_PORTFOLIO_ID,
    PORTFOLIO_BRIEFINGS_KEY,
    create_portfolio,
    delete_portfolio,
    ensure_default_portfolio,
    filter_assignments_by_portfolio,
    get_scoped_briefing,
    list_portfolios,
    merge_imported_portfolios,
    store_scoped_briefing_settings,
)


def test_ensure_default_portfolio_creates_main_bucket():
    settings = ensure_default_portfolio({})
    portfolios = list_portfolios(settings)
    assert len(portfolios) == 1
    assert portfolios[0]["id"] == DEFAULT_PORTFOLIO_ID
    assert portfolios[0]["name"] == "Main"


def test_create_and_delete_portfolio():
    settings, entry, err = create_portfolio({}, "Acme Corp", description="Client A")
    assert err is None
    assert entry["name"] == "Acme Corp"
    assert entry["id"] != DEFAULT_PORTFOLIO_ID

    settings, err = delete_portfolio(settings, entry["id"])
    assert err is None
    assert len(list_portfolios(settings)) == 1


def test_cannot_delete_default_portfolio():
    settings = ensure_default_portfolio({})
    settings, err = delete_portfolio(settings, DEFAULT_PORTFOLIO_ID)
    assert err is not None


def test_filter_assignments_by_portfolio():
    assignments = [
        {"id": "a1", "portfolio_id": "default"},
        {"id": "a2", "portfolio_id": "pf_acme"},
        {"id": "a3"},
    ]
    scoped = filter_assignments_by_portfolio(assignments, "pf_acme")
    assert [a["id"] for a in scoped] == ["a2"]

    default_scoped = filter_assignments_by_portfolio(assignments, DEFAULT_PORTFOLIO_ID)
    assert sorted(a["id"] for a in default_scoped) == ["a1", "a3"]


def test_scoped_briefing_storage_keys():
    settings = store_scoped_briefing_settings(
        {},
        scope="portfolio",
        scope_id="pf_acme",
        briefing={"generated_at": "2026-06-05T12:00:00", "headline": "ok"},
        engine="attention",
    )
    assert get_scoped_briefing(settings, scope="portfolio", scope_id="pf_acme")["headline"] == "ok"
    assert PORTFOLIO_BRIEFINGS_KEY in settings

    settings = store_scoped_briefing_settings(
        settings,
        scope="assignment",
        scope_id="proj-1",
        briefing={"generated_at": "2026-06-05T12:05:00", "headline": "assignment"},
        engine="attention",
    )
    assert (
        get_scoped_briefing(settings, scope="assignment", scope_id="proj-1")["headline"]
        == "assignment"
    )
    assert ASSIGNMENT_BRIEFINGS_KEY in settings


def test_merge_imported_portfolios_preserves_default():
    settings = merge_imported_portfolios(
        {},
        [
            {"id": "default", "name": "Primary"},
            {"id": "pf_client", "name": "Client B", "sort_order": 2},
        ],
    )
    portfolios = {p["id"]: p for p in list_portfolios(settings)}
    assert portfolios["default"]["name"] == "Primary"
    assert portfolios["pf_client"]["name"] == "Client B"
