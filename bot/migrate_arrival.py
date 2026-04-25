# bot/migrate_arrival.py
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import DATABASE_URL

async def run_migration():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # Проверяем, есть ли уже колонка raw_product_id
        columns = await conn.execute(text("PRAGMA table_info('arrivals')"))
        col_names = [row[1] for row in columns.fetchall()]

        if 'raw_product_id' not in col_names:
            # Добавляем колонку, пока без NOT NULL
            await conn.execute(text(
                "ALTER TABLE arrivals ADD COLUMN raw_product_id INTEGER REFERENCES raw_products(id)"
            ))

            # Заполняем по соответствию type -> RawProduct.name
            await conn.execute(text("""
                UPDATE arrivals
                SET raw_product_id = (
                    SELECT id FROM raw_products WHERE name = arrivals.type
                )
            """))

            # Проверка, что у всех записей есть сырьё
            nulls = await conn.execute(text("SELECT COUNT(*) FROM arrivals WHERE raw_product_id IS NULL"))
            null_count = (nulls.fetchone())[0]
            if null_count > 0:
                raise Exception("Обнаружены приходы без соответствующего сырья. Миграция прервана.")

if __name__ == "__main__":
    asyncio.run(run_migration())