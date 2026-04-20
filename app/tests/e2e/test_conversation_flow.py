"""E2E тест для проверки корректности всего цикла диалогов (пока без ИИ)."""

import asyncio
import pytest

from app.repositories.conversation_repo import ConversationRepository
from app.models.conversation import Status

class TestConversationFlow:
    """Класс для тестирования полного цикла диалогов."""
    
    def test_full_conversation_flow(self, authenticated_client, operator_client, async_session):
        """Тестирование полного цикла диалогов."""
        
        # 1. Создание нового диалога пользователем
        response = authenticated_client.post("/conversations/", json={
            "priority": "medium",
            "channel": "api"
        })
        
        assert response.status_code == 201
        
        conversation_id = response.json()["id"]
        
        # 2. Проверяем, что в БД появился новый диалог
        response = authenticated_client.get(f"/conversations/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["id"] == conversation_id
        assert response.json()["status"] == "open"
        
        
        # 3. Добавляем сообщение от пользователя
        response = authenticated_client.post(f"/conversations/{conversation_id}/messages/", json={
            "content": "Привет, мне нужна помощь!"
        })
        assert response.status_code == 201
        
        # 4. Проверяем, что в очереди диалогов для операторов есть диалог
        response = authenticated_client.get("/operator/queue/")
        assert response.status_code == 403
        
        response = operator_client.get("/operator/queue/")
        assert response.status_code == 200
        
        # Меняем статус диалога (вообще это должно быть автоматически ИИ, но это потом)
        repo = ConversationRepository(async_session)
        asyncio.run(repo.update_conversation_status(conversation_id, Status.ESCALATED))
        
        # Заново получаем очередь после обновления статуса
        response = operator_client.get("/operator/queue/")
        assert response.status_code == 200
        assert conversation_id in [conv["id"] for conv in response.json()]
        
        # 5. Оператор назначает диалог себе
        response = operator_client.post(f"/operator/assign/{conversation_id}")
        assert response.status_code == 200
        
        # Меняем статус диалога
        asyncio.run(repo.update_conversation_status(conversation_id, Status.WAITING_FOR_OPERATOR)) # Пока заглушка
        
        # 6. Проверяем, что диалог больше не в очереди
        response = operator_client.get("/operator/queue/")
        assert response.status_code == 200
        assert conversation_id not in [conv["id"] for conv in response.json()]
        
        # 7. Проверяем, что оператор назначен на диалог
        response = operator_client.get(f"/conversations/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["operator_id"] is not None
        
        # 8. Оператор добавляет сообщение в диалог
        response = operator_client.post(f"/operator/reply/{conversation_id}/", json={
            "message": "Здравствуйте! Я оператор, чем могу помочь?"
        })
        assert response.status_code == 200
        
        # 9. Проверяем, что сообщение от оператора добавлено в диалог
        response = authenticated_client.get(f"/conversations/{conversation_id}/messages/")
        assert response.status_code == 200
        messages = response.json()
        assert any(msg["content"] == "Здравствуйте! Я оператор, чем могу помочь?" for msg in messages)
        
        # 10. Оператор возвращает управление диалогов ИИ
        response = operator_client.post(f"/operator/back_to_ai/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "open"
        
        # 11. Проверяем, что оператор больше не назначен на диалог
        response = authenticated_client.get(f"/conversations/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["operator_id"] is None
        
        # 12. Проверяем, что диалога нет а в очереди для операторов до эскалации
        response = operator_client.get("/operator/queue/")
        assert response.status_code == 200
        assert conversation_id not in [conv["id"] for conv in response.json()]
        
        # 13. Оператор закрывает диалог
        response = operator_client.post(f"/operator/close/{conversation_id}/")
        assert response.status_code == 200
        assert response.json()["detail"] == "Диалог успешно закрыт."
        