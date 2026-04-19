"""Задачи для фоновой работы с LLM."""

from app.core.config import settings
from app.celery.celery_app import celery_app
from app.services.llm_service import LLMService


@celery_app.task(bind=True, max_retries=settings.LLM_RETRY_ATTEMPTS, default_retry_delay=5)
def process_llm_task(
    self,
    conversation_id: int,
    llm_service: LLMService,
    session
    ) -> str:
    """Обработка задачи LLM с повторными попытками при неудаче."""
    
    try:
        response = llm_service.generate_response(conversation_id, session)
        return response
    except Exception as exc:
        raise self.retry(exc=exc)
