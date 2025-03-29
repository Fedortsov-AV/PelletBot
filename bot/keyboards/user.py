from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Основное меню пользователя
user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📜 Информация"), KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)
