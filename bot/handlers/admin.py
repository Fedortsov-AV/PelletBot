import logging

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.filters.exception import ExceptionTypeFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from select import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.exceptions import InvalidDataError
from bot.fsm.admin import AddRecordStates
from bot.keyboards.admin import admin_menu, record_actions_keyboard, table_actions_keyboard, db_tables_keyboard, \
    cancel_keyboard, db_management_keyboard, back_to_table_keyboard
from bot.keyboards.users import get_user_list_keyboard
from bot.keyboards.roles import get_role_selection_keyboard
from bot.services.auth import get_user_role, update_user_role, get_all_users, is_admin
from bot.services.db_service import DBService
from bot.services.role_service import get_all_roles

logger = logging.getLogger(__name__)
router = Router()

class DBErrorFilter(ExceptionTypeFilter):
    def __init__(self):
        super().__init__(SQLAlchemyError)

    async def __call__(self, exception: Exception) -> bool:
        logger.error(f"Database error: {str(exception)}")
        return True

router.error.filter(DBErrorFilter())

@router.message(Command("admin"))
async def admin_panel(message: types.Message, session: AsyncSession):
    """ Открывает панель администратора. """
    role = await get_user_role(session, message.from_user.id)

    if role != "admin":
        await message.answer("❌ У вас нет прав для доступа в админ-панель.")
        return

    await message.answer("🔧 Панель администратора", reply_markup=admin_menu())


@router.message(F.text == "🔧 Панель администратора")
async def admin_panel(message: types.Message, session: AsyncSession):
    role = await get_user_role(session, message.from_user.id)

    if role != "admin":
        await message.answer("❌ У вас нет прав для доступа в админ-панель.")
        return

    await message.answer("🔧 Панель администратора", reply_markup=admin_menu())

@router.callback_query(F.data == "admin_users")
async def show_users(callback: CallbackQuery, session: AsyncSession):
    """ Отображает список пользователей. """
    users = await get_all_users(session)

    if not users:
        await callback.message.answer("📭 В базе данных пока нет пользователей.")
        return

    for user in users:
        await callback.message.answer(
            f"👤 {user.full_name} (ID: {user.telegram_id})\nРоль: {user.role}",
            reply_markup=get_user_list_keyboard(user.telegram_id)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("change_role:"))
async def ask_for_role_selection(callback: CallbackQuery, session: AsyncSession):
    """ Запрашивает новую роль у администратора. """
    user_id = int(callback.data.split(":")[1])

    # Получаем список ролей из базы данных
    roles = await get_all_roles(session)

    # Генерируем клавиатуру с ролями
    role_buttons = [types.InlineKeyboardButton(text=role.name, callback_data=f"set_role:{user_id}:{role.name}") for role in roles]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[role_buttons])

    await callback.message.answer(
        f"🔄 На какую роль изменить пользователя {user_id}?",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_role:"))
async def set_user_role(callback: CallbackQuery, session: AsyncSession):
    """ Меняет роль пользователя в БД. """
    _, user_id, role = callback.data.split(":")
    user_id = int(user_id)

    success = await update_user_role(session, user_id, role)

    if success:
        await callback.message.answer(f"✅ Роль пользователя {user_id} изменена на `{role}`.", parse_mode="Markdown")
    else:
        await callback.message.answer("❌ Ошибка: не удалось изменить роль.")
    await callback.answer()

@router.callback_query(F.data == "admin_close")
async def close_menu(callback: CallbackQuery):
    """ Закрывает админское меню. """
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "admin_db")
async def handle_db_management(callback: CallbackQuery):
    """Меню управления БД"""
    await callback.message.edit_text(
        "🗃 Управление базой данных\nВыберите таблицу:",
        reply_markup=db_management_keyboard()
    )
    await callback.answer()



@router.callback_query(F.data.startswith("select_table:"))
async def handle_table_selection(callback: CallbackQuery):
    """Обработка выбора таблицы"""
    table_name = callback.data.split(":")[1]
    await callback.message.edit_text(
        f"Таблица: {table_name.capitalize()}\nВыберите действие:",
        reply_markup=table_actions_keyboard(table_name)
    )
    await callback.answer()

