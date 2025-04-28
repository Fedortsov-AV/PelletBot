from datetime import datetime
from typing import Dict, Any, Optional

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import User  # Новая модель для логов
from bot.services.db_service import DBService, get_admin_ids
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
        # self.TRACKED_ENTITIES = {"expense", "arrival"}

    def set_bot(self, bot: Bot):
        self.bot = bot

    async def _get_admin_ids(self, session: AsyncSession) -> list[int]:
        """Получаем ID администраторов"""
        return await get_admin_ids(session)

    async def send_notification(
        self,
        session: AsyncSession,
        user_id: int,
        message: str  # Принимаем готовое сообщение
    ):
        if not self.bot:
            logger.error("Bot instance not set in NotificationService")
            return

        try:
            admin_ids = await self._get_admin_ids(session)
            for admin_id in admin_ids:
                try:
                    await self.bot.send_message(admin_id, message)
                except Exception as e:
                    logger.error(f"Failed to send to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Notification error: {e}", exc_info=True)

    async def _get_admin_ids(self, session: AsyncSession) -> list[int]:
        result = await session.execute(
            select(User).with_only_columns(User.telegram_id).where(User.role == "admin")
        )
        return [row[0] for row in result.all()] or []

    def _format_message(
        self,
        user: User,
        action: str,
        entity: str,
        entity_id: int,
        old_data: Dict,
        new_data: Dict,
    ) -> str:
        """Форматирует сообщение для Telegram"""
        action_verbs = {
            "create": "добавил",
            "update": "изменил",
            "delete": "удалил",
        }
        entity_names = {
            "arrival": "приход",
            "expense": "расход",
            "shipment": "отгрузку",
            "packaging": "фасовку",
        }

        base_msg = (
            f"👤 Пользователь **{user.full_name}** (ID: {user.telegram_id})\n"
            f"⚡ **{action_verbs[action]}** {entity_names[entity]} #{entity_id}\n"
            f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        )

        if action == "update":
            changes = "\n".join(
                f"  - `{field}`: {old_data.get(field)} → **{new_data.get(field)}**"
                for field in new_data if field in old_data
            )
            base_msg += f"📝 Изменения:\n{changes}"

        elif action == "create":
            fields = "\n".join(f"  - `{k}`: **{v}**" for k, v in new_data.items())
            base_msg += f"📌 Данные:\n{fields}"

        elif action == "delete":
            fields = "\n".join(f"  - `{k}`: **{v}**" for k, v in old_data.items())
            base_msg += f"🗑 Удаленные данные:\n{fields}"

        return base_msg

    # async def _log_to_db(self, session: AsyncSession, user_id: int, action: str, entity: str, entity_id: int, old_data: Dict, new_data: Dict):
    #     """Сохраняет действие в таблицу AuditLog"""
    #     log_entry = AuditLog(
    #         user_id=user_id,
    #         action=action,
    #         entity_type=entity,
    #         entity_id=entity_id,
    #         old_data=str(old_data) if old_data else None,
    #         new_data=str(new_data) if new_data else None,
    #         timestamp=datetime.now(),
    #     )
    #     session.add(log_entry)
    #     await session.commit()