from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
import asyncio

from alembic import context

from app.db import Base
from app.models.user import User, UserRole  # noqa: F401 - импортируем модели для регистрации в метаданных

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Изменяем эту функцию, чтобы она запускала асинхронный цикл"""
    asyncio.run(run_migrations_online_async())

async def run_migrations_online_async() -> None:
    """Основная логика миграций для aiosqlite"""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # ВАЖНО: для SQLite добавляем render_as_batch=True
        await connection.run_sync(
            lambda conn: context.configure(
                connection=conn, 
                target_metadata=target_metadata,
                render_as_batch=True # Без этого SQLite не даст менять колонки
            )
        )

        async with connection.begin():
            await connection.run_sync(lambda _: context.run_migrations())
    
    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()