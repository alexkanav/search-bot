from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from infrastructure.mongo_repository import ItemRepository
from services.search_control import stop_search
from services.task_manager import TaskManager
from services.telegram_service import notify_user
from telegram.constants import DB_QUERY_BY_ID, DB_QUERY_ALL
from telegram.constants import ERROR_MESSAGE
from telegram.states import SearchFlow
from utils.card import is_valid_card_id

router = Router()


@router.message(SearchFlow.selecting_db_query)
async def select_db_query(
        message: Message,
        state: FSMContext,
        repository: ItemRepository,
        task_manager: TaskManager,
) -> None:
    if message.text == DB_QUERY_BY_ID:
        await message.answer("Введіть номер картки", reply_markup=ReplyKeyboardRemove())
        await state.set_state(SearchFlow.selecting_card)
        return

    if message.text == DB_QUERY_ALL:
        data = await state.get_data()
        items = await repository.get_items(message.from_user.id, data["query"])
        for item in items:
            await notify_user(message, item)

        await stop_search(message, state, task_manager)
        return

    await message.answer(ERROR_MESSAGE)


@router.message(SearchFlow.selecting_card)
async def handle_card_lookup(
        message: Message,
        state: FSMContext,
        repository: ItemRepository,
        task_manager: TaskManager,
) -> None:
    card_id = message.text.strip()
    if not is_valid_card_id(card_id):
        await message.answer(text="Помилка. Вкажіть валідний номер картки:")
        return

    item = await repository.get_item(message.from_user.id, card_id)
    if not item:
        await message.answer("Картку не знайдено.")
        return

    await notify_user(message, item)
    await stop_search(message, state, task_manager)
