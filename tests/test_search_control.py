import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import ReplyKeyboardRemove

from services.search_control import start_search_flow, cancel_search, stop_search, ask_for_action, start_monitoring
from telegram.constants import SEARCH_BUTTON, CANCEL_BUTTON, STOP_BUTTON
from telegram.states import SearchFlow


@pytest.mark.asyncio
async def test_start_search_flow__called__asks_for_item_and_sets_state():
    message = AsyncMock()
    state = AsyncMock()

    await start_search_flow(message, state)

    message.answer.assert_awaited_once_with(
        "Що шукаєте?",
        reply_markup=ReplyKeyboardRemove(),
    )
    state.set_state.assert_awaited_once_with(SearchFlow.selecting_item)


@pytest.mark.asyncio
async def test_cancel_search__called__clears_state_and_replies():
    message = AsyncMock()
    state = AsyncMock()

    await cancel_search(message, state)

    state.clear.assert_awaited_once()

    message.answer.assert_awaited_once_with(
        text="Дію відхилено.",
        reply_markup=ReplyKeyboardRemove(),
    )


@pytest.mark.asyncio
async def test_stop_search__called__cancels_task_clears_state_and_replies():
    message = AsyncMock()
    message.from_user.id = 123

    state = AsyncMock()
    task_manager = MagicMock()

    await stop_search(message, state, task_manager)

    task_manager.cancel.assert_called_once_with(123)
    state.clear.assert_awaited_once()

    message.answer.assert_awaited_once_with(
        text="Пошук зупинено.\nЗвертайтесь ще, в мене немає вихідних)",
        reply_markup=ReplyKeyboardRemove(),
    )


@pytest.mark.asyncio
async def test_ask_for_action__called__shows_keyboard_and_sets_state(mocker):
    message = AsyncMock()
    state = AsyncMock()

    keyboard = MagicMock()
    make_keyboard = mocker.patch(
        "services.search_control.keyboards.make_row_keyboard",
        return_value=keyboard,
    )

    await ask_for_action(message, state)

    make_keyboard.assert_called_once_with([SEARCH_BUTTON, CANCEL_BUTTON])

    message.answer.assert_awaited_once_with(
        text="Оберіть дію",
        reply_markup=keyboard,
    )

    state.set_state.assert_awaited_once_with(SearchFlow.confirming_search)


@pytest.mark.asyncio
async def test_start_monitoring__called__starts_monitoring_task(mocker):
    message = AsyncMock()
    message.from_user.id = 123

    repository = MagicMock()
    scraper = MagicMock()
    task_manager = MagicMock()
    search_params = MagicMock()

    keyboard = MagicMock()
    make_keyboard = mocker.patch(
        "services.search_control.keyboards.make_row_keyboard",
        return_value=keyboard,
    )

    await start_monitoring(
        message,
        repository,
        scraper,
        task_manager,
        search_params,
    )

    make_keyboard.assert_called_once_with([STOP_BUTTON])

    message.answer.assert_awaited_once_with(
        text="Почекайте, шукаю усі варіанти ...",
        reply_markup=keyboard,
    )

    task_manager.start.assert_called_once()

    user_id, coro = task_manager.start.call_args.args

    assert user_id == 123
    assert inspect.iscoroutine(coro)

    await coro
