import pytest
from aiogram.types import ReplyKeyboardRemove

import config
from constants import SEARCH_BUTTON, IMPORT_BUTTON, UNSUPPORTED_BUTTON_MESSAGE
from handlers.items import process_search_query, process_action_choice
from states import SearchFlow


@pytest.mark.asyncio
async def test_process_search_query__valid_query__stores_normalized_query(mocker):
    mock_make_row_keyboard = mocker.patch("handlers.items.keyboards.make_row_keyboard")
    message = mocker.MagicMock()
    message.text = "  iPhone 15 Pro  "
    message.answer = mocker.AsyncMock()

    state = mocker.AsyncMock()
    keyboard = mocker.MagicMock()
    mock_make_row_keyboard.return_value = keyboard

    await process_search_query(message, state)

    mock_make_row_keyboard.assert_called_once_with([SEARCH_BUTTON, IMPORT_BUTTON])

    message.answer.assert_awaited_once_with(
        text="Оберіть дію: Новий пошук або Імпорт з базІ даних?",
        reply_markup=keyboard,
    )

    state.update_data.assert_awaited_once_with(query="iphone 15 pro")
    state.set_state.assert_awaited_once_with(SearchFlow.selecting_action)


@pytest.mark.asyncio
async def test_process_action_choice__search_button__shows_marketplaces(mocker):
    keyboard = mocker.MagicMock()
    mock_make_multiline_keyboard = mocker.patch(
        "handlers.items.keyboards.make_multiline_keyboard",
        return_value=keyboard,
    )

    message = mocker.MagicMock()
    message.text = SEARCH_BUTTON
    message.answer = mocker.AsyncMock()

    state = mocker.AsyncMock()

    await process_action_choice(message, state)

    mock_make_multiline_keyboard.assert_called_once_with(
        list(config.MARKETPLACE_URLS),
        4,
    )

    message.answer.assert_awaited_once_with(
        "Виберіть Маркетплейс:",
        reply_markup=keyboard,
    )
    state.set_state.assert_awaited_once_with(SearchFlow.selecting_marketplace)


@pytest.mark.asyncio
async def test_process_action_choice__import_button__asks_for_db_query(mocker):
    message = mocker.MagicMock()
    message.text = IMPORT_BUTTON
    message.answer = mocker.AsyncMock()

    state = mocker.AsyncMock()

    await process_action_choice(message, state)

    message.answer.assert_awaited_once_with(
        text="Введіть ID конкретної картки або 0 для пошуку всіх ID в базі даних?",
        reply_markup=ReplyKeyboardRemove(),
    )
    state.set_state.assert_awaited_once_with(SearchFlow.selecting_db_query)


@pytest.mark.asyncio
async def test_process_action_choice__unsupported_button__shows_error(mocker):
    message = mocker.MagicMock()
    message.text = "Something else"
    message.answer = mocker.AsyncMock()

    state = mocker.AsyncMock()

    await process_action_choice(message, state)

    message.answer.assert_awaited_once_with(UNSUPPORTED_BUTTON_MESSAGE)

    state.set_state.assert_not_awaited()
