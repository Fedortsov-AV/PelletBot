import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from bot.handlers import register_handlers
from bot.middlewares.db import DBMiddleware  # Импортируем middleware
from bot.models import create_tables
from bot.models.database import init_db, async_session
from bot.config import TOKEN
from bot.context import app_context
from bot.services.notification_service import NotificationService
from bot.services.role_service import fill_roles

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)





async def main():
    print(f'{TOKEN=}')
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    await init_db()  # Инициализация БД
    await on_startup(bot)
    async with async_session() as session:
        await fill_roles(session)
    logging.info("Таблица ролей заполнена.")

    dp.update.middleware(DBMiddleware())  # Подключаем middleware
    register_handlers(dp)  # Регистрация обработчиков



    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота"),
    ])

    await dp.start_polling(bot)

async def on_startup(bot):
    await create_tables()
    from bot.services.scheduler import SchedulerService
    scheduler = SchedulerService(bot)
    await scheduler.start()
    app_context.notification_service.set_bot(bot)


if __name__ == "__main__":
    asyncio.run(main())
