from fastapi.testclient import TestClient

from app.main import app

ORIGIN = "http://localhost:5173"


def test_unhandled_error_is_a_500_the_browser_can_read():
    """A crash still carries CORS headers, so the frontend sees a 500, not "Network Error"."""

    def boom():
        raise RuntimeError("no such table: settlements")

    app.add_api_route("/_boom", boom)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/_boom", headers={"Origin": ORIGIN})
    finally:
        app.router.routes.pop()

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == ORIGIN
    detail = response.json()["detail"]
    assert "settlements" not in detail  # internals stay in the server log
