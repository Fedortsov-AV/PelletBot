# bot/migrate_arrival_fix_type.py
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import DATABASE_URL

async def run_fix():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # Отключаем проверку внешних ключей на время миграции
        await conn.execute(text("PRAGMA foreign_keys=OFF;"))

        # Создаём новую таблицу с правильной схемой
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS arrivals_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type VARCHAR NULL,
                raw_product_id INTEGER NOT NULL REFERENCES raw_products(id),
                amount INTEGER NOT NULL,
                date DATETIME,
                user_id INTEGER NOT NULL REFERENCES users(id)
            );
        """))

        # Копируем данные из старой таблицы в новую
        await conn.execute(text("""
            INSERT INTO arrivals_new (id, type, raw_product_id, amount, date, user_id)
            SELECT id, type, raw_product_id, amount, date, user_id FROM arrivals;
        """))

        # Удаляем старую таблицу
        await conn.execute(text("DROP TABLE arrivals;"))

        # Переименовываем новую таблицу в оригинальное имя
        await conn.execute(text("ALTER TABLE arrivals_new RENAME TO arrivals;"))

        # Включаем внешние ключи обратно
        await conn.execute(text("PRAGMA foreign_keys=ON;"))

if __name__ == "__main__":
    asyncio.run(run_fix())