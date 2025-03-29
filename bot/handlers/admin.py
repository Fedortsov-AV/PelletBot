from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin import get_admin_menu
from bot.keyboards.users import get_user_list_keyboard
from bot.keyboards.roles import get_role_selection_keyboard
from bot.services.auth import get_user_role, update_user_role, get_all_users
from bot.services.role_service import get_all_roles

router = Router()


@router.message(Command("admin"))
async def admin_panel(message: types.Message, session: AsyncSession):
    """ Открывает панель администратора. """
    role = await get_user_role(session, message.from_user.id)

    if role != "admin":
        await message.answer("❌ У вас нет прав для доступа в админ-панель.")
        return

    await message.answer("🔧 Панель администратора", reply_markup=get_admin_menu())


@router.message(F.text == "🔧 Панель администратора")
async def admin_panel(message: types.Message, session: AsyncSession):
    role = await get_user_role(session, message.from_user.id)

    if role != "admin":
        await message.answer("❌ У вас нет прав для доступа в админ-панель.")
        return

    await message.answer("🔧 Панель администратора", reply_markup=get_admin_menu())

@router.callback_query(F.data == "admin_users_list")
async def show_users(callback: CallbackQuery, session: AsyncSession):
    """ Отображает список пользователей. """
    users = await get_all_users(session)

    if not users:
        await callback.message.answer("📭 В базе данных пока нет пользователей.")
        return

    for user in users:
        await callback.message.answer(
            f"👤 {user.full_name} (ID: {user.telegram_id})\nРоль: {user.role}",
            reply_markup=get_user_list_keyboard(user.telegram_id)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("change_role:"))
async def ask_for_role_selection(callback: CallbackQuery, session: AsyncSession):
    """ Запрашивает новую роль у администратора. """
    user_id = int(callback.data.split(":")[1])

    # Получаем список ролей из базы данных
    roles = await get_all_roles(session)

    # Генерируем клавиатуру с ролями
    role_buttons = [types.InlineKeyboardButton(text=role.name, callback_data=f"set_role:{user_id}:{role.name}") for role in roles]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[role_buttons])

    await callback.message.answer(
        f"🔄 На какую роль изменить пользователя {user_id}?",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_role:"))
async def set_user_role(callback: CallbackQuery, session: AsyncSession):
    """ Меняет роль пользователя в БД. """
    _, user_id, role = callback.data.split(":")
    user_id = int(user_id)

    success = await update_user_role(session, user_id, role)

    if success:
        await callback.message.answer(f"✅ Роль пользователя {user_id} изменена на `{role}`.", parse_mode="Markdown")
    else:
        await callback.message.answer("❌ Ошибка: не удалось изменить роль.")
    await callback.answer()

@router.callback_query(F.data == "admin_close")
async def close_menu(callback: CallbackQuery):
    """ Закрывает админское меню. """
    await callback.message.delete()
    await callback.answer()
