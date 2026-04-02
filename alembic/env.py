import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# alembic.ini 설정 로드
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 모델 메타데이터 임포트 (autogenerate 지원)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dashboard.db import Base  # noqa: E402
from dashboard.models import Job  # noqa: E402, F401  — 모델 등록

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # async URL → 동기 URL로 변환해서 alembic에 전달
    from config import settings

    url = settings.database_url.replace("+asyncpg", "+psycopg2")
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # asyncpg URL 사용
        **{"url": settings.database_url},
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
