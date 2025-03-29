from aiogram import Router, types
from aiogram.filters import Command
from bot.keyboards.user import user_menu

router = Router()

# Обработчик команды /info и кнопки "📜 Информация"
@router.message(Command("info"))
@router.message(lambda message: message.text == "📜 Информация")
async def info_handler(message: types.Message):
    text = "Это Telegram-бот для работы с системой склада. Версия 1.0."
    await message.answer(text, reply_markup=user_menu)

# Обработчик команды /help и кнопки "❓ Помощь"
@router.message(Command("help"))
@router.message(lambda message: message.text == "❓ Помощь")
async def help_handler(message: types.Message):
    text = "Доступные команды:\n" \
           "/start — Начать работу\n" \
           "/info — О боте\n" \
           "/help — Список команд\n" \
           "/admin — Панель администратора (для админов)"
    await message.answer(text, reply_markup=user_menu)
