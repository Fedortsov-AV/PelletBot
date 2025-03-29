from bot.models.database import engine
from bot.models.base import Base
from bot.models.user import User
from bot.models.arrival import Arrival
from bot.models.role import Role
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)