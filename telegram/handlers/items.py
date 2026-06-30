from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import config
from telegram import keyboards
from telegram.constants import SEARCH_BUTTON, IMPORT_BUTTON, ERROR_MESSAGE, DB_QUERY_BY_ID, DB_QUERY_ALL
from telegram.states import SearchFlow

router = Router()


@router.message(SearchFlow.selecting_item)
async def process_item(message: Message, state: FSMContext) -> None:
    await state.update_data(query=message.text.strip().lower())
    await message.answer(
        text="Оберіть дію: Новий пошук, або Імпорт з бази данних?",
        reply_markup=keyboards.make_row_keyboard([SEARCH_BUTTON, IMPORT_BUTTON]),
    )
    await state.set_state(SearchFlow.selecting_action)


@router.message(SearchFlow.selecting_action)
async def process_action_choice(message: Message, state: FSMContext) -> None:
    if message.text == SEARCH_BUTTON:
        await message.answer(
            "Виберіть Маркетплейс:",
            reply_markup=keyboards.make_multiline_keyboard(list(config.MARKETPLACE_URLS), 4),
        )
        await state.set_state(SearchFlow.selecting_marketplace)
        return

    if message.text == IMPORT_BUTTON:
        await message.answer(
            text="Оберіть ID конкретної картки або усі наявні в базі даних?",
            reply_markup=keyboards.make_row_keyboard([DB_QUERY_BY_ID, DB_QUERY_ALL]),
        )
        await state.set_state(SearchFlow.selecting_db_query)
        return

    await message.answer(ERROR_MESSAGE)
