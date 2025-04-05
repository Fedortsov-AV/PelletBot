from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(role: str) -> ReplyKeyboardMarkup:
    """Генерация клавиатуры в зависимости от роли пользователя"""
    buttons = []  # Доступно всем пользователям

    # Кнопка "Приходы" доступна всем, кроме анонимов
    if role != "anonymous":
        buttons.append([KeyboardButton(text="Приходы")])

    if role != "anonymous":
        buttons.append([KeyboardButton(text="🚚 Отгрузка")])

    # Кнопка "Фасовка" доступна всем, кроме анонимов
    if role != "anonymous":
        buttons.append([KeyboardButton(text="📦 Фасовка")])

    # Кнопки для администраторов и менеджеров
    if role in ["admin", "manager"]:
        buttons.append([KeyboardButton(text="💸 Расходы")])
        buttons.append([KeyboardButton(text="Заявки")])

    # Кнопка "Управление ролями" доступна только для администратора
    if role == "admin":
        buttons.append([KeyboardButton(text="🔧 Панель администратора")])

    # Кнопка "Статистика" доступна только для администратора и менеджера
    if role in ["admin", "manager"]:
        buttons.append([KeyboardButton(text="📊 Статистика", callback_data="statistics")])

    # Оператор не должен видеть кнопку "Приходы за месяц"
    if role == "operator":
        return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)