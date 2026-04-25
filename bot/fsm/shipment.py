from aiogram.fsm.state import State, StatesGroup


class ShipmentStates(StatesGroup):
    waiting_for_product = State()
    waiting_for_quantity = State()
    waiting_for_more_products = State()
    selecting_product = State()  # Выбор продукта для отгрузки
    entering_quantity = State()  # Ввод количества для отгрузки
    adding_more = State()  # Добавление еще продуктов в отгрузку
