import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from bot.services.role_service import fill_roles
from config import TOKEN
from bot.handlers import register_handlers
from bot.models.database import init_db, async_session
from bot.middlewares.db import DBMiddleware  # Импортируем middleware
import asyncio
from bot.models import create_tables


logging.basicConfig(level=logging.INFO)

async def on_startup():
    await create_tables()





async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    await init_db()  # Инициализация БД
    await on_startup()
    # async with async_session() as session:
    #     await fill_roles(session)
    logging.info("Таблица ролей заполнена.")

    dp.update.middleware(DBMiddleware())  # Подключаем middleware
    register_handlers(dp)  # Регистрация обработчиков

    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="help", description="Справка"),
    ])

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
