from aiogram.fsm.state import StatesGroup, State

class ExpenseStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_purpose = State()
    waiting_for_source = State()
    waiting_for_new_amount = State()
    waiting_for_new_purpose = State()
