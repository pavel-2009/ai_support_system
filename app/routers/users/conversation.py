"""Пользовательский роутер для работы с диалогами."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    get_conversation_for_user,
    get_conversation_service,
    require_authenticated_user,
)
from app.core.logging import get_logger
from app.models.conversation import Channel, Conversation, Priority, Status
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationGet,
    ConversationListResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = get_logger(__name__)


@router.post("/", response_model=ConversationGet, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(require_authenticated_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationGet:
    """Создать новый диалог."""
    logger.info("Пользователь %s создаёт новый диалог.", current_user.id)
    return await conversation_service.create_conversation(
        user_id=current_user.id,
        priority=conversation_data.priority,
        channel=conversation_data.channel,
    )


@router.get("/", response_model=ConversationListResponse)
async def get_conversations(
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    size: int = Query(default=20, ge=1, le=100, description="Размер страницы"),
    status_filter: Status | None = Query(default=None, alias="status"),
    priority_filter: Priority | None = Query(default=None, alias="priority"),
    channel_filter: Channel | None = Query(default=None, alias="channel"),
    user_id_filter: int | None = Query(default=None, alias="user_id"),
    operator_id_filter: int | None = Query(default=None, alias="operator_id"),
    current_user: User = Depends(require_authenticated_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    """Получить список диалогов с базовой фильтрацией и пагинацией."""
    offset = (page - 1) * size
    participant_id = None if current_user.role.value == "admin" else current_user.id

    items = await conversation_service.list_conversations(
        limit=size,
        offset=offset,
        status_filter=status_filter,
        priority_filter=priority_filter,
        channel_filter=channel_filter,
        user_id_filter=user_id_filter,
        operator_id_filter=operator_id_filter,
        participant_id=participant_id,
    )
    total = await conversation_service.count_conversations(
        status_filter=status_filter,
        priority_filter=priority_filter,
        channel_filter=channel_filter,
        user_id_filter=user_id_filter,
        operator_id_filter=operator_id_filter,
        participant_id=participant_id,
    )

    logger.info(
        "Список диалогов запрошен пользователем %s: page=%s size=%s total=%s.",
        current_user.id,
        page,
        size,
        total,
    )
    return ConversationListResponse(items=items, total=total, page=page, size=size)


@router.post("/{conversation_id}/close", response_model=ConversationGet)
async def close_conversation(
    conversation: Conversation = Depends(get_conversation_for_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationGet:
    """Закрыть диалог переводом в статус CLOSED."""
    closed = await conversation_service.close(conversation.id)
    if closed is None:
        logger.warning("Не удалось закрыть диалог %s: не найден.", conversation.id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Диалог не найден.")

    logger.info("Диалог %s успешно закрыт.", conversation.id)
    return closed


@router.get("/queue/active", response_model=list[ConversationGet])
async def get_active_conversations_queue(
    current_user: User = Depends(require_authenticated_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationGet]:
    """Получить активную очередь диалогов (только для админа)."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может просматривать очередь.",
        )
    return await conversation_service.get_active_queue()


@router.get("/{conversation_id}", response_model=ConversationGet)
async def get_conversation(
    conversation: Conversation = Depends(get_conversation_for_user),
) -> ConversationGet:
    """Получить диалог по id с проверкой доступа и статуса."""
    if conversation.status == Status.CLOSED:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Диалог закрыт.")
    return conversation
