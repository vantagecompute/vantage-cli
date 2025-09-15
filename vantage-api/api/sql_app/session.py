"""Core module for database session related operations."""
from asyncio import current_task
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_scoped_session, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.settings import SETTINGS

engines: dict[str, AsyncEngine] = {}


async def create_keycloak_conn() -> asyncpg.Connection:
    """Create a connection to the database."""
    conn_url = "postgresql://{}:{}@{}:{}/{}".format(
        SETTINGS.KC_DB_USERNAME,
        SETTINGS.KC_DB_PASSWORD,
        SETTINGS.KC_DB_HOST,
        SETTINGS.KC_DB_PORT,
        SETTINGS.KC_DB_DATABASE,
    )
    conn = await asyncpg.connect(conn_url)
    return conn


@asynccontextmanager
async def keycloak_transaction():
    """Create a transaction against the Keycloak database."""
    conn = await create_keycloak_conn()
    async with conn.transaction():
        yield conn


async def create_async_session(
    db: str, use_cached_engines: bool = True, read_only: bool = False
) -> async_scoped_session:
    """Create an async session against the API's database."""
    host = (
        SETTINGS.DB_HOST_READ_REPLICA
        if read_only and SETTINGS.DB_HOST_READ_REPLICA is not None
        else SETTINGS.DB_HOST
    )
    conn_url = "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
        SETTINGS.DB_USERNAME,
        SETTINGS.DB_PASSWORD,
        host,
        SETTINGS.DB_PORT,
        db,
    )

    if use_cached_engines:
        if db not in engines:
            engine = create_async_engine(
                conn_url,
                pool_pre_ping=True,
                pool_size=SETTINGS.DB_POOL_SIZE,
                max_overflow=SETTINGS.DB_MAX_OVERFLOW,
                connect_args={"server_settings": {"jit": SETTINGS.DB_JIT}},
            )
            engines[db] = engine
        else:
            engine = engines[db]
    else:
        engine = create_async_engine(
            conn_url,
            pool_pre_ping=True,
            pool_size=SETTINGS.DB_POOL_SIZE,
            max_overflow=SETTINGS.DB_MAX_OVERFLOW,
        )

    async_session = async_scoped_session(
        sessionmaker(
            engine,
            expire_on_commit=False,
            class_=AsyncSession,
        ),
        scopefunc=current_task,
    )
    return async_session


@asynccontextmanager
async def async_session(db: str, read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
    """Create a transaction against the API's database."""
    session = await create_async_session(db, read_only=read_only)
    async with session() as sess:
        async with sess.begin():
            try:
                yield sess
            except Exception as err:
                await sess.rollback()
                raise err
            finally:
                await sess.close()
