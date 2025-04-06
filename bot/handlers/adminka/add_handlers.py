import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import RelationshipProperty

from bot.exceptions import InvalidDataError
from bot.fsm.admin import AddRecordStates
from bot.keyboards.admin import cancel_keyboard, back_to_table_keyboard
from bot.services.db_service import DBService
from bot.services.validation import DataValidator

logger = logging.getLogger(__name__)
router = Router()


class AddHandler:
    def __init__(self, table_name: str, session: AsyncSession):
        self.table_name = table_name
        self.session = session
        self.model = DBService.get_model(table_name)
        self.fields = DBService.get_model_fields(self.model)
        self.current_field = None
        self.data = {}
        self.required_fields = self._get_required_fields()

    def _get_required_fields(self):
        """Получает обязательные поля, включая проверку FK"""
        required = []
        for name, props in self.fields.items():
            # Пропускаем ID и nullable поля
            if name == 'id' or props['nullable']:
                continue

            # Включаем поля без значения по умолчанию
            if props['default'] is None:
                required.append(name)

            # Особо проверяем ForeignKey - они могут быть nullable=False
            # но не отмечены как обязательные при инспекции
            if props.get('foreign_key') and name not in required:
                required.append(name)

        return required

    async def start(self, message: Message, state: FSMContext):
        """Начало процесса добавления"""
        await state.set_state(AddRecordStates.waiting_for_fields)
        await state.update_data(handler=self)
        self.current_field = self.required_fields[0]
        await self._ask_for_field(message)

    async def _ask_for_field(self, message: Message):
        """Запрашивает значение поля или показывает варианты для FK"""
        field_props = self.fields[self.current_field]

        # Если это внешний ключ - показываем варианты
        if field_props.get('foreign_key'):
            await self._show_fk_options(message)
        else:
            await message.answer(
                f"Введите значение для поля '{self.current_field}' ({field_props['type']}):",
                reply_markup=cancel_keyboard()
            )

    async def _show_fk_options(self, message: Message):
        """Показывает варианты для поля внешнего ключа"""
        related_model = self._get_related_model(self.current_field)
        try:
            options = await DBService.get_all_records(self.session, related_model)

            if not options:
                await message.answer(
                    f"Нет доступных вариантов для {self.current_field}",
                    reply_markup=cancel_keyboard()
                )
                return

            keyboard = self._build_fk_keyboard(options)
            await message.answer(
                f"Выберите значение для {self.current_field}:",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка получения вариантов FK: {str(e)}")
            await message.answer(
                "Ошибка при получении вариантов",
                reply_markup=cancel_keyboard()
            )

    def _get_related_model(self, field_name: str):
        """Получает модель связанной таблицы"""
        rel: RelationshipProperty = getattr(self.model, field_name).property
        return rel.mapper.class_

    def _build_fk_keyboard(self, options):
        """Строит клавиатуру с вариантами FK"""
        builder = InlineKeyboardBuilder()
        for option in options:
            builder.button(
                text=f"{option.id}: {getattr(option, 'name', str(option.id))}",
                callback_data=f"fk_select:{option.id}"
            )
        builder.button(text="❌ Отмена", callback_data="cancel_add_record")
        builder.adjust(1)
        return builder.as_markup()

    async def handle_field_input(self, message: Message, state: FSMContext):
        """Обработка ввода значения обычного поля"""
        try:
            field_props = self.fields[self.current_field]
            validated_value = DataValidator.validate_field(
                self.current_field,
                field_props['type'],
                message.text
            )
            self.data[self.current_field] = validated_value
            await self._move_to_next_field(state, message)

        except ValueError as e:
            await message.answer(f"Ошибка: {str(e)}\nПопробуйте еще раз:")

    async def handle_fk_selection(self, value: int, state: FSMContext, message: Message):
        """Обработка выбора значения FK"""
        self.data[self.current_field] = value
        await self._move_to_next_field(state, message)

    async def _move_to_next_field(self, state: FSMContext, message: Message):
        """Переход к следующему полю или завершение"""
        current_idx = self.required_fields.index(self.current_field)
        if current_idx + 1 < len(self.required_fields):
            self.current_field = self.required_fields[current_idx + 1]
            await state.update_data(handler=self)
            await self._ask_for_field(message)
        else:
            await self._finish_adding(message, state)

    async def _finish_adding(self, message: Message, state: FSMContext):
        """Подготовка к завершению процесса"""
        await message.answer(
            "Проверьте введенные данные:\n" +
            "\n".join(f"{k}: {v}" for k, v in self.data.items()),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_add_record"),
                InlineKeyboardButton(text="🔄 Начать заново", callback_data=f"add_record:{self.table_name}")
            ]])
        )

    async def commit_record(self) -> int:
        """Гарантированное сохранение записи"""
        try:
            record = await DBService.add_record(self.session, self.model, self.data)
            return record.id
        except InvalidDataError as e:
            logger.error(f"Ошибка валидации: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Ошибка сохранения: {str(e)}")
            raise InvalidDataError("Не удалось сохранить запись")


@router.callback_query(F.data.startswith("add_record:"))
async def start_add_record(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Исправленный запуск добавления"""
    try:
        table_name = callback.data.split(":")[1]
        handler = AddHandler(table_name, session)
        await handler.start(callback.message, state)
    except Exception as e:
        logger.error(f"Ошибка запуска добавления: {str(e)}")
        await callback.message.answer(
            "Ошибка при запуске процесса добавления",
            reply_markup=back_to_table_keyboard()
        )
    finally:
        await callback.answer()


@router.message(AddRecordStates.waiting_for_fields)
async def handle_field_input(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка ввода значения поля"""
    data = await state.get_data()
    handler: AddHandler = data.get('handler')
    if handler:
        await handler.handle_field_input(message, state)


@router.callback_query(F.data.startswith("fk_select:"))
async def handle_fk_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора значения FK"""
    _, value = callback.data.split(":")
    data = await state.get_data()
    handler: AddHandler = data.get('handler')
    if handler:
        await handler.handle_fk_selection(int(value), state, callback.message)
    await callback.answer()


@router.callback_query(F.data == "confirm_add_record")
async def handle_confirm_add(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и сохранение записи"""
    data = await state.get_data()
    handler: AddHandler = data.get('handler')

    if not handler:
        await callback.answer("Ошибка: обработчик не найден")
        return

    try:
        record_id = await handler.commit_record()
        await callback.message.answer(
            f"✅ Запись успешно добавлена (ID: {record_id})",
            reply_markup=back_to_table_keyboard()
        )
    except InvalidDataError as e:
        await callback.message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=back_to_table_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка добавления записи: {str(e)}", exc_info=True)
        await callback.message.answer(
            "⚠️ Произошла непредвиденная ошибка",
            reply_markup=back_to_table_keyboard()
        )
    finally:
        await state.clear()
    await callback.answer()
