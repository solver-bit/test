from aiogram.fsm.state import StatesGroup, State

class DodgeOrder(StatesGroup):
    waiting_for_city = State()   # Шаг 1: Ждем город
    waiting_for_phone = State()  # Шаг 2: Ждем телефон
class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()