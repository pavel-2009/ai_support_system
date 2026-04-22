"""Контрактные тесты API и базовые метрики Prometheus."""

from app.models.user import UserRole


class TestOpenAPIContracts:
    def test_conversation_routes_have_contracts(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        paths = schema["paths"]

        assert "/conversations/" in paths
        assert "post" in paths["/conversations/"]
        assert paths["/conversations/"]["post"]["responses"]["201"]

        assert "/conversations/{conversation_id}" in paths
        assert "get" in paths["/conversations/{conversation_id}"]


class TestPrometheusMetrics:
    def test_metrics_endpoint_exposed(self, client):
        client.get("/health")
        response = client.get("/metrics")

        assert response.status_code == 200
        assert "http_requests_total" in response.text or "Prometheus client unavailable" in response.text


class TestOperatorReplyContract:
    def test_operator_cannot_reply_to_unassigned_dialog(self, client, create_test_user):
        create_test_user(email="user_contract@example.com", password="TestPass123!", nickname="user_contract")
        create_test_user(
            email="operator_contract@example.com",
            password="TestPass123!",
            nickname="operator_contract",
            role=UserRole.OPERATOR,
        )

        user_login = client.post(
            "/api/auth/login",
            json={"email": "user_contract@example.com", "password": "TestPass123!"},
        )
        user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}
        created = client.post(
            "/api/conversations/",
            headers=user_headers,
            json={"priority": "high", "channel": "api"},
        )
        conversation_id = created.json()["id"]

        operator_login = client.post(
            "/api/auth/login",
            json={"email": "operator_contract@example.com", "password": "TestPass123!"},
        )
        operator_headers = {"Authorization": f"Bearer {operator_login.json()['access_token']}"}

        reply_response = client.post(
            f"/api/operator/reply/{conversation_id}",
            headers=operator_headers,
            json={"message": "Попытка ответа без назначения"},
        )
        assert reply_response.status_code == 404
