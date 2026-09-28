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
        assert "/conversations/{conversation_id}/close" in routes

    def test_health_check_endpoint(self, client, monkeypatch):
        class MockLLMClient:
            class Models:
                async def list(self):
                    return []

            def __init__(self, **_kwargs):
                self.models = self.Models()

            async def close(self):
                pass

        monkeypatch.setattr("main.AsyncOpenAI", MockLLMClient)
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] in {"healthy", "degraded"}
        assert "checks" in body
        assert "database" in body["checks"]
        assert "redis" in body["checks"]
        assert "celery" in body["checks"]
        assert body["checks"]["llm_api"] == "ok"
        assert body["checks"]["disk_space"] == "ok"
        assert body["checks"]["open_conversations"] == "ok"
        assert body["resources"]["free_disk_space_bytes"] >= 0
        assert body["resources"]["free_disk_space_gb"] >= 0
        assert isinstance(body["resources"]["open_conversations"], int)

    def test_app_title_set(self):
        from app.core.config import settings
        from main import app

        assert app.title == settings.APP_NAME
