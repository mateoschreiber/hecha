from apps.api.app.main import app


def test_health_route_is_registered() -> None:
    assert any(route.path == "/api/v1/health/live" for route in app.routes)
