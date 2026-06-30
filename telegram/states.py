from aiogram.fsm.state import StatesGroup, State


class SearchFlow(StatesGroup):
    selecting_item = State()
    selecting_action = State()
    selecting_marketplace = State()
    selecting_price = State()
    selecting_search_scope = State()
    selecting_region = State()
    selecting_location = State()
    selecting_timeout = State()
    confirming_search = State()
    selecting_card = State()
    selecting_db_query = State()
