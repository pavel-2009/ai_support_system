"""Minimal tests for main.py"""


class TestMainApp:
    """Basic tests for FastAPI app."""

    def test_app_is_created(self):
        from main import app

        assert app is not None
        assert hasattr(app, "openapi")

    def test_app_has_routers(self):
        from main import app

        routes = [route.path for route in app.routes]
        assert len(routes) > 0
        assert "/conversations/" in routes

    def test_health_check_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_app_title_set(self):
        from app.core.config import settings
        from main import app

        assert app.title == settings.APP_NAME
