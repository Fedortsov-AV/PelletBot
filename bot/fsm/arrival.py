from aiogram.fsm.state import State, StatesGroup

class ArrivalState(StatesGroup):
    type = State()
    type_edit = State()
    amount = State()
    amount_edit = State()
    confirm = State()
