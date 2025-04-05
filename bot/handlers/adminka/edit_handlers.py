# ------------------- Файл handlers/adminka/edit_handlers.py -------------------
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.db_service import DBService
from bot.services.validation import DataValidator
from bot.fsm.admin import EditRecordStates
from bot.keyboards.admin import cancel_keyboard, edit_fields_keyboard

router = Router()


class EditHandler:
    def __init__(self, table_name: str, record_id: int):
        self.table_name = table_name
        self.record_id = record_id
        self.model = DBService.get_model(table_name)
        self.fields = DBService.get_model_fields(self.model)
        self.current_field = None

    async def start(self, callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        """Начало процесса редактирования"""
        record = await session.get(self.model, self.record_id)
        if not record:
            await callback.message.answer("Запись не найдена")
            return

        await state.set_state(EditRecordStates.selecting_field)
        await state.update_data(
            handler=self,
            record_data={col.name: getattr(record, col.name) for col in record.__table__.columns}
        )

        await callback.message.answer(
            "Выберите поле для редактирования:",
            reply_markup=edit_fields_keyboard(self.fields)
        )

    async def select_field(self, callback: CallbackQuery, state: FSMContext):
        """Выбор поля для редактирования"""
        field_name = callback.data.split(":")[1]
        self.current_field = field_name

        data = await state.get_data()
        current_value = data['record_data'].get(field_name, "")

        await state.set_state(EditRecordStates.editing_field)
        await callback.message.answer(
            f"Текущее значение поля '{field_name}': {current_value}\n"
            f"Введите новое значение ({self.fields[field_name]['type']}):",
            reply_markup=cancel_keyboard()
        )
        await callback.answer()

    async def handle_edit_input(self, message: Message, state: FSMContext):
        """Обработка ввода нового значения"""
        try:
            field_props = self.fields[self.current_field]
            validated_value = DataValidator.validate_field(
                self.current_field,
                field_props['type'],
                message.text
            )

            data = await state.get_data()
            data['record_data'][self.current_field] = validated_value
            await state.update_data(record_data=data['record_data'])

            await message.answer("Значение успешно обновлено. Хотите изменить еще что-то?",
                                 reply_markup=edit_fields_keyboard(self.fields))
            await state.set_state(EditRecordStates.selecting_field)

        except ValueError as e:
            await message.answer(f"Ошибка: {str(e)}\nПопробуйте еще раз:")

    async def finish(self, message: Message, state: FSMContext, session: AsyncSession):
        """Завершение редактирования и сохранение"""
        data = await state.get_data()
        try:
            await DBService.update_record(
                session,
                self.model,
                self.record_id,
                data['record_data']
            )
            await message.answer("✅ Изменения успешно сохранены")
            await state.clear()
        except Exception as e:
            await message.answer(f"Ошибка при сохранении: {str(e)}")


@router.callback_query(F.data.startswith("db_edit:"))
async def handle_edit_record(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработчик начала редактирования"""
    _, table_name, record_id = callback.data.split(":")
    handler = EditHandler(table_name, int(record_id))
    await handler.start(callback, state, session)
    await callback.answer()


@router.callback_query(EditRecordStates.selecting_field, F.data.startswith("edit_field:"))
async def handle_field_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора поля"""
    data = await state.get_data()
    handler = data['handler']
    await handler.select_field(callback, state)


@router.message(EditRecordStates.editing_field)
async def handle_edit_input(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик ввода нового значения"""
    data = await state.get_data()
    handler = data['handler']
    await handler.handle_edit_input(message, state)


@router.callback_query(EditRecordStates.selecting_field, F.data == "edit_finish")
async def handle_edit_finish(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Завершение редактирования"""
    data = await state.get_data()
    handler = data['handler']
    await handler.finish(callback.message, state, session)
    await callback.answer()