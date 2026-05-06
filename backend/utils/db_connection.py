"""Database connection utilities using asyncpg."""
import asyncpg
from typing import Optional
from config import get_settings

settings = get_settings()

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            min_size=5,
            max_size=20
        )
    return _pool


async def close_pool():
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


class Database:
    """Database helper for executing queries via the connection pool."""

    @staticmethod
    async def fetch_one(query: str, *args):
        """Fetch a single row."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    @staticmethod
    async def fetch_all(query: str, *args):
        """Fetch all rows."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    @staticmethod
    async def execute(query: str, *args):
        """Execute a query without returning results."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    @staticmethod
    async def execute_many(query: str, args_list: list):
        """Execute a query multiple times with different arguments."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            return await conn.executemany(query, args_list)


db = Database()
