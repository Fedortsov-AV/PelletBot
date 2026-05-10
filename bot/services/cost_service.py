from datetime import date
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.expense import Expense
from bot.models.packaging import Packaging
from bot.models.cost_calculation import CostCalculation

async def calculate_full_cost(session: AsyncSession, period_start: date, period_end: date):
    # Суммируем все накладные расходы (все категории) за период
    overhead = await session.execute(
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(and_(Expense.date >= period_start, Expense.date <= period_end))
    )
    total_overhead = overhead.scalar()

    # Общий выпуск в кг (по израсходованному сырью)
    prod = await session.execute(
        select(func.coalesce(func.sum(Packaging.used_raw_material), 0))
        .where(and_(Packaging.date >= period_start, Packaging.date <= period_end))
    )
    total_kg = prod.scalar()
    if total_kg == 0:
        return None  # нечего оценивать

    # Прямые материальные затраты из фасовок
    mat_cost = await session.execute(
        select(func.coalesce(func.sum(Packaging.total_material_cost), 0))
        .where(and_(Packaging.date >= period_start, Packaging.date <= period_end))
    )
    total_material_cost = mat_cost.scalar()

    cost_per_kg = (total_material_cost + total_overhead) / total_kg

    calc = CostCalculation(
        period_start=period_start,
        period_end=period_end,
        total_material_cost=total_material_cost,
        total_overhead_cost=total_overhead,
        total_produced_kg=total_kg,
        cost_per_kg=cost_per_kg
    )
    session.add(calc)
    await session.commit()
    return calc