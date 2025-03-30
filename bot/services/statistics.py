from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, case, extract

from bot.models import User
from bot.models.arrival import Arrival
from bot.models.packaging import Packaging
from bot.models.expense import Expense
from datetime import datetime, date


async def get_stock(session: AsyncSession):
    # Получаем сумму пеллет 6мм
    pellets_result = await session.execute(
        select(func.sum(Arrival.amount)).where(Arrival.type == "Пеллеты 6мм")
    )
    pellets_6mm = pellets_result.scalar() or 0

    # Получаем количество расфасованных пачек
    packaging_result = await session.execute(
        select(
            func.sum(Packaging.small_packs),
            func.sum(Packaging.large_packs)
        )
    )
    small_packs, large_packs = packaging_result.one()

    return {
        "pellets_6mm": pellets_6mm,
        "packs_3kg": small_packs or 0,
        "packs_5kg": large_packs or 0
    }


async def get_packed_month(session: AsyncSession):
    now = datetime.utcnow()  # Получаем текущую дату и время (UTC)

    result = await session.execute(
        select(
            func.sum(Packaging.small_packs),
            func.sum(Packaging.large_packs)
        ).where(
            extract("year", Packaging.date) == now.year,  # Фильтр по году
            extract("month", Packaging.date) == now.month  # Фильтр по месяцу
        )
    )

    small_packs, large_packs = result.one()  # Получаем оба значения сразу
    return {"packs_3kg": small_packs or 0, "packs_5kg": large_packs or 0}

# 📦 Расфасовано за заданный период
async def get_packed_period(session: AsyncSession, start_date: date, end_date: date):
    result = await session.execute(
        select(
            func.sum(Packaging.small_packs),
            func.sum(Packaging.large_packs)
        ).where(
            and_(
                Packaging.date >= start_date,
                Packaging.date <= end_date
            )
        )
    )
    packed = result.one()
    return {"packs_3kg": packed[0] or 0, "packs_5kg": packed[1] or 0}

# 📥 Сумма приходов за текущий месяц
async def get_arrivals_month(session: AsyncSession):
    today = datetime.today()
    first_day = datetime(today.year, today.month, 1)

    result = await session.execute(
        select(func.sum(Arrival.amount)).where(Arrival.date >= first_day)
    )
    total_arrivals = result.scalar()
    return total_arrivals or 0

# 📥 Сумма приходов за заданный период
async def get_arrivals_period(session: AsyncSession, start_date: date, end_date: date):
    result = await session.execute(
        select(func.sum(Arrival.amount)).where(
            and_(Arrival.date >= start_date, Arrival.date <= end_date)
        )
    )
    total_arrivals = result.scalar()
    return total_arrivals or 0

# 💰 Расходы пользователя
async def get_user_expenses(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(func.sum(Expense.amount)).where(
            and_(Expense.user_id == user_id, Expense.source == "собственные средства")
        )
    )
    total_expenses = result.scalar()
    return total_expenses or 0

# 📜 Список всех расходов
async def get_all_expenses(session: AsyncSession):
    result = await session.execute(
        select(User.full_name, Expense.amount, Expense.purpose)
        .join(User, User.telegram_id == Expense.user_id)
        .order_by(Expense.date.desc())
    )
    expenses = [{"user": row[0], "amount": row[1], "purpose": row[2]} for row in result.all()]
    return expenses