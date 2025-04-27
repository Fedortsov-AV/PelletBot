from aiogram.dispatcher.middlewares.base import BaseMiddleware

from bot.models.database import async_session


class DBMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with async_session() as session:  # Используем вашу async_session
            data["session"] = session
            data['kwargs'] = data.get('kwargs', {})
            data['kwargs']['session'] = session
            return await handler(event, data)
