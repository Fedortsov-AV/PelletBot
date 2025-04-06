from aiogram.fsm.state import State, StatesGroup


class ShipmentState(StatesGroup):
    selecting_product = State()  # Выбор продукта для отгрузки
    entering_quantity = State()  # Ввод количества для отгрузки
    adding_more = State()  # Добавление еще продуктов в отгрузку
