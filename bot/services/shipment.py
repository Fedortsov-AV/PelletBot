from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.database import async_session
from bot.models import Shipment, Storage

# Сохранение отгрузки в базу данных
async def save_shipment(user_id: int, small_packs: int, large_packs: int, session: AsyncSession):
    shipment = Shipment(user_id=user_id, small_packs=small_packs, large_packs=large_packs)
    session.add(shipment)
    await session.commit()

# Обновление остатков на складе после отгрузки
async def update_stock_after_shipment(small_packs: int, large_packs: int, session: AsyncSession):
    # Получаем текущий склад
    stock = await session.get(Storage, 1)

    # Обновляем количество пачек на складе
    stock.packs_3kg -= small_packs
    stock.packs_5kg -= large_packs

    await session.commit()


# Получаем сумму отгрузок за текущий месяц
async def get_shipments_for_current_month(session: AsyncSession):
    """Получить сумму отгрузок за текущий месяц"""
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)  # Начало текущего месяца
    end_of_month = datetime(now.year, now.month + 1, 1) if now.month < 12 else datetime(now.year + 1, 1, 1)  # Начало следующего месяца

    try:
        result = await session.execute(
            select(
                func.sum(Shipment.small_packs),
                func.sum(Shipment.large_packs)
            ).filter(
                Shipment.timestamp >= start_of_month,
                Shipment.timestamp < end_of_month
            )
        )
        shipments = result.fetchone()  # Получаем результат из запроса
        return shipments

    except SQLAlchemyError as e:
        await session.rollback()  # Откат транзакции при ошибке
        print(f"Ошибка выполнения запроса: {e}")
        return None

# Получаем сумму отгрузок за определённый период
async def get_shipments_for_period(session: AsyncSession, start_date: str, end_date: str):
    """Получить сумму отгрузок за определённый период для пользователя"""
    try:

        # Создаем запрос с использованием select и фильтрации по дате
        stmt = select(
            func.sum(Shipment.small_packs).label('small_packs_sum'),
            func.sum(Shipment.large_packs).label('large_packs_sum')
        ).filter(Shipment.timestamp >= start_date, Shipment.timestamp < end_date)

        # Выполняем запрос
        result = await session.execute(stmt)
        shipments = result.fetchone()

        if shipments:
            return shipments.small_packs_sum, shipments.large_packs_sum
        return 0, 0  # Если нет данных для этого периода

    except ValueError:
        return None  # Некорректный формат даты
