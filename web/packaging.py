import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

from bot.models import RawMaterialStorage, ProductStorage
from bot.models.packaging import Packaging
from bot.models.rawProduct import RawProduct
from bot.models.product import Product
from bot.services.packaging_service import (
    get_raw_materials,
    get_products_for_raw_material,
    save_packaging,
    update_stock_after_packaging,
    get_raw_material_availability,
)
from bot.services.user_service import get_user
from .dependencies import get_db, get_current_user, role_required

router = APIRouter()
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    auto_reload=True,
)

PAGE_SIZE = 15


@router.get("/packaging")
async def list_packaging(
        request: Request,
        page: int = 1,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """Отображение списка фасовок с пагинацией."""
    offset = (page - 1) * PAGE_SIZE

    # Общее количество записей
    total_count = (await db.execute(select(func.count(Packaging.id)))).scalar()
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

    # Загружаем фасовки с подгрузкой связанных объектов
    result = await db.execute(
        select(Packaging)
        .options(
            selectinload(Packaging.user),
            selectinload(Packaging.raw_product),
            selectinload(Packaging.product),
        )
        .order_by(desc(Packaging.date))
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    packagings = result.scalars().all()

    template = env.get_template("packaging.html")
    html = template.render({
        "request": request,
        "user": current_user,
        "packagings": packagings,
        "page": page,
        "total_pages": total_pages,
        "total_count": total_count,
    })
    return HTMLResponse(html)


@router.get("/packaging/add")
async def add_packaging_form(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """Форма добавления фасовки."""
    if current_user.role not in ("admin", "manager", "operator"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    # Получаем список сырья с остатками
    raw_materials = await get_raw_materials(db)  # список кортежей (RawProduct, amount)

    template = env.get_template("packaging_add.html")
    html = template.render({
        "request": request,
        "user": current_user,
        "raw_materials": raw_materials,
    })
    return HTMLResponse(html)


@router.get("/api/products-for-raw/{raw_product_id}")
async def get_products_for_raw(
        raw_product_id: int,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """API: получить продукты для выбранного сырья (для динамического обновления формы)."""
    products = await get_products_for_raw_material(db, raw_product_id)
    # products – список кортежей (Product, stock_amount)
    data = [{"id": p.id, "name": p.name, "weight": p.weight, "stock": amt} for p, amt in products]
    return data


@router.post("/packaging/add")
async def add_packaging_submit(
        request: Request,
        raw_product_id: int = Form(...),
        product_id: int = Form(...),
        amount: int = Form(...),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user),
):
    """Обработка формы добавления фасовки."""
    if current_user.role not in ("admin", "manager", "operator"):
        raise HTTPException(status_code=403)

    # Получаем продукт для вычислений
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")

    required_raw = amount * product.weight

    # Проверяем доступность сырья
    _, is_available, max_packs = await get_raw_material_availability(
        db,
        raw_product_id,
        product_weight=product.weight,
        required_amount=required_raw,
    )

    if not is_available:
        # В реальном приложении лучше вернуть ошибку на ту же страницу,
        # но для первого шага просто редиректим с сообщением (можно улучшить через Flash-сообщения)
        return RedirectResponse(url="/packaging/add?error=insufficient_raw", status_code=302)

    # Сохраняем фасовку и обновляем склад
    user = await get_user(db, current_user.telegram_id)
    await save_packaging(
        db,
        user.id,
        product.id,
        raw_product_id,
        amount,
        required_raw,
    )
    await update_stock_after_packaging(
        db,
        product.id,
        raw_product_id,
        amount,
        required_raw,
    )

    return RedirectResponse(url="/packaging", status_code=302)

# =========== РЕДАКТИРОВАНИЕ ФАСОВКИ ===========
@router.get("/packaging/{packaging_id}/edit")
async def edit_packaging_form(
    packaging_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Форма редактирования фасовки (только количество)."""
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

    # Загружаем фасовку с подгрузкой связанных данных для отображения
    result = await db.execute(
        select(Packaging)
        .options(
            selectinload(Packaging.raw_product),
            selectinload(Packaging.product),
            selectinload(Packaging.user)
        )
        .where(Packaging.id == packaging_id)
    )
    packaging = result.scalar_one_or_none()
    if not packaging:
        raise HTTPException(status_code=404, detail="Фасовка не найдена")

    template = env.get_template("packaging_edit.html")
    return HTMLResponse(template.render({
        "request": request,
        "user": current_user,
        "packaging": packaging
    }))


@router.post("/packaging/{packaging_id}/edit")
async def edit_packaging_submit(
    packaging_id: int,
    amount: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Обработка редактирования фасовки."""
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

    # Получаем оригинальную запись
    packaging = await db.get(Packaging, packaging_id)
    if not packaging:
        raise HTTPException(status_code=404, detail="Фасовка не найдена")

    old_amount = packaging.amount
    old_used_raw = packaging.used_raw_material
    new_amount = amount

    # Получаем продукт и его вес
    product = await db.get(Product, packaging.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")

    new_used_raw = new_amount * product.weight
    delta_product = new_amount - old_amount
    delta_raw = old_used_raw - new_used_raw   # обратная логика: было потрачено X, стало Y, склад сырья изменится на (старый - новый)

    # Проверяем, не превышает ли новое количество доступное сырьё
    # Получаем текущий остаток сырья
    raw_stock = (await db.execute(
        select(RawMaterialStorage).where(RawMaterialStorage.raw_product_id == packaging.raw_product_id)
    )).scalar_one()
    # После изменения остаток не должен стать отрицательным
    if raw_stock.amount + delta_raw < 0:   # delta_raw положительно, когда мы уменьшаем расход сырья
        # Перенаправление с ошибкой (для простоты)
        return RedirectResponse(url=f"/packaging/{packaging_id}/edit?error=insufficient_raw", status_code=302)

    # Обновляем запись фасовки
    packaging.amount = new_amount
    packaging.used_raw_material = new_used_raw

    # Обновляем склады
    # Изменение запаса продукции: дельта может быть положительной или отрицательной
    product_stock = (await db.execute(
        select(ProductStorage).where(ProductStorage.product_id == packaging.product_id)
    )).scalar_one()
    product_stock.amount += delta_product   # если увеличили количество пачек, продукции становится больше

    raw_stock.amount += delta_raw   # если увеличили расход сырья, сырья становится меньше (но мы проверили)

    await db.commit()

    return RedirectResponse(url="/packaging", status_code=302)

# =========== УДАЛЕНИЕ ФАСОВКИ ===========
@router.post("/packaging/{packaging_id}/delete")
async def delete_packaging_handler(
    packaging_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Удаление фасовки с корректировкой склада."""
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

    packaging = await db.get(Packaging, packaging_id)
    if not packaging:
        raise HTTPException(status_code=404, detail="Фасовка не найдена")

    # Возвращаем сырьё на склад
    raw_stock = (await db.execute(
        select(RawMaterialStorage).where(RawMaterialStorage.raw_product_id == packaging.raw_product_id)
    )).scalar_one_or_none()
    if raw_stock:
        raw_stock.amount += packaging.used_raw_material

    # Убираем продукцию со склада
    product_stock = (await db.execute(
        select(ProductStorage).where(ProductStorage.product_id == packaging.product_id)
    )).scalar_one_or_none()
    if product_stock:
        product_stock.amount -= packaging.amount
        if product_stock.amount < 0:
            product_stock.amount = 0  # на всякий случай

    # Удаляем запись фасовки
    await db.delete(packaging)
    await db.commit()

    return RedirectResponse(url="/packaging", status_code=302)