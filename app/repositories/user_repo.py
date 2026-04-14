"""Репозиторий для работы с пользователями."""

from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import create_tokens
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    """Репозиторий для работы с пользователями."""

    @staticmethod
    async def get_user_by_id(
        session: AsyncSession,
        user_id: int
    ) -> User:
        """Получить пользователя по ID."""
        
        result = await session.execute(select(User).where(User.id == user_id))
        
        if not result.scalar_one_or_none():
            raise ValueError("Пользователь с таким ID не найден.")

        return result.scalar_one_or_none()


    @staticmethod
    async def create_user_by_admin(
        session: AsyncSession,
        data: UserCreate,
        current_user: User | None = None
    ) -> User:
        """Создать нового пользователя."""
        try:
        
            if UserRepository.user_exists(session, email=data.email):
                raise ValueError("Пользователь с таким email уже существует.")
            
            if current_user and current_user.role != "admin":
                raise ValueError("Только администратор может создавать новых пользователей.")
            
            new_user = User(**data.model_dump())
            
            session.add(new_user)
            await session.commit()
            
            return new_user
        
        except Exception as e:
            await session.rollback()
            raise e


    @staticmethod
    async def update_user(
        session: AsyncSession,
        user_id: int,
        data: UserUpdate,
        current_user: User | None = None
    ):
        """Обновить данные пользователя."""
        
        if not await UserRepository.user_exists(session, user_id=user_id):
            raise ValueError("Пользователь с таким ID не существует.")
        
        try:
        
            if not current_user:
                raise ValueError("Только аутентифицированный пользователь может обновлять данные.")
            
            if current_user.role != "admin" and current_user.id != user_id:
                raise ValueError("Пользователь может обновлять только свои данные.")
            
            if current_user.role != "admin" and data.role in ("admin", "operator"):
                raise ValueError("Пользователь не может повышать свою роль.")
            
            user_updated = update(User).where(User.id == user_id)
            
            await session.execute(user_updated.values(**data.model_dump(exclude_unset=True)))
                
            await session.execute(user_updated)
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            raise e


    @staticmethod
    async def delete_user(
        session: AsyncSession,
        user_id: int
    ):
        """Удалить пользователя."""
        
        if not await UserRepository.user_exists(session, user_id=user_id):
            raise ValueError("Пользователь с таким ID не существует.")
        
        try:
        
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            raise e
        
        
    @staticmethod
    async def get_all_users(session: AsyncSession):
        """Получить всех пользователей."""
        
        try:
        
            result = await session.execute(select(User))
            
            return result.scalars().all()
        except Exception as e:
            await session.rollback()
            raise e
    
    
    @staticmethod    
    async def get_user_by_email(
        session: AsyncSession, 
        email: str
    ) -> User:
        """Получить пользователя по email."""
        
        if not await UserRepository.user_exists(session, email=email):
            raise ValueError("Пользователь с таким email не найден.")
        
        try:
        
            result = await session.execute(select(User).where(User.email == email))
            
            return result.scalar_one_or_none()
        
        except Exception as e:
            await session.rollback()
            raise e
    
    
    @staticmethod
    async def user_exists(
        session: AsyncSession,
        email: str | None = None,
        user_id: int | None = None
    ) -> bool:
        """Проверить, существует ли пользователь с данным email или id."""
        
        try:
        
            query = select(User)
            
            if email:
                query = query.where(User.email == email)
                
            if user_id is not None:
                query = query.where(User.id == user_id)
                
            result = await session.execute(query)
            
            return result.scalar_one_or_none() is not None
        
        except Exception as e:
            await session.rollback()
            raise e


    @staticmethod
    async def register_user(
        session: AsyncSession,
        name: str,
        email: str
    ) -> User:
        """Зарегистрировать нового пользователя, если email не занят."""
        
        if await UserRepository.user_exists(session, email=email):
            raise ValueError("Пользователь с таким email уже существует.")
        
        return await UserRepository.create_user(session, name, email)
    
    
    @staticmethod
    async def update_user_email(
        session: AsyncSession,
        user_id: int,
        new_email: str
    ):
        """Обновить email пользователя, если новый email не занят."""
        
        if not await UserRepository.user_exists(session, user_id=user_id):
            raise ValueError("Пользователь с таким ID не существует.")
        
        if await UserRepository.user_exists(session, email=new_email):
            raise ValueError("Пользователь с таким email уже существует.")
        
        await UserRepository.update_user(session, user_id, email=new_email)
        
        
    @staticmethod
    async def create_tokens_for_user(
        session: AsyncSession,
        user_id: int,
    ):
        """Создать токен для пользователя."""
        
        user = await UserRepository.get_user_by_id(session, user_id)
        
        if not user:
            raise ValueError("Пользователь с таким ID не существует.")
        
        # Создаем токены
        try:
            tokens = create_tokens(user_id)
            
            return tokens
        
        except Exception as e:
            raise e
