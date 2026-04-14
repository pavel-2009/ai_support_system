"""Minimal tests for main.py"""
import pytest


class TestMainApp:
    """Basic tests for FastAPI app."""

    def test_app_is_created(self):
        """Test that FastAPI application instance is created."""
        from main import app
        assert app is not None
        assert hasattr(app, "openapi")

    def test_app_has_routers(self):
        """Test that routers are included."""
        from main import app
        routes = [route.path for route in app.routes]
        assert len(routes) > 0

    def test_health_check_endpoint(self, client):
        """Test health check endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_app_title_set(self):
        """Test app title is configured."""
        from main import app
        from app.core.config import settings
        assert app.title == settings.APP_NAME
