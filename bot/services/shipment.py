from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
async def create_shipment(
        session: AsyncSession,
        telegram_id: int,  # Используем telegram_id вместо user_id

):
    user = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = user.scalar_one()

    # Создаем запись об отгрузке
    shipment = Shipment(
        user_id=user.id,  # Используем внутренний id пользователя
        timestamp=datetime.now()
    )
    session.add(shipment)
    await session.flush()
    await session.commit()
    return shipment

from sqlalchemy.orm import selectinload



from bot.models import Shipment, ShipmentItem, Product, ProductStorage, User

async def add_product_to_shipment(
    session: AsyncSession,
    shipment_id: int,
    product_id: int,
    quantity: int
) -> ShipmentItem:
    """Добавляет товар в существующую отгрузку"""
    shipment_item = ShipmentItem(
        shipment_id=shipment_id,
        product_id=product_id,
        quantity=quantity
    )
    session.add(shipment_item)
    await session.commit()
    return shipment_item

async def complete_shipment(session: AsyncSession, shipment_id: int):
    """Отмечает отгрузку как завершенную (если нужно)"""
    # Здесь можно добавить логику, если нужно отметить отгрузку как завершенную
    # Например, добавить поле completed = True в модель Shipment
    await session.commit()

async def get_shipment_products(session: AsyncSession, shipment_id: int):
    """Получает все товары в отгрузке"""
    result = await session.execute(
        select(ShipmentItem)
        .where(ShipmentItem.shipment_id == shipment_id)
        .options(selectinload(ShipmentItem.product))
    )
    return result.scalars().all()

async def get_user_shipments(session: AsyncSession,  telegram_id: int):
    """Получает все отгрузки пользователя"""
    user = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = user.scalar_one()
    print(f'{user.id=}')
    result = await session.execute(
        select(Shipment)
        .where(Shipment.user_id == user.id)
        .order_by(Shipment.timestamp.desc())
    )
    return result.scalars().all()

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

