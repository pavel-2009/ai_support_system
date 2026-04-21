"""Задачи для фоновой работы с LLM."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.celery.celery_app import celery_app
from app.services.llm_service import LLMService
from app.services.message_service import MessageService
from app.services.conversation_service import ConversationService
from app.models.conversation import Status
from app.schemas.llm import LLMResponse


@celery_app.task(bind=True, max_retries=settings.LLM_RETRY_ATTEMPTS, default_retry_delay=5)
def process_llm_task(
    self,
    conversation_id: int,
    llm_service: LLMService,
    session: AsyncSession,
    message_service: MessageService,
    conversation_service: ConversationService
    ) -> str:
    """Обработка задачи LLM с повторными попытками при неудаче."""
    
    try:
        response: LLMResponse = llm_service.generate_response(conversation_id, session)
        
        confidence = response.confidence if hasattr(response, 'confidence') else 0
        
        # Проверяем уровень доверия и сохраняем ответ в базу данных
        if confidence >= settings.LLM_AI_CONFIDENCE_THRESHOLD:
        
            # Сохранение ответа в базу данных
            message_service.create_message(
                conversation_id=conversation_id,
                sender_type="ai",
                sender_id=None,
                content=response.answer,
                is_auto_reply=True,
                confidence=confidence,
                needs_review=False,
            )
            
        else:
            # Эскадируем диалог для ручной обработки, если доверие низкое
            conversation_service.update_conversation_status(
                conversation_id=conversation_id,
                new_status=Status.ESCALATED,
            )
            
    except Exception as exc:
        raise self.retry(exc=exc)
