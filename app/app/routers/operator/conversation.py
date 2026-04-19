"""Роутер для работы операторов с диалогами."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_conversation_service,
    get_message_service,
    get_llm_service
)

from app.models.user import User
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.llm_service import LLMService
from app.core.logging import get_logger

logger = get_logger(__name__)


router = APIRouter(
    prefix="/operator",
    tags=["operator"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/queue", status_code=status.HTTP_200_OK, summary="Получить список диалогов в очереди")
async def get_conversation_queue(
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """Получить список диалогов в очереди."""
    
    if current_user.role != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён: требуется роль оператора.",
        )
        
    try:
        conversations = await conversation_service.get_active_queue()
        
        logger.info(f"Оператор {current_user.id} получил очередь диалогов: {len(conversations)} диалогов.")
        return conversations
    
    except Exception as exc:
        logger.exception("Ошибка при получении очереди диалогов.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении очереди диалогов.",
        ) from exc
        
        
@router.post("/assign/{conversation_id}", status_code=status.HTTP_200_OK, summary="Назначить диалог оператору")
async def assign_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """Назначить диалог оператору."""
    
    if current_user.role != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён: требуется роль оператора.",
        )
        
    try:
        conversation = await conversation_service.assign_operator(conversation_id, current_user.id)
        
        if not conversation:
            logger.warning(f"Оператор {current_user.id} попытался назначить диалог {conversation_id}, но он не найден или уже назначен.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Диалог не найден или уже назначен.",
            )
        
        logger.info(f"Оператор {current_user.id} назначен на диалог {conversation_id}.")
        return conversation
    
    except HTTPException:
        logger.warning(f"Оператор {current_user.id} не смог назначить диалог {conversation_id} из-за ошибки HTTP.")
        raise
    
    except Exception as exc:
        logger.exception("Ошибка при назначении диалога оператору.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при назначении диалога оператору.",
        ) from exc
        
        
@router.post("/reply/{conversation_id}", status_code=status.HTTP_200_OK, summary="Ответить в диалоге")
async def reply_to_conversation(
    conversation_id: int,
    message: str,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Ответить в диалоге."""
    
    if current_user.role != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён: требуется роль оператора.",
        )
        
    try:
        response = await message_service.create_message(
            conversation_id,
            sender_type="operator",
            sender_id=current_user.id,
            content=message
        )
        
        if not response:
            logger.warning(f"Оператор {current_user.id} попытался ответить в диалоге {conversation_id}, но он не найден или не назначен ему.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Диалог не найден или не назначен вам.",
            )
        
        logger.info(f"Оператор {current_user.id} ответил в диалоге {conversation_id}.")
        return response
    
    except HTTPException:
        logger.warning(f"Оператор {current_user.id} не смог ответить в диалоге {conversation_id} из-за ошибки HTTP.")
        raise
    
    except Exception as exc:
        logger.exception("Ошибка при ответе в диалоге.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при ответе в диалоге.",
        ) from exc
        
        
@router.post("/close/{conversation_id}", status_code=status.HTTP_200_OK, summary="Закрыть диалог")
async def close_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """Закрыть диалог."""
    
    if current_user.role != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён: требуется роль оператора.",
        )
        
    try:
        result = await conversation_service.close(conversation_id)
        
        if not result:
            logger.warning(f"Оператор {current_user.id} попытался закрыть диалог {conversation_id}, но он не найден или не назначен ему.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Диалог не найден или не назначен вам.",
            )
        
        logger.info(f"Оператор {current_user.id} закрыл диалог {conversation_id}.")
        return {"detail": "Диалог успешно закрыт."}
    
    except HTTPException:
        logger.warning(f"Оператор {current_user.id} не смог закрыть диалог {conversation_id} из-за ошибки HTTP.")
        raise
    
    except Exception as exc:
        logger.exception("Ошибка при закрытии диалога.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при закрытии диалога.",
        ) from exc
        
        
@router.post("/back_to_ai/{conversation_id}", status_code=status.HTTP_200_OK, summary="Вернуть диалог в очередь ИИ")
async def back_to_ai(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Вернуть диалог в очередь ИИ."""
    
    if current_user.role != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён: требуется роль оператора.",
        )
        
    try:
        result = await conversation_service.back_to_ai(conversation_id)
        
        if not result:
            logger.warning(f"Оператор {current_user.id} попытался вернуть диалог {conversation_id} в очередь ИИ, но он не найден или не назначен ему.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Диалог не найден или не назначен вам.",
            )
        
        logger.info(f"Оператор {current_user.id} вернул диалог {conversation_id} в очередь ИИ.")
        return {"detail": "Диалог успешно возвращен в очередь ИИ."}
    
    except HTTPException:
        logger.warning(f"Оператор {current_user.id} не смог вернуть диалог {conversation_id} в очередь ИИ из-за ошибки HTTP.")
        raise
    
    except Exception as exc:
        logger.exception("Ошибка при возвращении диалога в очередь ИИ.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при возвращении диалога в очередь ИИ.",
        ) from exc
