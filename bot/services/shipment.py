from sqlalchemy import select
from bot.models.database import async_session
from bot.models import Shipment, Storage

# Сохранение отгрузки в базу данных
async def save_shipment(user_id: int, small_packs: int, large_packs: int, session: async_session):
    shipment = Shipment(user_id=user_id, small_packs=small_packs, large_packs=large_packs)
    session.add(shipment)
    await session.commit()

# Обновление остатков на складе после отгрузки
async def update_stock_after_shipment(small_packs: int, large_packs: int, session: async_session):
    # Получаем текущий склад
    stock = await session.get(Storage, 1)

    # Обновляем количество пачек на складе
    stock.packs_3kg -= small_packs
    stock.packs_5kg -= large_packs

    await session.commit()


