import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

from bot.models.arrival import Arrival
from bot.models.rawProduct import RawProduct
from bot.services.arrival import add_arrival, delete_arrival, update_arrival_amount, get_arrival_by_id
from bot.services.storage import update_stock_arrival
from .dependencies import get_db, get_current_user, role_required

router = APIRouter()
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    auto_reload=True
)

PAGE_SIZE = 15

@router.get("/arrivals")
async def list_arrivals(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Пагинация
    offset = (page - 1) * PAGE_SIZE
    # Получаем общее количество
    total_count = (await db.execute(select(func.count(Arrival.id)))).scalar()
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

    # Загружаем приходы с подгрузкой связанного сырья
    result = await db.execute(
        select(Arrival)
        .options(selectinload(Arrival.raw_product))
        .order_by(desc(Arrival.date))
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    arrivals = result.scalars().all()

    template = env.get_template("arrivals.html")
    html = template.render({
        "request": request,
        "user": current_user,
        "arrivals": arrivals,
        "page": page,
        "total_pages": total_pages,
        "total_count": total_count
    })
    return HTMLResponse(html)

@router.get("/arrivals/add")
async def add_arrival_form(request: Request, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role not in ("admin", "manager", "operator"):
        raise HTTPException(status_code=403)
    # Получаем список сырья
    raw_result = await db.execute(select(RawProduct))
    raw_products = raw_result.scalars().all()
    template = env.get_template("arrival_add.html")
    return HTMLResponse(template.render({"request": request, "user": current_user, "raw_products": raw_products}))

@router.post("/arrivals/add")
async def add_arrival_submit(
    request: Request,
    raw_product_id: int = Form(...),
    amount: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager", "operator"):
        raise HTTPException(status_code=403)
    await add_arrival(db, current_user.telegram_id, raw_product_id, amount)
    return RedirectResponse(url="/arrivals", status_code=302)


@router.get("/arrivals/{arrival_id}/edit")
async def edit_arrival_form(
        arrival_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

    # Загружаем приход вместе со связанным сырьём
    result = await db.execute(
        select(Arrival)
        .options(selectinload(Arrival.raw_product))
        .where(Arrival.id == arrival_id)
    )
    arrival = result.scalar_one_or_none()

    if not arrival:
        raise HTTPException(status_code=404, detail="Приход не найден")

    template = env.get_template("arrival_edit.html")
    return HTMLResponse(template.render({"request": request, "user": current_user, "arrival": arrival}))

@router.post("/arrivals/{arrival_id}/edit")
async def edit_arrival_submit(
    arrival_id: int,
    amount: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)
    await update_arrival_amount(db, arrival_id, amount)
    return RedirectResponse(url="/arrivals", status_code=302)

# Удаление прихода
@router.post("/arrivals/{arrival_id}/delete")
async def delete_arrival_handler(
    arrival_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)
    await delete_arrival(db, arrival_id)
    return RedirectResponse(url="/arrivals", status_code=302)