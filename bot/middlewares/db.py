from aiogram.dispatcher.middlewares.base import BaseMiddleware

from bot.models.database import async_session


class DBMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with async_session() as session:
            data["session"] = session  # Передаем сессию в обработчик
            return await handler(event, data)
