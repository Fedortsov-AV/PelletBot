from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def admin_menu():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📋 Список пользователей", callback_data="admin_users_list")
    keyboard.button(text="🔄 Изменить роль пользователя", callback_data="admin_change_role")
    keyboard.button(text="❌ Закрыть меню", callback_data="admin_close")
    return keyboard.as_markup()




def role_selection_keyboard(user_id: int):
    keyboard = InlineKeyboardBuilder()
    roles = ["admin", "manager", "user", "anonymous"]

    for role in roles:
        keyboard.button(text=role.capitalize(), callback_data=f"setrole_{user_id}_{role}")

    keyboard.button(text="❌ Отмена", callback_data="admin_close")
    return keyboard.as_markup()

def get_admin_menu():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users_list")],
            [InlineKeyboardButton(text="❌ Закрыть меню", callback_data="admin_close")]
        ]
    )
    return keyboard