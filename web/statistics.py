import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Environment, FileSystemLoader
from datetime import date

from .dependencies import get_db, get_current_user, role_required
from bot.services.cost_service import calculate_full_cost

router = APIRouter()
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    auto_reload=True
)

@router.get("/cost-calculation")
async def cost_calculation_page(request: Request, current_user=Depends(role_required(["admin", "manager"]))):
    template = env.get_template("cost_calculation.html")
    return HTMLResponse(template.render({"request": request, "user": current_user}))

@router.post("/cost-calculation")
async def cost_calculation_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"])),
    period_start: date = Form(...),
    period_end: date = Form(...)
):
    result = await calculate_full_cost(db, period_start, period_end)
    if not result:
        return RedirectResponse(url="/cost-calculation?error=no_production", status_code=302)
    return RedirectResponse(url=f"/cost-calculation/result/{result.id}", status_code=302)

@router.get("/cost-calculation/result/{calc_id}")
async def cost_result(calc_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user=Depends(role_required(["admin", "manager"]))):
    from bot.models.cost_calculation import CostCalculation
    calc = await db.get(CostCalculation, calc_id)
    if not calc:
        raise HTTPException(status_code=404)
    template = env.get_template("cost_result.html")
    return HTMLResponse(template.render({"request": request, "user": current_user, "calc": calc}))