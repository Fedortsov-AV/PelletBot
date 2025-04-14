# ------------------- Файл services/db_service.py -------------------
import logging
from sqlite3 import IntegrityError
from typing import List

from sqlalchemy import select, desc, inspect, exists
from sqlalchemy.ext.asyncio import AsyncSession

from bot.exceptions import InvalidDataError
from bot.models import User, Product, RawProduct, Shipment, Arrival, Expense, ShipmentItem, Role, RawMaterialStorage, \
    ProductStorage, Packaging

logger = logging.getLogger(__name__)


class DBService:
    MODELS = {
        'пользователи': User,
        'продукты': Product,
        'сырье': RawProduct,
        'отгрузки': Shipment,
        'поступления': Arrival,
        'расходы': Expense,
        'элементы_отгрузки': ShipmentItem,
        'роли': Role,
        'cклад сырья': RawMaterialStorage,
        'cклад продукции': ProductStorage,
        'фасовка': Packaging,
        # 'cклад продукции': ProductStorage,

    }

    @staticmethod
    def get_model(table_name: str):
        """Получить модель по имени таблицы"""
        table_name = table_name.lower()
        if table_name not in DBService.MODELS:
            raise ValueError(f"Неизвестная таблица: {table_name}")
        return DBService.MODELS[table_name]

    @staticmethod
    async def get_last_records(session: AsyncSession, model, limit=10):
        """Получить последние записи из таблицы"""
        result = await session.execute(
            select(model)
            .order_by(desc(model.id))
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def add_record(session: AsyncSession, model, data: dict):
        """Корректная проверка уникальности и добавление записи"""
        try:
            # Проверка уникальности имени для RawProduct и Product
            if model in (RawProduct, Product) and 'name' in data:
                exists_query = await session.execute(
                    select(exists().where(model.name == data['name']))
                )
                if exists_query.scalar():
                    raise InvalidDataError(f"Запись с именем '{data['name']}' уже существует")

            # Проверка существования сырья для Product
            if model == Product and 'raw_product_id' in data and data['raw_product_id']:
                raw_exists_query = await session.execute(
                    select(exists().where(RawProduct.id == data['raw_product_id']))
                )
                if not raw_exists_query.scalar():
                    raise InvalidDataError("Указанное сырьё не существует")

            # Создание записи
            record = model(**data)
            session.add(record)
            await session.flush()

            # Автоматическое создание хранилища
            if model == RawProduct:
                session.add(RawMaterialStorage(raw_product_id=record.id, amount=0))
            elif model == Product:
                session.add(ProductStorage(product_id=record.id, amount=0))

            await session.commit()
            return record

        except IntegrityError as e:
            await session.rollback()
            raise InvalidDataError("Ошибка целостности данных при сохранении")
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при добавлении записи: {str(e)}")
            raise

    @staticmethod
    async def update_record(session: AsyncSession, model, record_id: int, data: dict):
        """Обновить запись"""
        record = await session.get(model, record_id)
        if not record:
            raise ValueError("Запись не найдена")

        for key, value in data.items():
            if hasattr(record, key):
                setattr(record, key, value)

        await session.commit()
        return record

    @staticmethod
    async def delete_record(session: AsyncSession, model, record_id: int):
        """Удалить запись"""
        record = await session.get(model, record_id)
        if record:
            await session.delete(record)
            await session.commit()
            return True
        return False

    @staticmethod
    def get_model_fields(model):
        """Получить информацию о полях модели"""
        inspector = inspect(model)
        return {
            column.name: {
                'type': str(column.type),
                'nullable': column.nullable,
                'default': column.default.arg if column.default else None
            }
            for column in inspector.columns
        }

    @staticmethod
    def get_required_fields(model):
        """Получить обязательные поля модели"""
        inspector = inspect(model)
        return [
            col.name for col in inspector.columns
            if not col.nullable and col.default is None and col.name != 'id'
        ]

    @staticmethod
    async def get_records(session: AsyncSession, model, limit=10):
        """Получение записей с логированием"""
        try:
            result = await session.execute(
                select(model)
                .order_by(desc(model.id))
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"DB query error: {str(e)}")
            raise ValueError("Ошибка при получении данных из БД")

    @staticmethod
    async def get_foreign_key_options(session: AsyncSession, model, field_name: str):
        """Получает варианты для поля внешнего ключа"""
        inspector = inspect(model)
        rel = getattr(model, field_name).property
        related_model = rel.mapper.class_

        # Получаем все записи связанной таблицы
        result = await session.execute(select(related_model))
        return result.scalars().all()

    @staticmethod
    def get_model_fields_info(model):
        """Возвращает информацию о полях модели, включая FK"""
        inspector = inspect(model)
        fields = {}

        for column in inspector.columns:
            field_info = {
                'type': str(column.type),
                'nullable': column.nullable,
                'foreign_key': bool(column.foreign_keys)
            }

            if column.foreign_keys:
                fk = next(iter(column.foreign_keys))
                field_info['related_model'] = fk.column.table.name

            fields[column.name] = field_info

        return fields

    @staticmethod
    async def get_all_records(session: AsyncSession, model):
        """Получает все записи указанной модели"""
        result = await session.execute(select(model))
        return result.scalars().all()

async def get_admin_ids(session: AsyncSession) -> List[int]:
    """Получает telegram_id всех администраторов"""
    result = await session.execute(
        select(User.telegram_id).where(User.role == "admin")
    )
    return [row[0] for row in result.all()]
