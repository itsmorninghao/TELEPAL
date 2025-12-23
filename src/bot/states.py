from aiogram.fsm.state import State, StatesGroup


class LocationStates(StatesGroup):
    """位置设置相关的状态"""

    waiting_for_location = State()
