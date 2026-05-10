# bot/migrate_materials.py
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from bot.config import DATABASE_URL

async def run():
    print(DATABASE_URL)
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # Таблица материалов (справочник)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL UNIQUE
            );
        """))
        # Движения материалов (приход/расход)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS material_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL REFERENCES materials(id),
                type VARCHAR NOT NULL CHECK(type IN ('in','out')),
                quantity FLOAT NOT NULL,
                unit VARCHAR NOT NULL,
                unit_price FLOAT,
                remaining_quantity FLOAT,
                date DATETIME DEFAULT CURRENT_TIMESTAMP,
                expense_id INTEGER REFERENCES expenses(id),
                packaging_id INTEGER REFERENCES packaging(id)
            );
        """))
        # Связь материалов с фасовкой
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS packaging_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                packaging_id INTEGER NOT NULL REFERENCES packaging(id),
                material_id INTEGER NOT NULL REFERENCES materials(id),
                quantity FLOAT NOT NULL,
                unit VARCHAR NOT NULL,
                cost FLOAT NOT NULL
            );
        """))
        # Таблица для хранения результатов калькуляции себестоимости
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cost_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                total_material_cost FLOAT,
                total_overhead_cost FLOAT,
                total_produced_kg FLOAT,
                cost_per_kg FLOAT,
                calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """))
        # Дополняем таблицу packaging
        cols = await conn.execute(text("PRAGMA table_info('packaging')"))
        col_names = [row[1] for row in cols.fetchall()]
        if 'total_material_cost' not in col_names:
            await conn.execute(text("ALTER TABLE packaging ADD COLUMN total_material_cost FLOAT DEFAULT 0.0"))
        # Дополняем таблицу expenses (если ещё не добавляли)
        cols = await conn.execute(text("PRAGMA table_info('expenses')"))
        exp_cols = [row[1] for row in cols.fetchall()]
        if 'category' not in exp_cols:
            await conn.execute(text("ALTER TABLE expenses ADD COLUMN category VARCHAR"))
        if 'material_id' not in exp_cols:
            await conn.execute(text("ALTER TABLE expenses ADD COLUMN material_id INTEGER REFERENCES materials(id)"))
        if 'quantity' not in exp_cols:
            await conn.execute(text("ALTER TABLE expenses ADD COLUMN quantity FLOAT"))
        if 'unit' not in exp_cols:
            await conn.execute(text("ALTER TABLE expenses ADD COLUMN unit VARCHAR"))
        if 'employee_id' not in exp_cols:
            await conn.execute(text("ALTER TABLE expenses ADD COLUMN employee_id INTEGER REFERENCES users(id)"))
        if 'packaging_id' not in exp_cols:
            await conn.execute(text("ALTER TABLE expenses ADD COLUMN packaging_id INTEGER REFERENCES packaging(id)"))

if __name__ == "__main__":
    asyncio.run(run())