from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, time
from bot.handlers.stock_handlers import send_daily_stock_report
from bot.models.database import async_session

class SchedulerService:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    async def start(self):
        """Запускает планировщик с ежедневным отчетом"""
        self.scheduler.add_job(
            self._safe_send_report,
            'cron',
            hour=4,
            minute=12,
            timezone='Europe/Moscow'
        )
        self.scheduler.start()

    async def _safe_send_report(self):
        try:
            async with async_session() as session:
                await send_daily_stock_report(self.bot, session)
        except Exception as e:
            print(f"Критическая ошибка в планировщике: {str(e)}")