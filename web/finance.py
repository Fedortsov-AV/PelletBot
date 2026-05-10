import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, case
from sqlalchemy.orm import selectinload
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

from bot.models.expense import Expense
from bot.models.material import Material
from bot.models.material_movement import MaterialMovement
from bot.models.user import User
from bot.models.packaging import Packaging
from bot.services.user_service import get_user
from .dependencies import get_db, get_current_user, role_required

router = APIRouter()
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    auto_reload=True
)

CATEGORIES = [
    ("", "Все категории"),
    ("raw_material_purchase", "Закупка сырья (опилки)"),
    ("packaging_material", "Упаковочные материалы"),
    ("fuel", "Топливо"),
    ("salary", "Зарплата"),
    ("rent", "Аренда"),
    ("electricity", "Электричество"),
    ("repair", "Ремонт/модернизация"),
    ("other", "Прочее"),
]

PAGE_SIZE = 20

def get_expense_query(category: str = None):
    """Возвращает базовый запрос с подгрузкой связей."""
    q = select(Expense).options(
        selectinload(Expense.user),
        selectinload(Expense.material),
        selectinload(Expense.employee),
        selectinload(Expense.packaging)
    ).order_by(desc(Expense.date))
    if category:
        q = q.where(Expense.category == category)
    return q

@router.get("/finance")
async def list_expenses(
    request: Request,
    category: str = "",
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Проверка прав: доступно admin, manager, operator
    if current_user.role not in ("admin", "manager", "operator"):
        raise HTTPException(status_code=403)

    offset = (page - 1) * PAGE_SIZE
    base_q = get_expense_query(category if category else None)
    count_q = select(func.count()).select_from(Expense)
    if category:
        count_q = count_q.where(Expense.category == category)
    total_count = (await db.execute(count_q)).scalar()
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

    result = await db.execute(base_q.offset(offset).limit(PAGE_SIZE))
    expenses = result.scalars().all()

    # Общая сумма расходов по текущему фильтру
    sum_q = select(func.coalesce(func.sum(Expense.amount), 0))
    if category:
        sum_q = sum_q.where(Expense.category == category)
    total_amount = (await db.execute(sum_q)).scalar()

    category_labels = {key: label for key, label in CATEGORIES}

    template = env.get_template("finance.html")
    html = template.render({
        "request": request,
        "user": current_user,
        "expenses": expenses,
        "categories": CATEGORIES,
        "current_category": category,
        "total_amount": total_amount,
        "category_labels": category_labels,
        "page": page,
        "total_pages": total_pages
    })
    return HTMLResponse(html)


@router.get("/finance/add")
async def add_expense_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager", "operator"]))
):
    materials = (await db.execute(select(Material))).scalars().all()
    users = (await db.execute(select(User))).scalars().all()
    packagings = (await db.execute(select(Packaging).limit(50))).scalars().all()  # последние 50 фасовок
    template = env.get_template("expense_add.html")
    return HTMLResponse(template.render({
        "request": request,
        "user": current_user,
        "categories": CATEGORIES[1:],  # без "Все"
        "materials": materials,
        "users": users,
        "packagings": packagings
    }))


@router.post("/finance/add")
async def add_expense_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager", "operator"])),
    amount: float = Form(...),
    purpose: str = Form(""),
    source: str = Form("собственные средства"),
    category: str = Form(...),
    material_id: int = Form(None),
    quantity: float = Form(None),
    unit: str = Form(None),
    employee_id: int = Form(None),
    packaging_id: int = Form(None),
    expense_date: str = Form(None)  # дата в виде строки
):
    # Преобразование даты
    date_obj = None
    if expense_date:
        try:
            date_obj = datetime.fromisoformat(expense_date)
        except ValueError:
            date_obj = datetime.utcnow()
    else:
        date_obj = datetime.utcnow()

    # Получаем внутреннего пользователя
    user = await get_user(db, current_user.telegram_id)

    expense = Expense(
        amount=amount,
        purpose=purpose,
        source=source,
        category=category,
        material_id=material_id,
        quantity=quantity,
        unit=unit,
        employee_id=employee_id,
        packaging_id=packaging_id,
        user_id=user.id,
        date=date_obj
    )
    db.add(expense)
    await db.commit()
    return RedirectResponse("/finance", status_code=302)


@router.get("/finance/{expense_id}/edit")
async def edit_expense_form(
    expense_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"]))
):
    expense = await db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Расход не найден")

    materials = (await db.execute(select(Material))).scalars().all()
    users = (await db.execute(select(User))).scalars().all()
    packagings = (await db.execute(select(Packaging).limit(50))).scalars().all()

    template = env.get_template("expense_edit.html")
    return HTMLResponse(template.render({
        "request": request,
        "user": current_user,
        "expense": expense,
        "categories": CATEGORIES[1:],
        "materials": materials,
        "users": users,
        "packagings": packagings
    }))


@router.post("/finance/{expense_id}/edit")
async def edit_expense_submit(
    expense_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"])),
    amount: float = Form(...),
    purpose: str = Form(""),
    source: str = Form("собственные средства"),
    category: str = Form(...),
    material_id: int = Form(None),
    quantity: float = Form(None),
    unit: str = Form(None),
    employee_id: int = Form(None),
    packaging_id: int = Form(None),
    expense_date: str = Form(None)
):
    expense = await db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404)

    # Обновление основных полей
    expense.amount = amount
    expense.purpose = purpose
    expense.source = source
    expense.category = category
    expense.material_id = material_id
    expense.quantity = quantity
    expense.unit = unit
    expense.employee_id = employee_id
    expense.packaging_id = packaging_id
    if expense_date:
        try:
            expense.date = datetime.fromisoformat(expense_date)
        except ValueError:
            pass

    # Если расход связан с закупкой материала, обновим movement
    if expense.material_id:
        # Ищем movement, который ссылается на этот expense
        stmt = select(MaterialMovement).where(MaterialMovement.expense_id == expense.id)
        result = await db.execute(stmt)
        movement = result.scalar_one_or_none()
        if movement:
            movement.quantity = quantity if quantity else movement.quantity
            movement.unit = unit if unit else movement.unit
            # Пересчёт remaining_quantity: разница между старым и новым количеством
            old_qty = movement.quantity  # уже обновили
            # Но нужно сохранить пропорцию оставшегося остатка. Упростим: если количество изменилось, скорректируем remaining.
            if quantity and old_qty:
                old_remaining = movement.remaining_quantity
                movement.remaining_quantity = max(0, old_remaining + (quantity - old_qty))
            # Обновим цену за единицу в movement, если она была
            if quantity and quantity > 0:
                movement.unit_price = amount / quantity
            # unit не меняем, если передали

    await db.commit()
    return RedirectResponse("/finance", status_code=302)


@router.post("/finance/{expense_id}/delete")
async def delete_expense(
    expense_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin", "manager"]))
):
    expense = await db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404)

    # Если расход связан с закупкой материала, удалим и движение
    if expense.material_id:
        movement = (await db.execute(
            select(MaterialMovement).where(MaterialMovement.expense_id == expense.id)
        )).scalar_one_or_none()
        if movement:
            # Проверим, что movement не был использован (остаток равен исходному)
            if movement.remaining_quantity < movement.quantity:
                # Частично использован – запретим удаление
                return RedirectResponse(f"/finance/{expense_id}/edit?error=partially_used", status_code=302)
            await db.delete(movement)

    await db.delete(expense)
    await db.commit()
    return RedirectResponse("/finance", status_code=302)