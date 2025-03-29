from aiogram.types import Message
from sqlalchemy import select, extract
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.database import async_session
from bot.models.arrival import Arrival
from datetime import datetime

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

async def add_arrival(session: AsyncSession, user_id: int, amount: int, type: str):
    """Добавление нового прихода"""
    arrival = Arrival(
        type=type,
        amount=amount,
        date=datetime.utcnow(),
        user_id=user_id
    )
    session.add(arrival)
    await session.commit()

    return arrival

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
    result = await session.execute(select(Arrival).where(Arrival.id == arrival_id))
    arrival = result.scalars().first()
    if arrival:
        arrival.amount = new_amount
        await session.commit()
    return arrival