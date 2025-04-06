from aiogram.fsm.state import StatesGroup, State


class AddRecordStates(StatesGroup):
    waiting_for_table = State()
    waiting_for_fields = State()
    waiting_table = State()
    waiting_field_value = State()
    waiting_fk_selection = State()


class EditRecordStates(StatesGroup):
    selecting_field = State()
    editing_field = State()
