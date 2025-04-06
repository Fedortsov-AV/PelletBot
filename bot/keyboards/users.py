from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_user_list_keyboard(user_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить права", callback_data=f"change_role:{user_id}")]
        ]
    )
