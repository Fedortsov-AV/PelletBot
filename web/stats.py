import os
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, and_
from jinja2 import Environment, FileSystemLoader

from bot.models.packaging import Packaging
from bot.models.expense import Expense
from bot.models.storage import RawMaterialStorage, ProductStorage
from .dependencies import get_db, get_current_user

router = APIRouter()
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    auto_reload=True
)

@router.get("/stats")
async def stats_page(request: Request, current_user=Depends(get_current_user)):
    """Основная страница статистики."""
    return HTMLResponse(env.get_template("stats.html").render({"request": request, "user": current_user}))


@router.get("/api/stats/monthly-output")
async def monthly_output_api(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Выпуск продукции по месяцам (кг) за последние 12 месяцев."""
    # Берём последние 12 месяцев от текущего
    today = date.today()
    start_month = today.replace(day=1)
    # сдвигаемся на 12 месяцев назад
    start_month = (start_month - timedelta(days=365)).replace(day=1)

    # SQLite: группировка по году и месяцу
    result = await db.execute(
        select(
            func.strftime('%Y-%m', Packaging.date).label('month'),
            func.coalesce(func.sum(Packaging.used_raw_material), 0).label('total_kg')
        )
        .where(and_(Packaging.date >= start_month, Packaging.date <= today))
        .group_by('month')
        .order_by('month')
    )
    rows = result.all()
    labels = [row.month for row in rows]
    values = [int(row.total_kg) for row in rows]

    return JSONResponse({"labels": labels, "values": values})


@router.get("/api/stats/expenses-by-category")
async def expenses_by_category_api(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    year: int = Query(None),
    month: int = Query(None)
):
    """Затраты по категориям за указанный месяц (по умолчанию – последний полный месяц)."""
    today = date.today()
    if year is None or month is None:
        # последний завершённый месяц
        first_of_this_month = today.replace(day=1)
        last_month = first_of_this_month - timedelta(days=1)
        year = last_month.year
        month = last_month.month

    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    result = await db.execute(
        select(
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0).label('total')
        )
        .where(and_(Expense.date >= start_date, Expense.date <= end_date))
        .group_by(Expense.category)
    )
    rows = result.all()
    data = [{"category": row.category or "other", "total": round(row.total, 2)} for row in rows]
    return JSONResponse(data)


@router.get("/api/stats/current-stock")
async def current_stock_api(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Текущие остатки сырья и продукции (для виджетов)."""
    raw = await db.execute(select(RawMaterialStorage))
    raw_stocks = raw.scalars().all()
    raw_items = [{"product_id": s.raw_product_id, "amount": s.amount} for s in raw_stocks]

    prod = await db.execute(select(ProductStorage))
    prod_stocks = prod.scalars().all()
    prod_items = [{"product_id": s.product_id, "amount": s.amount} for s in prod_stocks]

    return JSONResponse({"raw": raw_items, "products": prod_items})


@router.get("/api/stats/totals")
async def totals_api(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    year: int = Query(None),
    month: int = Query(None)
):
    """Общие итоги за месяц: выпуск (кг), затраты, себестоимость."""
    today = date.today()
    if year is None or month is None:
        first_of_this_month = today.replace(day=1)
        last_month = first_of_this_month - timedelta(days=1)
        year = last_month.year
        month = last_month.month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    # Выпуск кг
    prod_result = await db.execute(
        select(func.coalesce(func.sum(Packaging.used_raw_material), 0))
        .where(and_(Packaging.date >= start_date, Packaging.date <= end_date))
    )
    total_kg = int(prod_result.scalar())

    # Материальные затраты из фасовок
    mat_cost_result = await db.execute(
        select(func.coalesce(func.sum(Packaging.total_material_cost), 0))
        .where(and_(Packaging.date >= start_date, Packaging.date <= end_date))
    )
    material_cost = round(mat_cost_result.scalar(), 2)

    # Общие расходы (накладные)
    overhead_result = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(and_(Expense.date >= start_date, Expense.date <= end_date))
    )
    overhead = round(overhead_result.scalar(), 2)

    total_cost = material_cost + overhead
    cost_per_kg = (total_cost / total_kg) if total_kg > 0 else 0

    return JSONResponse({
        "period": f"{year}-{month:02d}",
        "total_kg": total_kg,
        "material_cost": material_cost,
        "overhead": overhead,
        "total_cost": total_cost,
        "cost_per_kg": round(cost_per_kg, 2)
    })