from aiogram.types import Message
from sqlalchemy import select, extract
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import RawMaterialStorage
from bot.models.database import async_session
from bot.models.arrival import Arrival
from datetime import datetime

from bot.models.rawProduct import RawProduct
from bot.services.storage import update_stock_arrival
from bot.services.user_service import get_user


async def process_arrival(message: Message):
    """Обработка прихода без запроса комментария."""
    async with async_session() as session:
        arrival = Arrival(
            type="default",  # Можно заменить на реальный тип, если он есть
            amount=1,  # Можно передавать реальное количество
            date=datetime.utcnow(),
            user_id=message.from_user.id
        )
        session.add(arrival)
        await session.commit()

    await message.answer("Приход успешно зарегистрирован!")


async def add_arrival(session: AsyncSession, tg_id: int, type: str, amount: int):
    async with session.begin():  # Атомарная транзакция
        try:
            user = await get_user(session, tg_id)
            print(f'Получен user_id {user.id=}')
            # Добавляем приход
            arrival = Arrival(
                type=type,
                amount=amount,
                user_id=user.id,
                date=datetime.utcnow(),
            )
            session.add(arrival)

            # Вызов обновления склада с передачей всех аргументов
            await update_stock_arrival(session,type, amount)
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise

async def get_arrivals_for_month(session: AsyncSession, user_id: int):
    """Получение приходов за текущий месяц"""
    current_month = datetime.utcnow().month
    result = await session.execute(
        select(Arrival).filter(
            extract('month', Arrival.date) == current_month,  # Используем extract для получения месяца

        )
    )
    return result.scalars().all()

async def delete_arrival(session: AsyncSession, arrival_id: int):
    """Удаление прихода по ID"""
    result = await session.execute(select(Arrival).where(Arrival.id == arrival_id))
    arrival = result.scalars().first()
    if arrival:
        await session.delete(arrival)
        await session.commit()
    return arrival

async def update_arrival_amount(session: AsyncSession, arrival_id: int, new_amount: int):
    """Изменение количества продукции в приходе"""
    try:
        result = await session.execute(select(Arrival).where(Arrival.id == arrival_id))
        arrival = result.scalars().first()
        if arrival:

            # Корректируем склад
            delta = new_amount - arrival.amount
            arrival.amount = new_amount
            await update_stock_arrival(session, arrival.type, delta)  # Изменяем склад
            await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

async def get_raw_product_names(session: AsyncSession):
    """Получить список всех наименований raw_products из БД"""
    result = await session.execute(select(RawProduct.name))
    rows = result.all()  # Результат выполнения запроса
    # print(f"Rows: {rows}")  # Печать всех строк для отладки

    # Возвращаем список только с названиями продуктов
    return [row[0] for row in rows]