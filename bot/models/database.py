from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from bot.config import DATABASE_URL
from bot.models.base import Base

# DATABASE_URL = "sqlite+aiosqlite:///bot/warehouse_bot.db"  # Или ваша БД


engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # Создание таблиц
