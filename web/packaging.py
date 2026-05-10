import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

from bot.models import RawMaterialStorage, ProductStorage, Material
from bot.models.packaging import Packaging, PackagingMaterial
from bot.models.material_movement import MaterialMovement
from bot.models.rawProduct import RawProduct
from bot.models.product import Product
from bot.services.material_service import consume_material, return_material
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

# ------------------- СПИСОК ФАСОВОК -------------------
@router.get("/packaging")
async def list_packaging(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    offset = (page - 1) * PAGE_SIZE
    total_count = (await db.execute(select(func.count(Packaging.id)))).scalar()
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

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
    return HTMLResponse(template.render({
        "request": request,
        "user": current_user,
        "packagings": packagings,
        "page": page,
        "total_pages": total_pages,
        "total_count": total_count,
    }))


# ------------------- ФОРМА ДОБАВЛЕНИЯ -------------------
@router.get("/packaging/add")
async def add_packaging_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in ("admin", "manager", "operator"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    raw_materials = await get_raw_materials(db)
    materials_result = await db.execute(
        select(Material).where(Material.name != "Наклейка")
    )
    materials = materials_result.scalars().all()

    template = env.get_template("packaging_add.html")
    return HTMLResponse(template.render({
        "request": request,
        "user": current_user,
        "raw_materials": raw_materials,
        "materials": materials,
    }))


# ------------------- API ДЛЯ ПРОДУКТОВ -------------------
@router.get("/api/products-for-raw/{raw_product_id}")
async def get_products_for_raw(
    raw_product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    products = await get_products_for_raw_material(db, raw_product_id)
    return [{"id": p.id, "name": p.name, "weight": p.weight, "stock": amt} for p, amt in products]


# ------------------- СОХРАНЕНИЕ НОВОЙ ФАСОВКИ -------------------
@router.post("/packaging/add")
async def add_packaging_submit(
    request: Request,
    raw_product_id: int = Form(...),
    product_id: int = Form(...),
    amount: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in ("admin", "manager", "operator"):
        raise HTTPException(status_code=403)

    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")

    required_raw = amount * product.weight
    _, is_available, _ = await get_raw_material_availability(
        db, raw_product_id, product_weight=product.weight, required_amount=required_raw
    )
    if not is_available:
        return RedirectResponse(url="/packaging/add?error=insufficient_raw", status_code=302)

    user = await get_user(db, current_user.telegram_id)
    packaging = await save_packaging(db, user.id, product.id, raw_product_id, amount, required_raw)
    await update_stock_after_packaging(db, product.id, raw_product_id, amount, required_raw)

    # Списание материалов
    form = await request.form()
    material_ids = form.getlist("material_id")
    material_quantities = form.getlist("material_quantity")
    total_material_cost = 0.0

    # Наклейки автоматически
    sticker = (await db.execute(select(Material).where(Material.name == "Наклейка"))).scalar_one_or_none()
    if sticker:
        try:
            cost_stickers = await consume_material(db, sticker.id, amount, packaging.id)
            total_material_cost += cost_stickers
        except ValueError:
            pass  # недостаточно наклеек — игнорируем (можно добавить обработку)

    # Остальные материалы
    for mat_id_str, qty_str in zip(material_ids, material_quantities):
        if not mat_id_str or not qty_str:
            continue
        try:
            mat_id = int(mat_id_str)
            qty = float(qty_str)
            if qty <= 0:
                continue
            cost_mat = await consume_material(db, mat_id, qty, packaging.id)
            total_material_cost += cost_mat
        except ValueError:
            continue

    packaging.total_material_cost = total_material_cost
    await db.commit()

    return RedirectResponse(url="/packaging", status_code=302)


# ------------------- РЕДАКТИРОВАНИЕ ФАСОВКИ -------------------
@router.get("/packaging/{packaging_id}/edit")
async def edit_packaging_form(
    packaging_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

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
    return HTMLResponse(template.render({"request": request, "user": current_user, "packaging": packaging}))


@router.post("/packaging/{packaging_id}/edit")
async def edit_packaging_submit(
    packaging_id: int,
    amount: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

    packaging = await db.get(Packaging, packaging_id)
    if not packaging:
        raise HTTPException(status_code=404, detail="Фасовка не найдена")

    old_amount = packaging.amount
    old_used_raw = packaging.used_raw_material
    new_amount = amount

    product = await db.get(Product, packaging.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")

    new_used_raw = new_amount * product.weight
    delta_product = new_amount - old_amount
    delta_raw = old_used_raw - new_used_raw

    # Проверка сырья
    raw_stock = (await db.execute(
        select(RawMaterialStorage).where(RawMaterialStorage.raw_product_id == packaging.raw_product_id)
    )).scalar_one()
    if raw_stock.amount + delta_raw < 0:
        return RedirectResponse(url=f"/packaging/{packaging_id}/edit?error=insufficient_raw", status_code=302)

    # === Откат старых материалов (возврат на склад) ===
    old_materials = (await db.execute(
        select(PackagingMaterial).where(PackagingMaterial.packaging_id == packaging_id)
    )).scalars().all()

    for pm in old_materials:
        unit_price = pm.cost / pm.quantity if pm.quantity > 0 else 0.0
        await return_material(db, pm.material_id, pm.quantity, pm.unit, unit_price, packaging_id)
        await db.delete(pm)

    # === Новое списание материалов ===
    total_material_cost = 0.0
    sticker = (await db.execute(select(Material).where(Material.name == "Наклейка"))).scalar_one_or_none()
    if sticker:
        try:
            cost_stickers = await consume_material(db, sticker.id, new_amount, packaging_id)
            total_material_cost += cost_stickers
        except ValueError:
            pass

    # Для других материалов (рукав, пакеты) мы берём их из старого набора, но с новым количеством пачек.
    # Поскольку мы не можем восстановить выбор пользователя, используем те же material_id, что были в old_materials,
    # исключая наклейку (уже обработана). Количество рассчитываем как old_quantity * (new_amount / old_amount), если old_amount >0.
    if old_amount > 0:
        ratio = new_amount / old_amount
        for pm in old_materials:
            if pm.material_id == sticker.id if sticker else -1:
                continue
            new_qty = round(pm.quantity * ratio, 2)
            if new_qty > 0:
                try:
                    cost_mat = await consume_material(db, pm.material_id, new_qty, packaging_id)
                    total_material_cost += cost_mat
                except ValueError:
                    pass

    # Обновление складов сырья/продукции
    packaging.amount = new_amount
    packaging.used_raw_material = new_used_raw
    packaging.total_material_cost = total_material_cost

    product_stock = (await db.execute(
        select(ProductStorage).where(ProductStorage.product_id == packaging.product_id)
    )).scalar_one()
    product_stock.amount += delta_product
    raw_stock.amount += delta_raw

    await db.commit()
    return RedirectResponse(url="/packaging", status_code=302)


# ------------------- УДАЛЕНИЕ ФАСОВКИ -------------------
@router.post("/packaging/{packaging_id}/delete")
async def delete_packaging_handler(
    packaging_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403)

    packaging = await db.get(Packaging, packaging_id)
    if not packaging:
        raise HTTPException(status_code=404, detail="Фасовка не найдена")

    # Возврат сырья
    raw_stock = (await db.execute(
        select(RawMaterialStorage).where(RawMaterialStorage.raw_product_id == packaging.raw_product_id)
    )).scalar_one_or_none()
    if raw_stock:
        raw_stock.amount += packaging.used_raw_material

    # Возврат продукции
    product_stock = (await db.execute(
        select(ProductStorage).where(ProductStorage.product_id == packaging.product_id)
    )).scalar_one_or_none()
    if product_stock:
        product_stock.amount -= packaging.amount
        if product_stock.amount < 0:
            product_stock.amount = 0

    # Возврат материалов на склад
    old_materials = (await db.execute(
        select(PackagingMaterial).where(PackagingMaterial.packaging_id == packaging_id)
    )).scalars().all()

    for pm in old_materials:
        unit_price = pm.cost / pm.quantity if pm.quantity > 0 else 0.0
        await return_material(db, pm.material_id, pm.quantity, pm.unit, unit_price, packaging_id)
        await db.delete(pm)

    # Удаление фасовки
    await db.delete(packaging)
    await db.commit()

    return RedirectResponse(url="/packaging", status_code=302)

# ------------------- ДЕТАЛЬНЫЙ ПРОСМОТР ФАСОВКИ -------------------
@router.get("/packaging/{packaging_id}")
async def view_packaging(
    packaging_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(
        select(Packaging)
        .options(
            selectinload(Packaging.user),
            selectinload(Packaging.raw_product),
            selectinload(Packaging.product),
            selectinload(Packaging.packaging_materials).selectinload(PackagingMaterial.material)
        )
        .where(Packaging.id == packaging_id)
    )
    packaging = result.scalar_one_or_none()
    if not packaging:
        raise HTTPException(status_code=404, detail="Фасовка не найдена")

    template = env.get_template("packaging_detail.html")
    return HTMLResponse(template.render({
        "request": request,
        "user": current_user,
        "packaging": packaging
    }))