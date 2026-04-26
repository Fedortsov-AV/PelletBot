import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from jinja2 import Environment, FileSystemLoader
import bcrypt
from datetime import datetime, date

from bot.models.user import User
from bot.services.db_service import DBService
from bot.services.auth import get_all_users
from bot.services.storage import update_stock_arrival   # если понадобится
from .dependencies import get_db, get_current_user, role_required

router = APIRouter()
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    auto_reload=True
)

def convert_value(value: str, field_type: str):
    """Конвертирует строку в подходящий Python-тип на основе типа колонки."""
    if value is None or value == "":
        return None
    t = field_type.upper()
    if "INT" in t:
        return int(value)
    elif "FLOAT" in t or "NUMERIC" in t or "REAL" in t:
        return float(value)
    elif "BOOLEAN" in t:
        return value.lower() in ("1", "true", "yes")
    elif "DATETIME" in t or "DATE" in t:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            return None
    else:
        return value

def format_value(value, field_type):
    """Форматирует значение для отображения в форме редактирования."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        if "DATE" in field_type.upper() and "DATETIME" not in field_type.upper():
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%dT%H:%M")
    elif isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)

# Все роли, доступные для выбора в формах
AVAILABLE_ROLES = ["admin", "manager", "operator", "anonymous"]
PAGE_SIZE = 20


# ================== ГЛАВНАЯ АДМИНКИ ==================
@router.get("/admin")
async def admin_home(request: Request, current_user=Depends(role_required(["admin"]))):
    template = env.get_template("admin.html")
    return HTMLResponse(template.render({"request": request, "user": current_user}))


# ================== ПОЛЬЗОВАТЕЛИ ==================
@router.get("/admin/users")
async def users_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"])),
    page: int = 1
):
    offset = (page - 1) * PAGE_SIZE
    total = (await db.execute(select(func.count(User.id)))).scalar()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    result = await db.execute(
        select(User).order_by(User.id).offset(offset).limit(PAGE_SIZE)
    )
    users = result.scalars().all()

    template = env.get_template("admin_users.html")
    return HTMLResponse(template.render(
        request=request, user=current_user,
        users=users, page=page, total_pages=total_pages
    ))


@router.get("/admin/users/add")
async def add_user_form(request: Request, current_user=Depends(role_required(["admin"]))):
    template = env.get_template("admin_user_add.html")
    return HTMLResponse(template.render(
        request=request, user=current_user, roles=AVAILABLE_ROLES
    ))


@router.post("/admin/users/add")
async def add_user_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"])),
    telegram_id: int = Form(...),
    full_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    if role not in AVAILABLE_ROLES:
        return RedirectResponse("/admin/users/add?error=invalid_role", 302)
    # Проверим уникальность telegram_id и username
    exists = (await db.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
    if exists:
        return RedirectResponse("/admin/users/add?error=telegram_exists", 302)
    exists = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if exists:
        return RedirectResponse("/admin/users/add?error=username_exists", 302)

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        username=username,
        hashed_password=hashed,
        role=role
    )
    db.add(new_user)
    await db.commit()
    return RedirectResponse("/admin/users", 302)


@router.get("/admin/users/{user_id}/edit")
async def edit_user_form(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"]))
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    template = env.get_template("admin_user_edit.html")
    return HTMLResponse(template.render(
        request=request, user=current_user,
        edited_user=user, roles=AVAILABLE_ROLES
    ))


@router.post("/admin/users/{user_id}/edit")
async def edit_user_submit(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"])),
    telegram_id: int = Form(...),
    full_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(""),
    role: str = Form(...)
):
    if role not in AVAILABLE_ROLES:
        return RedirectResponse(f"/admin/users/{user_id}/edit?error=invalid_role", 302)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    # Проверка уникальности telegram_id, если изменён
    if telegram_id != user.telegram_id:
        exist = (await db.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
        if exist:
            return RedirectResponse(f"/admin/users/{user_id}/edit?error=telegram_exists", 302)
    # Проверка уникальности username
    if username != user.username:
        exist = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if exist:
            return RedirectResponse(f"/admin/users/{user_id}/edit?error=username_exists", 302)

    user.telegram_id = telegram_id
    user.full_name = full_name
    user.username = username
    user.role = role
    if password.strip():
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.hashed_password = hashed
    await db.commit()
    return RedirectResponse("/admin/users", 302)


@router.post("/admin/users/{user_id}/delete")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"]))
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404)
    if user.telegram_id == current_user.telegram_id:
        return RedirectResponse("/admin/users?error=cannot_delete_self", 302)
    await db.delete(user)
    await db.commit()
    return RedirectResponse("/admin/users", 302)


# ================== УПРАВЛЕНИЕ ТАБЛИЦАМИ БД ==================
@router.get("/admin/tables")
async def tables_list(request: Request, current_user=Depends(role_required(["admin"]))):
    tables = list(DBService.MODELS.keys())
    template = env.get_template("admin_tables.html")
    return HTMLResponse(template.render(request=request, user=current_user, tables=tables))


@router.get("/admin/tables/{table_name}")
async def view_table(
    table_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"])),
    page: int = 1
):
    if table_name not in DBService.MODELS:
        raise HTTPException(404, "Таблица не найдена")
    model = DBService.MODELS[table_name]
    offset = (page - 1) * PAGE_SIZE
    total = (await db.execute(select(func.count(model.id)))).scalar()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    result = await db.execute(
        select(model).order_by(desc(model.id)).offset(offset).limit(PAGE_SIZE)
    )
    records = result.scalars().all()

    # Получаем названия колонок
    columns = [col.name for col in model.__table__.columns]

    template = env.get_template("admin_table_view.html")
    return HTMLResponse(template.render(
        request=request, user=current_user,
        table_name=table_name, records=records,
        columns=columns, page=page, total_pages=total_pages
    ))


@router.get("/admin/tables/{table_name}/add")
async def add_record_form(
    table_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"]))
):
    if table_name not in DBService.MODELS:
        raise HTTPException(404, "Таблица не найдена")
    model = DBService.MODELS[table_name]
    fields_info = DBService.get_model_fields(model)
    field_list = [{"name": name, "type": props["type"]} for name, props in fields_info.items() if name != "id"]
    template = env.get_template("admin_record_add.html")
    return HTMLResponse(template.render(
        request=request, user=current_user,
        table_name=table_name, fields=field_list
    ))


@router.post("/admin/tables/{table_name}/add")
async def add_record_submit(
    table_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"]))
):
    if table_name not in DBService.MODELS:
        raise HTTPException(404)
    model = DBService.MODELS[table_name]
    form = await request.form()
    # Собираем данные, конвертируя типы по возможности
    data = {}
    fields = DBService.get_model_fields(model)
    for field_name in form.keys():
        if field_name not in fields or field_name == "id":
            continue
        field_type = fields[field_name]["type"]
        raw = form[field_name]
        value = convert_value(raw, field_type)
        data[field_name] = value
    try:
        await DBService.add_record(db, model, data)
    except Exception as e:
        return RedirectResponse(f"/admin/tables/{table_name}/add?error={str(e)}", 302)
    return RedirectResponse(f"/admin/tables/{table_name}", 302)


@router.get("/admin/tables/{table_name}/{record_id}/edit")
async def edit_record_form(
    table_name: str,
    record_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"]))
):
    if table_name not in DBService.MODELS:
        raise HTTPException(404)
    model = DBService.MODELS[table_name]
    record = await db.get(model, record_id)
    if not record:
        raise HTTPException(404, "Запись не найдена")
    fields_info = DBService.get_model_fields(model)
    field_list = [{"name": name, "type": props["type"]} for name, props in fields_info.items() if name != "id"]
    formatted_values = {}
    for name, props in fields_info.items():
        if name == "id":
            continue
        raw = getattr(record, name)
        formatted_values[name] = format_value(raw, props["type"])
    template = env.get_template("admin_record_edit.html")
    return HTMLResponse(template.render(
        request=request, user=current_user,
        table_name=table_name, record_id=record_id,
        fields=field_list, values=formatted_values
    ))


@router.post("/admin/tables/{table_name}/{record_id}/edit")
async def edit_record_submit(
    table_name: str,
    record_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"]))
):
    if table_name not in DBService.MODELS:
        raise HTTPException(404)
    model = DBService.MODELS[table_name]
    record = await db.get(model, record_id)
    if not record:
        raise HTTPException(404)
    form = await request.form()
    data = {}
    fields = DBService.get_model_fields(model)
    for field_name in form.keys():
        if field_name not in fields or field_name == "id":
            continue
        field_type = fields[field_name]["type"]
        raw = form[field_name]
        value = convert_value(raw, field_type)
        data[field_name] = value
    try:
        await DBService.update_record(db, model, record_id, data)
    except Exception as e:
        return RedirectResponse(f"/admin/tables/{table_name}/{record_id}/edit?error={str(e)}", 302)
    return RedirectResponse(f"/admin/tables/{table_name}", 302)


@router.post("/admin/tables/{table_name}/{record_id}/delete")
async def delete_record(
    table_name: str,
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_required(["admin"]))
):
    if table_name not in DBService.MODELS:
        raise HTTPException(404)
    model = DBService.MODELS[table_name]
    await DBService.delete_record(db, model, record_id)
    return RedirectResponse(f"/admin/tables/{table_name}", 302)