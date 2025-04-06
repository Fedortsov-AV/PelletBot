from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_role_selection_keyboard(user_id: int, roles: list) -> InlineKeyboardMarkup:
    """Генерация клавиатуры для выбора роли пользователя."""
    keyboard = InlineKeyboardMarkup()
    for role in roles:
        keyboard.add(InlineKeyboardButton(text=role.name, callback_data=f"set_role:{user_id}:{role.name}"))
    return keyboard
