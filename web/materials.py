import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from jinja2 import Environment, FileSystemLoader

from bot.models import Expense
from bot.models.material import Material
from bot.models.material_movement import MaterialMovement
from bot.services.material_service import purchase_material
from bot.services.user_service import get_user
from .dependencies import get_db, get_current_user, role_required
from sqlalchemy import case
from sqlalchemy.orm import selectinload

router = APIRouter()
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    auto_reload=True
)

@router.get("/materials")
async def list_materials(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Получаем все материалы с подсчётом текущего остатка
    q = select(
        Material,
        func.coalesce(
            func.sum(
                case(
                    (MaterialMovement.type == 'in', MaterialMovement.quantity),
                    else_=-MaterialMovement.quantity
                )
            ), 0
        ).label("stock")
    ).join(MaterialMovement, Material.id == MaterialMovement.material_id, isouter=True) \
     .group_by(Material.id)

    result = await db.execute(q)
    rows = result.all()  # список кортежей (Material, stock)

    template = env.get_template("materials.html")
    return HTMLResponse(template.render({
        "request": request,
        "user": current_user,
        "materials": rows  # передаём материал + остаток
    }))

@router.get("/materials/add")
async def add_material_form(
    request: Request,
    current_user=Depends(role_required(["admin", "manager"]))
):
    template = env.get_template("material_add.html")
    return HTMLResponse(template.render({"request": request, "user": current_user}))

@router.post("/materials/add")
async def add_material_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"])),
    name: str = Form(...)
):
    # Проверка уникальности
    exists = (await db.execute(select(Material).where(Material.name == name))).scalar_one_or_none()
    if exists:
        return RedirectResponse(url="/materials/add?error=exists", status_code=302)

    new_mat = Material(name=name)
    db.add(new_mat)
    await db.commit()
    return RedirectResponse(url="/materials", status_code=302)

@router.get("/materials/{material_id}/edit")
async def edit_material_form(
    material_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"]))
):
    material = await db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Материал не найден")
    template = env.get_template("material_edit.html")
    return HTMLResponse(template.render({
        "request": request, "user": current_user, "material": material
    }))

@router.post("/materials/{material_id}/edit")
async def edit_material_submit(
    material_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"])),
    name: str = Form(...)
):
    material = await db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404)
    # Проверка уникальности имени
    dup = (await db.execute(select(Material).where(Material.name == name, Material.id != material_id))).scalar_one_or_none()
    if dup:
        return RedirectResponse(f"/materials/{material_id}/edit?error=exists", status_code=302)
    material.name = name
    await db.commit()
    return RedirectResponse("/materials", status_code=302)

@router.post("/materials/{material_id}/delete")
async def delete_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"]))
):
    material = await db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404)
    # Проверим, есть ли движения
    count = (await db.execute(select(func.count(MaterialMovement.id)).where(MaterialMovement.material_id == material_id))).scalar()
    if count > 0:
        return RedirectResponse("/materials?error=has_movements", status_code=302)
    await db.delete(material)
    await db.commit()
    return RedirectResponse("/materials", status_code=302)

@router.get("/materials/purchase")
async def purchase_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"]))
):
    materials = (await db.execute(select(Material))).scalars().all()
    template = env.get_template("material_purchase.html")
    return HTMLResponse(template.render({
        "request": request,
        "user": current_user,
        "materials": materials
    }))

@router.post("/materials/purchase")
async def purchase_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"])),
    material_id: int = Form(...),
    quantity: float = Form(...),
    unit: str = Form(...),
    unit_price: float = Form(...),
    create_expense: bool = Form(False)
):
    quantity = round(quantity, 2)
    unit_price = round(unit_price, 2)
    # Проверяем существование материала
    material = await db.get(Material, material_id)
    if not material:
        return RedirectResponse("/materials/purchase?error=material_not_found", status_code=302)

    expense_amount = unit_price * quantity if create_expense else None
    user = await get_user(db, current_user.telegram_id)
    await purchase_material(
        session=db,
        material_id=material_id,
        quantity=quantity,
        unit=unit,
        unit_price=unit_price,
        expense_amount=expense_amount,
        user_id=user.id
    )
    return RedirectResponse("/materials", status_code=302)

@router.get("/materials/{material_id}/movements")
async def material_movements(
    material_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    material = await db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Материал не найден")

    # Приходные движения (type='in') для данного материала
    result = await db.execute(
        select(MaterialMovement)
        .where(
            MaterialMovement.material_id == material_id,
            MaterialMovement.type == 'in'
        )
        .order_by(MaterialMovement.date.desc())
    )
    movements = result.scalars().all()

    template = env.get_template("material_movements.html")
    return HTMLResponse(template.render({
        "request": request,
        "user": current_user,
        "material": material,
        "movements": movements
    }))

@router.get("/materials/movements/{movement_id}/edit")
async def edit_movement_form(
    movement_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"]))
):
    result = await db.execute(
        select(MaterialMovement)
        .options(selectinload(MaterialMovement.material))
        .where(MaterialMovement.id == movement_id)
    )
    movement = result.scalar_one_or_none()
    if not movement or movement.type != 'in':
        raise HTTPException(status_code=404, detail="Закупка не найдена")

    template = env.get_template("material_movement_edit.html")
    return HTMLResponse(template.render({
        "request": request,
        "user": current_user,
        "movement": movement
    }))

@router.post("/materials/movements/{movement_id}/edit")
async def edit_movement_submit(
    movement_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"])),
    quantity: float = Form(...),
    unit_price: float = Form(...)
):
    quantity = round(quantity, 2)
    unit_price = round(unit_price, 2)
    movement = await db.get(MaterialMovement, movement_id)
    if not movement or movement.type != 'in':
        raise HTTPException(status_code=404)

    old_qty = movement.quantity
    # Обновляем остаток с учётом нового количества
    if old_qty > 0:
        movement.remaining_quantity = max(0, movement.remaining_quantity + (quantity - old_qty))
    else:
        movement.remaining_quantity = quantity
    movement.quantity = quantity
    movement.unit_price = unit_price

    # Если с этой закупкой связан расход, обновляем его
    if movement.expense_id:
        expense = await db.get(Expense, movement.expense_id)
        if expense:
            # Пересчитываем сумму расхода
            expense.amount = quantity * unit_price
            # Обновляем количество в расходе (если поле quantity существует)
            # expense.quantity менять не обязательно, т.к. оно хранит изначальное количество закупки
            # Но можно и обновить, если нужно
            expense.quantity = quantity

    await db.commit()
    return RedirectResponse(f"/materials/{movement.material_id}/movements", status_code=302)

@router.post("/materials/movements/{movement_id}/delete")
async def delete_movement(
    movement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"]))
):
    movement = await db.get(MaterialMovement, movement_id)
    if not movement or movement.type != 'in':
        raise HTTPException(status_code=404)

    # Проверка, что закупка не была использована частично
    if movement.remaining_quantity < movement.quantity:
        return RedirectResponse(f"/materials/{movement.material_id}/movements?error=partially_used", status_code=302)

    material_id = movement.material_id

    # Если с закупкой связан расход, удаляем его
    if movement.expense_id:
        from bot.models.expense import Expense
        expense = await db.get(Expense, movement.expense_id)
        if expense:
            await db.delete(expense)

    await db.delete(movement)
    await db.commit()
    return RedirectResponse(f"/materials/{material_id}/movements", status_code=302)