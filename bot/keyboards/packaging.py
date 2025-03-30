from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def packaging_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Пропорция", callback_data="packaging_proportion")],
            [InlineKeyboardButton(text="✅ Расфасовано", callback_data="packaging_done")],
            [InlineKeyboardButton(text="⚙ Задать соотношение", callback_data="set_packaging_ratio")],
            [InlineKeyboardButton(text="❌ Закрыть меню", callback_data="close_menu")]
        ]
    )

