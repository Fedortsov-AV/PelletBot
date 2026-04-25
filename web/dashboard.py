import os
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from jinja2 import Environment, FileSystemLoader
from bot.models.storage import RawMaterialStorage, ProductStorage
from .dependencies import get_db, get_current_user
from datetime import datetime
from bot.models.arrival import Arrival
from bot.models.shipment import Shipment, ShipmentItem
router = APIRouter()

env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    auto_reload=True
)


@router.get("/dashboard")
async def dashboard(request: Request, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    # Сырьё с подгрузкой названий
    raw_result = await db.execute(
        select(RawMaterialStorage).options(selectinload(RawMaterialStorage.raw_product))
    )
    raw_stocks = raw_result.scalars().all()

    # Продукция с подгрузкой названий
    prod_result = await db.execute(
        select(ProductStorage).options(selectinload(ProductStorage.product))
    )
    product_stocks = prod_result.scalars().all()

    from datetime import datetime
    current_month = datetime.utcnow().month

    raw_total = sum(s.amount for s in raw_stocks)
    product_total = sum(s.amount for s in product_stocks)

    arrivals_count = (await db.execute(
        select(func.count(Arrival.id)).where(extract('month', Arrival.date) == current_month)
    )).scalar()

    shipments_total = (await db.execute(
        select(func.coalesce(func.sum(ShipmentItem.quantity), 0))
        .join(Shipment)
        .where(extract('month', Shipment.timestamp) == current_month)
    )).scalar()

    template = env.get_template("dashboard.html")
    html = template.render({
        "request": request,
        "user": current_user,
        "raw_stocks": raw_stocks,
        "product_stocks": product_stocks,
        "arrivals_count": arrivals_count,
        "raw_total": raw_total,
        "product_total": product_total,
        "shipments_total": shipments_total
    })
    return HTMLResponse(html)