# @router.callback_query(F.data.startswith("view_records:"))
# async def view_table_records(callback: CallbackQuery, session: AsyncSession):
#     """Просмотр записей таблицы"""
#     table_name = callback.data.split(":")[1]
#     # Здесь реализация просмотра записей
#     await callback.answer()
#
# @router.callback_query(F.data.startswith("add_record:"))
# async def start_adding_record(callback: CallbackQuery, state: FSMContext):
#     """Начало добавления записи"""
#     table_name = callback.data.split(":")[1]
#     await state.update_data(table_name=table_name)
#     await callback.message.answer(
#         f"Начато добавление записи в таблицу {table_name}\nВведите данные в формате:\n"
#         "поле1=значение1\nполе2=значение2\n...",
#         reply_markup=cancel_keyboard()
#     )
#     await callback.answer()

async def ask_for_field(message: Message, state: FSMContext):
    """Запросить следующее поле"""
    data = await state.get_data()
    current_field = data['required_fields'][data['current_field_index']]

    await message.answer(
        f"Введите значение для поля '{current_field}':",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AddRecordStates.waiting_field_value)

@router.callback_query(F.data.startswith("db_view:"))
async def handle_view_table(callback: CallbackQuery, session: AsyncSession):
    """Просмотр записей таблицы"""
    if not await is_admin(session, callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    table_name = callback.data.split(":")[1]
    model = DBService.get_model(table_name)

    if not model:
        await callback.message.answer("Таблица не найдена")
        return

    records = await DBService.get_last_records(session, model)

    if not records:
        await callback.message.answer("В таблице нет записей")
        return

    for record in records:
        text = "\n".join(f"{key}: {value}" for key, value in record.__dict__.items() if not key.startswith("_"))
        await callback.message.answer(
            text,
            reply_markup=record_actions_keyboard(table_name, record.id)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("view_records:"))
async def view_table_records_handler(callback: CallbackQuery, session: AsyncSession):
    try:
        # Проверка прав
        if not await is_admin(session, callback.from_user.id):
            await callback.answer("⛔ Доступ запрещен")
            return

        table_name = callback.data.split(":")[1]
        logger.info(f"View records requested for table: {table_name}")

        # Получаем модель и записи
        model = DBService.get_model(table_name)
        records = await DBService.get_records(session, model, limit=5)

        if not records:
            await callback.message.answer(
                f"📭 Таблица '{table_name}' пуста",
                reply_markup=back_to_table_keyboard()
            )
            return

        # Отправляем записи по одной с кнопками
        for record in records:
            record_text = format_record(record)
            await callback.message.answer(
                record_text,
                reply_markup=record_actions_keyboard(table_name, record.id)
            )

        await callback.message.answer(
            f"🔍 Показано {len(records)} последних записей из '{table_name}'",
            reply_markup=back_to_table_keyboard()
        )

    except ValueError as e:
        logger.error(f"Error: {str(e)}")
        await callback.message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=back_to_table_keyboard()
        )
    finally:
        await callback.answer()

def format_record(record) -> str:
    """Форматирует запись БД в читаемый текст"""
    fields = []
    for key, value in record.__dict__.items():
        if not key.startswith('_'):
            fields.append(f"<b>{key}:</b> {value}")
    return "\n".join(fields)

