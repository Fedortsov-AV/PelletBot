import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

from bot.models import ProductStorage
from bot.models.shipment import Shipment, ShipmentItem
from bot.models.product import Product
from bot.models.user import User
from bot.services.shipment import get_available_products  # для формы добавления
from .dependencies import get_db, get_current_user

router = APIRouter()
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    auto_reload=True
)

PAGE_SIZE = 15


# ====================== СПИСОК ОТГРУЗОК ======================
@router.get("/shipments")
async def list_shipments(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    offset = (page - 1) * PAGE_SIZE
    total_count = (await db.execute(select(func.count(Shipment.id)))).scalar()
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

    # Загружаем отгрузки с пользователем и элементами
    result = await db.execute(
        select(Shipment)
        .options(
            selectinload(Shipment.user),
            selectinload(Shipment.shipment_items).selectinload(ShipmentItem.product)
        )
        .order_by(desc(Shipment.timestamp))
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    shipments = result.scalars().all()

    template = env.get_template("shipments.html")
    html = template.render({
        "request": request,
        "user": current_user,
        "shipments": shipments,
        "page": page,
        "total_pages": total_pages,
        "total_count": total_count
    })
    return HTMLResponse(html)


@router.get("/shipments/add")
async def add_shipment_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    available = await get_available_products(db)  # возвращает список кортежей (Product, int)
    template = env.get_template("shipment_add.html")
    html = template.render({
        "request": request,
        "user": current_user,
        "available_products": available
    })
    return HTMLResponse(html)


# ====================== ДОБАВЛЕНИЕ ОТГРУЗКИ ======================
@router.post("/shipments/add")
async def add_shipment_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

    # Получаем данные формы: список product_id и quantity из мульти-полей
    form = await request.form()
    product_ids = form.getlist("product_id")
    quantities = form.getlist("quantity")

    if not product_ids or not quantities or len(product_ids) != len(quantities):
        return RedirectResponse(url="/shipments/add?error=invalid", status_code=302)

    items = []
    for pid_str, qty_str in zip(product_ids, quantities):
        try:
            pid = int(pid_str)
            qty = int(qty_str)
            if qty <= 0:
                continue
            items.append({"product_id": pid, "quantity": qty})
        except ValueError:
            continue

    if not items:
        return RedirectResponse(url="/shipments/add?error=no_items", status_code=302)

    try:
        # Проверяем наличие на складе и создаём отгрузку
        # Найдём пользователя по telegram_id
        user_result = await db.execute(select(User).where(User.telegram_id == current_user.telegram_id))
        user = user_result.scalar_one()

        # Создаём отгрузку
        shipment = Shipment(user_id=user.id, timestamp=datetime.utcnow())
        db.add(shipment)
        await db.flush()  # получаем shipment.id

        for item in items:
            product = await db.get(Product, item["product_id"])
            if not product:
                raise HTTPException(status_code=400, detail=f"Продукт с id {item['product_id']} не найден")

            # Проверяем остаток
            storage = await db.get(ProductStorage, item["product_id"])
            if not storage or storage.amount < item["quantity"]:
                raise HTTPException(status_code=400, detail=f"Недостаточно товара '{product.name}' на складе")

            # Создаём элемент отгрузки
            shipment_item = ShipmentItem(
                shipment_id=shipment.id,
                product_id=item["product_id"],
                quantity=item["quantity"]
            )
            db.add(shipment_item)

            # Списываем со склада
            storage.amount -= item["quantity"]

        await db.commit()
        return RedirectResponse(url="/shipments", status_code=302)

    except HTTPException as e:
        await db.rollback()
        # Можно добавить flash-сообщение, но для простоты редиректим с ошибкой
        return RedirectResponse(url=f"/shipments/add?error={e.detail}", status_code=302)
    except Exception as e:
        await db.rollback()
        return RedirectResponse(url="/shipments/add?error=unknown", status_code=302)


# ====================== ДЕТАЛИ ОТГРУЗКИ ======================
@router.get("/shipments/{shipment_id}")
async def shipment_detail(
    shipment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(
        select(Shipment)
        .options(
            selectinload(Shipment.user),
            selectinload(Shipment.shipment_items).selectinload(ShipmentItem.product)
        )
        .where(Shipment.id == shipment_id)
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Отгрузка не найдена")

    template = env.get_template("shipment_detail.html")
    html = template.render({
        "request": request,
        "user": current_user,
        "shipment": shipment
    })
    return HTMLResponse(html)


# ====================== УДАЛЕНИЕ ОТГРУЗКИ ======================
@router.post("/shipments/{shipment_id}/delete")
async def delete_shipment(
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

    shipment = await db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Отгрузка не найдена")

    # Загружаем элементы явно
    items_result = await db.execute(
        select(ShipmentItem).where(ShipmentItem.shipment_id == shipment_id)
    )
    items = items_result.scalars().all()

    # Возвращаем товары на склад
    for item in items:
        storage = await db.get(ProductStorage, item.product_id)
        if storage:
            storage.amount += item.quantity
        # Удаляем сам элемент отгрузки
        await db.delete(item)

    # Теперь спокойно удаляем отгрузку (связанных элементов уже нет)
    await db.delete(shipment)
    await db.commit()

    return RedirectResponse(url="/shipments", status_code=302)

# ====================== РЕДАКТИРОВАНИЕ ОТГРУЗКИ ======================
@router.get("/shipments/{shipment_id}/edit")
async def edit_shipment_form(
    shipment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

    # Загружаем отгрузку с элементами и продуктами
    result = await db.execute(
        select(Shipment)
        .options(
            selectinload(Shipment.shipment_items).selectinload(ShipmentItem.product)
        )
        .where(Shipment.id == shipment_id)
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Отгрузка не найдена")

    # Доступные продукты (для добавления новых)
    available = await get_available_products(db)
    available_list = [{"id": p.id, "name": p.name, "amount": amt} for p, amt in available]

    # Текущие элементы отгрузки в удобном виде
    existing_items = []
    for item in shipment.shipment_items:
        existing_items.append({
            "product_id": item.product.id,
            "product_name": item.product.name,
            "quantity": item.quantity,
            "shipment_item_id": item.id
        })

    template = env.get_template("shipment_edit.html")
    html = template.render({
        "request": request,
        "user": current_user,
        "shipment": shipment,
        "available_products": available_list,
        "existing_items": existing_items
    })
    return HTMLResponse(html)


@router.post("/shipments/{shipment_id}/edit")
async def edit_shipment_submit(
    shipment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

    # Получаем данные формы
    form = await request.form()
    try:
        new_timestamp_str = form.get("timestamp")  # строка, например "2026-04-26T10:30"
        new_timestamp = datetime.fromisoformat(new_timestamp_str)
    except (ValueError, TypeError):
        return RedirectResponse(url=f"/shipments/{shipment_id}/edit?error=invalid_date", status_code=302)

    # Идентификаторы существующих элементов (скрытые поля) и новые строки
    existing_item_ids = form.getlist("existing_item_id")  # только для существующих записей
    quantities = form.getlist("quantity")                 # количество для каждой строки
    new_product_ids = form.getlist("new_product_id")      # для новых строк
    new_quantities = form.getlist("new_quantity")

    # Загружаем отгрузку
    shipment = await db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Отгрузка не найдена")

    # Загружаем существующие элементы
    stmt = select(ShipmentItem).where(ShipmentItem.shipment_id == shipment_id)
    result = await db.execute(stmt)
    old_items = {item.id: item for item in result.scalars().all()}

    # Строим словарь изменений: product_id -> (старое количество, новое количество)
    changes = {}  # product_id: delta (новое - старое)

    # Обработка существующих элементов: либо изменённое количество, либо удаление
    processed_ids = set()
    for item_id_str, qty_str in zip(existing_item_ids, quantities):
        try:
            item_id = int(item_id_str)
            qty = int(qty_str)
            if qty <= 0:
                continue  # удалим этот элемент позже
        except ValueError:
            continue

        old_item = old_items.get(item_id)
        if not old_item:
            continue

        processed_ids.add(item_id)
        old_qty = old_item.quantity
        if qty != old_qty:
            # Разница: новое - старое
            delta = qty - old_qty
            changes[old_item.product_id] = changes.get(old_item.product_id, 0) + delta
            # Обновляем количество в элементе
            old_item.quantity = qty

    # Удаление элементов, которые не пришли в форме (были удалены пользователем)
    for item_id, old_item in old_items.items():
        if item_id not in processed_ids:
            # Возвращаем товар на склад
            changes[old_item.product_id] = changes.get(old_item.product_id, 0) - old_item.quantity
            await db.delete(old_item)

    # Обработка новых добавленных строк
    for pid_str, qty_str in zip(new_product_ids, new_quantities):
        try:
            pid = int(pid_str)
            qty = int(qty_str)
            if pid <= 0 or qty <= 0:
                continue
        except ValueError:
            continue

        # Проверяем существование продукта
        product = await db.get(Product, pid)
        if not product:
            return RedirectResponse(url=f"/shipments/{shipment_id}/edit?error=product_not_found", status_code=302)

        # Создаём новый элемент отгрузки
        new_item = ShipmentItem(shipment_id=shipment_id, product_id=pid, quantity=qty)
        db.add(new_item)
        changes[pid] = changes.get(pid, 0) + qty

    # Применяем изменения к складу
    try:
        for product_id, delta in changes.items():
            if delta == 0:
                continue
            storage = await db.get(ProductStorage, product_id)
            if not storage:
                raise HTTPException(status_code=400, detail=f"Складская запись для продукта {product_id} не найдена")
            if storage.amount - delta < 0:
                raise HTTPException(status_code=400, detail=f"Недостаточно продукта на складе (product_id={product_id})")
            storage.amount -= delta

        # Обновляем дату отгрузки
        shipment.timestamp = new_timestamp
        await db.commit()
        return RedirectResponse(url=f"/shipments/{shipment_id}", status_code=302)

    except HTTPException as e:
        await db.rollback()
        return RedirectResponse(url=f"/shipments/{shipment_id}/edit?error={e.detail}", status_code=302)
    except Exception as e:
        await db.rollback()
        return RedirectResponse(url="/shipments", status_code=302)