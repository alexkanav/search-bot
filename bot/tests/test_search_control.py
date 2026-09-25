from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import ReplyKeyboardRemove

from constants import SEARCH_BUTTON, CANCEL_BUTTON
from services.search_control import (
    ask_for_action,
    cancel_search,
    start_search_flow,
    stop_search,
)
from states import SearchFlow


@pytest.mark.asyncio
async def test_start_search_flow__called__asks_for_item_and_sets_state():
    message = MagicMock()
    message.answer = AsyncMock()

    state = AsyncMock()

    await start_search_flow(message, state)

    message.answer.assert_awaited_once_with(
        text="Що шукаєте?",
        reply_markup=ReplyKeyboardRemove(),
    )

    state.set_state.assert_awaited_once_with(
        SearchFlow.selecting_item
    )


@pytest.mark.asyncio
async def test_cancel_search__called__clears_state_and_notifies_user():
    message = MagicMock()
    message.answer = AsyncMock()

    state = AsyncMock()

    await cancel_search(message, state)

    state.clear.assert_awaited_once()

    message.answer.assert_awaited_once_with(
        text="Дію відхилено.",
        reply_markup=ReplyKeyboardRemove(),
    )


@pytest.mark.asyncio
async def test_stop_search__called__clears_state_and_notifies_user():
    message = MagicMock()
    message.answer = AsyncMock()

    state = AsyncMock()

    await stop_search(message, state)

    state.clear.assert_awaited_once()

    message.answer.assert_awaited_once_with(
        text="Пошук зупинено.\nЗвертайтесь ще, в мене немає вихідних)",
        reply_markup=ReplyKeyboardRemove(),
    )


@pytest.mark.asyncio
async def test_ask_for_action__called__shows_action_keyboard_and_sets_state(mocker):
    mock_make_row_keyboard = mocker.patch("services.search_control.make_row_keyboard")
    message = MagicMock()
    message.answer = AsyncMock()

    state = AsyncMock()

    keyboard = MagicMock()
    mock_make_row_keyboard.return_value = keyboard

    await ask_for_action(message, state)

    mock_make_row_keyboard.assert_called_once_with(
        [SEARCH_BUTTON, CANCEL_BUTTON],
    )

    message.answer.assert_awaited_once_with(
        text="Оберіть дію",
        reply_markup=keyboard,
    )

    state.set_state.assert_awaited_once_with(
        SearchFlow.confirming_search
    )
