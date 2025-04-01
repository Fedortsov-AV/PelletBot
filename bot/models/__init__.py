from bot.models.database import engine
from bot.models.base import Base
from bot.models.user import User
from bot.models.arrival import Arrival
from bot.models.role import Role
from bot.models.expense import Expense
from bot.models.packaging import Packaging
from bot.models.storage import ProductStorage, RawMaterialStorage
from bot.models.shipment import Shipment
from bot.models.product import Product
from bot.models.rawProduct import RawProduct

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)