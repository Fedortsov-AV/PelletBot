from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Shipment, ShipmentItem, Product, ProductStorage, User


async def save_shipment(
        telegram_id: int,  # Используем telegram_id вместо user_id
        product_id: int,
        quantity: int,
        session: AsyncSession
):
    """Создание записи об отгрузке"""
    # Получаем user_id по telegram_id
    user = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = user.scalar_one()

    # Создаем запись об отгрузке
    shipment = Shipment(
        user_id=user.id,  # Используем внутренний id пользователя
        timestamp=datetime.now()
    )
    session.add(shipment)
    await session.flush()  # Получаем ID отгрузки

    # Добавляем элементы отгрузки
    shipment_item = ShipmentItem(
        shipment_id=shipment.id,
        product_id=product_id,
        quantity=quantity
    )
    session.add(shipment_item)

    # Обновляем остатки на складе
    await update_product_stock(product_id, -quantity, session)

    await session.commit()
    return shipment


async def update_product_stock(
        product_id: int,
        quantity_delta: int,
        session: AsyncSession
):
    """Обновление остатков продукта на складе"""
    storage = await session.get(ProductStorage, product_id)
    if storage:
        storage.amount += quantity_delta
        if storage.amount < 0:
            raise ValueError("Недостаточно товара на складе")
        await session.commit()


async def get_available_products(session: AsyncSession):
    """Получение списка продуктов с остатками на складе"""
    result = await session.execute(
        select(Product, ProductStorage.amount)
        .join(ProductStorage, Product.id == ProductStorage.product_id)
        .where(ProductStorage.amount > 0)
    )
    return result.all()

