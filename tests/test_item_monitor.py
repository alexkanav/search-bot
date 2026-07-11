import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from aiogram.types import ReplyKeyboardRemove

from services.item_monitor import process_new_items, run_monitoring


class ProcessNewItemsDeps:
    def __init__(self):
        self.repository = AsyncMock()
        self.scraper = AsyncMock()
        self.message = MagicMock()
        self.message.from_user.id = 123
        self.search_params = MagicMock()


@pytest.fixture
def deps():
    return ProcessNewItemsDeps()


@pytest.mark.asyncio
async def test_process_new_items__with_new_items__notifies_user_and_saves_items(mocker, deps):
    items = [MagicMock(), MagicMock()]
    deps.scraper.find_new_items.return_value = items
    notify_user = mocker.patch("services.item_monitor.notify_user", new_callable=AsyncMock)

    await process_new_items(
        deps.repository,
        deps.scraper,
        deps.message,
        deps.search_params,
    )

    deps.scraper.find_new_items.assert_awaited_once_with(123, deps.search_params)

    assert notify_user.await_args_list == [
        call(deps.message, items[0]),
        call(deps.message, items[1]),
    ]

    deps.repository.insert_items.assert_awaited_once_with(123, items)


@pytest.mark.asyncio
async def test_process_new_items__without_new_items__returns_immediately(mocker, deps):
    deps.scraper.find_new_items.return_value = []

    notify_user = mocker.patch("services.item_monitor.notify_user", new_callable=AsyncMock)
    await process_new_items(
        deps.repository,
        deps.scraper,
        deps.message,
        deps.search_params,
    )
    deps.scraper.find_new_items.assert_awaited_once_with(123, deps.search_params)
    notify_user.assert_not_awaited()
    deps.repository.insert_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_monitoring__timeout_is_zero__processes_items_once(mocker, deps):
    search_params = MagicMock(timeout=0)
    process_items = mocker.patch("services.item_monitor.process_new_items", new_callable=AsyncMock)
    await run_monitoring(
        deps.repository,
        deps.scraper,
        deps.message,
        search_params,
    )

    process_items.assert_awaited_once_with(
        deps.repository,
        deps.scraper,
        deps.message,
        search_params,
    )


@pytest.mark.asyncio
async def test_run_monitoring__timeout_is_set__processes_items_and_sleeps_until_cancelled(mocker, deps, caplog):
    search_params = MagicMock(timeout=10)
    mock_process_new_items = mocker.patch("services.item_monitor.process_new_items", new_callable=AsyncMock)

    sleep = mocker.patch("services.item_monitor.asyncio.sleep", new_callable=AsyncMock)
    sleep.side_effect = asyncio.CancelledError

    with caplog.at_level(logging.INFO):
        await run_monitoring(
            deps.repository,
            deps.scraper,
            deps.message,
            search_params,
        )

    mock_process_new_items.assert_awaited_once_with(
        deps.repository,
        deps.scraper,
        deps.message,
        search_params,
    )
    sleep.assert_awaited_once_with(10 * 60)

    assert f"Stopped monitoring user {deps.message.from_user.id}" in caplog.text


@pytest.mark.asyncio
async def test_run_monitoring__processing_raises_exception__logs_and_notifies_user(mocker, deps, caplog):
    search_params = MagicMock(timeout=0)
    deps.message.answer = AsyncMock()

    mock_process_new_items = mocker.patch("services.item_monitor.process_new_items", new_callable=AsyncMock)
    mock_process_new_items.side_effect = RuntimeError("Boom")
    await run_monitoring(
        deps.repository,
        deps.scraper,
        deps.message,
        search_params,
    )

    mock_process_new_items.assert_awaited_once_with(
        deps.repository,
        deps.scraper,
        deps.message,
        search_params,
    )

    deps.message.answer.assert_awaited_once_with(
        "Сталася помилка під час моніторингу. Пошук зупинено.",
        reply_markup=ReplyKeyboardRemove(),
    )
    assert f"Monitoring failed for user {deps.message.from_user.id}" in caplog.text
