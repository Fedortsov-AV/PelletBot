from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.db_service import DBService


def admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Пользователи", callback_data="admin_users")
    builder.button(text="🗃 Управление БД", callback_data="admin_db")
    builder.button(text="❌ Закрыть", callback_data="admin_close")
    return builder.adjust(2).as_markup()


def record_actions_keyboard(table_name: str, record_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Изменить", callback_data=f"db_edit:{table_name}:{record_id}")
    builder.button(text="🗑 Удалить", callback_data=f"delete:{table_name}:{record_id}")
    builder.adjust(2)
    return builder.as_markup()


def db_management_keyboard():
    """Клавиатура выбора таблиц"""
    builder = InlineKeyboardBuilder()
    models = DBService.MODELS.keys()
    # tables = ["Пользователи", "Продукты", "Сырье", "Отгрузки", "Поступления", "Расходы"]
    tables = [x for x in models]
    for table in tables:
        builder.button(text=table, callback_data=f"select_table:{table.lower()}")
    builder.button(text="⬅️ Назад", callback_data="admin_menu")
    builder.adjust(2)
    return builder.as_markup()


def table_actions_keyboard(table_name: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить", callback_data=f"add_record:{table_name}")
    builder.button(text="👁 Просмотреть", callback_data=f"view_records:{table_name}")
    builder.button(text="📋 Структура", callback_data=f"view_structure:{table_name}")
    builder.button(text="⬅️ Назад", callback_data="admin_db_manage")
    builder.adjust(2)
    return builder.as_markup()


def cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()


def edit_fields_keyboard(fields):
    builder = InlineKeyboardBuilder()
    for field_name in fields:
        if field_name != 'id':
            builder.button(text=field_name, callback_data=f"edit_field:{field_name}")
    builder.button(text="✅ Готово", callback_data="edit_finish")
    builder.button(text="❌ Отмена", callback_data="cancel_operation")
    return builder.adjust(2).as_markup()


def back_to_table_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 К таблице", callback_data=f"admin_db")
    builder.button(text="📋 В меню", callback_data="admin_menu")
    builder.adjust(2)
    return builder.as_markup()

# def get_fk_keyboard(options, field_name):
#     builder = InlineKeyboardBuilder()
#     for item in options:
#         builder.button(
#             text=f"{item.id}: {getattr(item, 'name', str(item.id))}",
#             callback_data=f"fk_select:{field_name}:{item.id}"
#         )
#     builder.button(text="❌ Отмена", callback_data="cancel_add_record")
#     builder.adjust(1)
#     return builder.as_markup()
