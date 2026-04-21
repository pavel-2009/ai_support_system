"""Базовые зависимости для приложения."""

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import verify_access_token
from app.db import get_async_session
from app.models.conversation import Conversation, Status
from app.models.user import User
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.user_service import UserService
from app.services.llm_service import LLMService
from app.repositories.llm_repo import LLMRepository

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    description="JWT токен доступа"
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Получить текущего пользователя по access JWT."""
    payload = verify_access_token(token)
    if payload is None:
        logger.warning("Ошибка авторизации: недействительный access токен.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен доступа.",
        )

    user_id = payload.get("user_id")
    if user_id is None:
        logger.warning("Ошибка авторизации: в токене отсутствует user_id.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный payload токена.",
        )

    try:
        return await UserService(session).get_user_by_id(int(user_id))
    except ValueError as exc:
        logger.exception("Ошибка авторизации: пользователь из токена не найден.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь из токена не найден.",
        ) from exc


async def require_authenticated_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Общая зависимость для защищённых эндпоинтов (только авторизованный пользователь)."""
    return current_user


async def get_user_service(
    session: AsyncSession = Depends(get_async_session),
) -> UserService:
    """Зависимость для получения сервиса работы с пользователями."""
    return UserService(session)


async def get_conversation_service(
    session: AsyncSession = Depends(get_async_session),
) -> ConversationService:
    """Зависимость для получения сервиса работы с диалогами."""
    return ConversationService(session)


async def get_message_service(
    session: AsyncSession = Depends(get_async_session),
) -> MessageService:
    """Зависимость для получения сервиса работы с сообщениями."""
    return MessageService(session)


async def get_llm_service() -> LLMService:
    """Зависимость для получения сервиса работы с LLM."""
    # Instantiate repository with configured defaults and inject into service
    llm_repo = LLMRepository()
    return LLMService(llm_repo)


def ensure_conversation_access(current_user: User, conversation: Conversation) -> None:
    """Проверить доступ к диалогу: только админ или участник."""
    if current_user.role.value == "admin":
        return

    is_participant = current_user.id in {conversation.user_id, conversation.operator_id}
    if not is_participant:
        logger.warning(
            "Доступ запрещён: пользователь %s не является участником диалога %s.",
            current_user.id,
            conversation.id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому диалогу.",
        )


def ensure_conversation_is_open(conversation: Conversation) -> None:
    """Проверить, что диалог открыт для чтения и работы."""
    if conversation.status == Status.CLOSED:
        logger.info("Диалог %s закрыт, возвращаем 410.", conversation.id)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Диалог закрыт.",
        )


async def get_conversation_for_user(
    conversation_id: int = Path(...),
    current_user: User = Depends(require_authenticated_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> Conversation:
    """Получить диалог по id с проверкой существования и прав доступа."""
    conversation = await conversation_service.get_conversation_by_id(conversation_id)
    if conversation is None:
        logger.warning("Диалог %s не найден.", conversation_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Диалог не найден.")

    ensure_conversation_access(current_user, conversation)
    return conversation


async def get_open_conversation_for_user(
    conversation: Conversation = Depends(get_conversation_for_user),
) -> Conversation:
    """Получить доступный (не закрытый) диалог для пользователя."""
    ensure_conversation_is_open(conversation)
    return conversation