@router.callback_query(F.data.startswith("delete:"))
async def handle_delete_record(callback: CallbackQuery, session: AsyncSession):
    """Обработчик удаления с улучшенной обработкой ошибок"""
    try:
        _, table_name, record_id = callback.data.split(":")
        record_id = int(record_id)

        model = DBService.get_model(table_name)
        if not model:
            await callback.answer("❌ Таблица не найдена")
            return

        try:
            success = await DBService.delete_record(session, model, record_id)
            if success:
                await callback.message.answer(
                    f"✅ Запись {record_id} успешно удалена из {table_name}",
                    reply_markup=back_to_table_keyboard()
                )
            else:
                await callback.message.answer(
                    f"❌ Запись {record_id} не найдена в {table_name}",
                    reply_markup=back_to_table_keyboard()
                )
        except InvalidDataError as e:
            await callback.message.answer(
                f"⚠️ {str(e)}\nУдалите сначала связанные данные.",
                reply_markup=back_to_table_keyboard()
            )

    except ValueError:
        await callback.message.answer(
            "❌ Неверный формат ID записи",
            reply_markup=back_to_table_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_delete: {str(e)}")
        await callback.message.answer(
            "⚠️ Произошла непредвиденная ошибка",
            reply_markup=back_to_table_keyboard()
        )
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("db_add:"))
async def handle_add_record_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления записи"""
    table_name = callback.data.split(":")[1]
    await state.set_state(AddRecordStates.waiting_for_fields)
    await state.update_data(table_name=table_name)

    model = DBService.get_model(table_name)
    if not model:
        await callback.message.answer("Таблица не найдена")
        return

    # Здесь можно добавить логику для запроса конкретных полей
    if table_name == "пользователи":
        await callback.message.answer("Введите Telegram ID пользователя:")

    await callback.answer()


# @router.message(AddRecordStates.waiting_for_fields)
# async def handle_add_record_fields(message: Message, state: FSMContext, session: AsyncSession):
#     """Обработка полей для новой записи"""
#     data = await state.get_data()
#     table_name = data.get("table_name")
#
#     if table_name == "пользователи":
#         try:
#             telegram_id = int(message.text)
#             await state.update_data(telegram_id=telegram_id)
#             await message.answer("Введите полное имя пользователя:")
#             # Здесь можно продолжить сбор данных
#         except ValueError:
#             await message.answer("Пожалуйста, введите числовой Telegram ID")
#             return


# @router.message(AddRecordStates.waiting_field_value)
# async def handle_field_value(message: Message, state: FSMContext, session: AsyncSession):
#     """Обработка введенного значения поля"""
#     data = await state.get_data()
#     current_field = data['required_fields'][data['current_field_index']]
#
#     # Сохраняем значение поля
#     record_data = data['record_data']
#     record_data[current_field] = message.text
#
#     # Обновляем индекс текущего поля
#     current_field_index = data['current_field_index'] + 1
#     await state.update_data(
#         record_data=record_data,
#         current_field_index=current_field_index
#     )
#
#     # Проверяем, есть ли еще поля для заполнения
#     if current_field_index < len(data['required_fields']):
#         await ask_for_field(message, state)
#     else:
#         await finish_adding(message, state, session)


async def finish_adding(message: Message, state: FSMContext, session: AsyncSession):
    """Завершение процесса добавления"""
    data = await state.get_data()
    try:
        record = data['model'](**data['record_data'])
        session.add(record)
        await session.commit()

        await message.answer(
            f"✅ Запись успешно добавлена в таблицу '{data['table_name']}'",
            reply_markup=admin_menu()
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при добавлении записи: {str(e)}",
            reply_markup=admin_menu()
        )
    finally:
        await state.clear()


@router.callback_query(F.data.startswith("view_structure:"))
async def view_table_structure(callback: CallbackQuery):
    """Просмотр структуры таблицы"""
    table_name = callback.data.split(":")[1]
    model = DBService.get_model(table_name)
    fields = DBService.get_model_fields(model)

    text = f"Структура таблицы {table_name}:\n\n"
    for field, props in fields.items():
        text += f"{field}: {props['type']} "
        text += "(обязательное)" if not props['nullable'] else "(опциональное)"
        text += "\n"

    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "test_db")
async def test_db_handler(callback: CallbackQuery, session: AsyncSession):
    try:
        from bot.models import User
        test_records = await session.execute(select(User).limit(5))
        count = len(test_records.scalars().all())
        await callback.answer(f"Тест БД: найдено {count} пользователей")
    except Exception as e:
        logger.error(f"Test DB error: {str(e)}")
        await callback.answer("❌ Ошибка теста БД")