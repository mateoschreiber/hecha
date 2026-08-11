from apps.api.app.main import app


def test_public_contract_contains_dashboard_and_freshness() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/dashboard/summary" in paths
    assert "/api/v1/meta/freshness" in paths
    assert "/api/v1/search" in paths
