"""Глобальная инициализация сервисов."""

from app.services.user_service import UserService
from app.services.conversation_service import ConversationService


__services = {}


async def init_services(session):
    """Инициализация сервисов."""
    global __services
    
    # Пока единый try-except для всех сервисов, можно потом разделить по отдельности при добавлении новых сервисов
    try:
        # Инициализация сервисов с передачей сессии
        __services['user_service'] = UserService(session)
        __services['conversation_service'] = ConversationService(session)
        
    except Exception as e:
        print(f"Ошибка при инициализации сервисов: {e}")  
        

# === ГЕТТЕРЫ ДЛЯ ЗАВИСИМОСТЕЙ ===
async def get_conversation_service() -> ConversationService:
    """Получить экземпляр ConversationService."""
    return __services.get('conversation_service')


async def get_user_service() -> UserService:
    """Получить экземпляр UserService."""
    return __services.get('user_service')  