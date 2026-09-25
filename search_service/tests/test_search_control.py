import asyncio

import pytest

from models.items import ItemParams
from services.search_control import SearchService
from utils.enums import Command
from unittest.mock import AsyncMock, MagicMock


def test_init__valid_dependencies__stores_dependencies():
    repository = MagicMock()
    scraper = MagicMock()
    rabbit = MagicMock()
    task_manager = MagicMock()

    service = SearchService(
        repository=repository,
        scraper=scraper,
        rabbit=rabbit,
        task_manager=task_manager,
    )

    assert service.repository is repository
    assert service.scraper is scraper
    assert service.rabbit is rabbit
    assert service.task_manager is task_manager


@pytest.mark.asyncio
async def test_search_handle__start_command__starts_monitoring(
        search_service,
        make_search_params,
):
    message = MagicMock()
    params = make_search_params(command=Command.START)

    message.body = params.model_dump_json().encode()

    search_service.start_monitoring = MagicMock()

    await search_service.search_handle(message)

    search_service.start_monitoring.assert_called_once_with(params)


@pytest.mark.asyncio
async def test_search_handle__stop_command__stops_search(
        search_service,
        make_search_params,
):
    message = MagicMock()
    params = make_search_params(command=Command.STOP)

    message.body = params.model_dump_json().encode()

    search_service.stop_search = MagicMock()

    await search_service.search_handle(message)

    search_service.stop_search.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_repository_handler__specific_card_id__gets_item():
    message = MagicMock()

    params = ItemParams(
        card_id="123",
        chat_id=456,
        query="iphone",
    )

    message.body = params.model_dump_json().encode()

    item = MagicMock()
    item.model_dump.return_value = {
        "card_id": "123",
        "chat_id": 456,
        "query": "iphone",
    }

    repository = MagicMock()
    repository.get_item = AsyncMock(return_value=[item])

    rabbit = MagicMock()
    rabbit.publish = AsyncMock()

    service = SearchService(
        repository=repository,
        scraper=MagicMock(),
        rabbit=rabbit,
        task_manager=MagicMock(),
    )

    await service.repository_handler(message)

    repository.get_item.assert_awaited_once_with(
        456,
        "123",
    )

    repository.get_items.assert_not_called()

    rabbit.publish.assert_awaited_once_with(
        queue="search_result",
        body={
            "items": [
                {
                    "card_id": "123",
                    "chat_id": 456,
                    "query": "iphone",
                },
            ],
        },
    )


@pytest.mark.asyncio
async def test_repository_handler__card_id_zero__gets_items_by_query():
    message = MagicMock()

    params = ItemParams(
        card_id="0",
        chat_id=456,
        query="iphone",
    )

    message.body = params.model_dump_json().encode()

    item = MagicMock()
    item.model_dump.return_value = {
        "card_id": "123",
        "chat_id": 456,
        "query": "iphone",
    }

    repository = MagicMock()
    repository.get_items = AsyncMock(return_value=[item])

    rabbit = MagicMock()
    rabbit.publish = AsyncMock()

    service = SearchService(
        repository=repository,
        scraper=MagicMock(),
        rabbit=rabbit,
        task_manager=MagicMock(),
    )

    await service.repository_handler(message)

    repository.get_items.assert_awaited_once_with(
        456,
        "iphone",
    )

    repository.get_item.assert_not_called()
    rabbit.publish.assert_awaited_once_with(
        queue="search_result",
        body={
            "items": [
                {
                    "card_id": "123",
                    "chat_id": 456,
                    "query": "iphone",
                },
            ],
        },
    )


@pytest.mark.asyncio
async def test_repository_handler__no_items__publishes_empty_result():
    message = MagicMock()

    params = ItemParams(
        card_id="0",
        chat_id=456,
        query="iphone",
    )

    message.body = params.model_dump_json().encode()

    repository = MagicMock()
    repository.get_items = AsyncMock(return_value=[])

    rabbit = MagicMock()
    rabbit.publish = AsyncMock()

    service = SearchService(
        repository=repository,
        scraper=MagicMock(),
        rabbit=rabbit,
        task_manager=MagicMock(),
    )

    await service.repository_handler(message)

    rabbit.publish.assert_awaited_once_with(
        queue="search_result",
        body={"items": []},
    )


def test_start_monitoring__search_params__starts_task():
    task_manager = MagicMock()

    service = SearchService(
        repository=MagicMock(),
        scraper=MagicMock(),
        rabbit=MagicMock(),
        task_manager=task_manager,
    )

    params = MagicMock()
    monitoring = MagicMock()

    service.run_monitoring = MagicMock(
        return_value=monitoring,
    )

    service.start_monitoring(params)

    service.run_monitoring.assert_called_once_with(params)

    task_manager.start.assert_called_once_with(
        params.chat_id,
        monitoring,
    )


def test_stop_search__chat_id__cancels_task_and_clears_seen_cards():
    task_manager = MagicMock()
    scraper = MagicMock()

    service = SearchService(
        repository=MagicMock(),
        scraper=scraper,
        rabbit=MagicMock(),
        task_manager=task_manager,
    )

    service.stop_search(123)

    task_manager.cancel.assert_called_once_with(123)
    scraper.clear_seen_cards.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_process_new_items__no_new_items__does_nothing():
    scraper = MagicMock()
    scraper.find_new_items = AsyncMock(return_value=[])

    rabbit = MagicMock()
    rabbit.publish = AsyncMock()

    repository = MagicMock()
    repository.insert_items = AsyncMock()

    service = SearchService(
        repository=repository,
        scraper=scraper,
        rabbit=rabbit,
        task_manager=MagicMock(),
    )

    params = MagicMock()

    await service.process_new_items(params)

    scraper.find_new_items.assert_awaited_once_with(params)
    rabbit.publish.assert_not_awaited()
    repository.insert_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_new_items__new_items__publishes_and_stores_items():
    params = MagicMock()
    params.chat_id = 123

    item = MagicMock()
    item.model_dump.return_value = {
        "card_id": "456",
        "chat_id": 123,
        "query": "iphone",
    }

    scraper = MagicMock()
    scraper.find_new_items = AsyncMock(
        return_value=[item],
    )

    rabbit = MagicMock()
    rabbit.publish = AsyncMock()

    repository = MagicMock()
    repository.insert_items = AsyncMock()

    service = SearchService(
        repository=repository,
        scraper=scraper,
        rabbit=rabbit,
        task_manager=MagicMock(),
    )

    await service.process_new_items(params)

    rabbit.publish.assert_awaited_once_with(
        queue="search_result",
        body={
            "items": [
                {
                    "card_id": "456",
                    "chat_id": 123,
                    "query": "iphone",
                }
            ],
        },
    )

    repository.insert_items.assert_awaited_once_with(
        123,
        [item],
    )


@pytest.mark.asyncio
async def test_run_monitoring__zero_timeout__processes_items_once(
        mocker,
        search_service,
        make_search_params,
):
    search_service.process_new_items = AsyncMock()
    sleep = mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    params = make_search_params(timeout=0)

    await search_service.run_monitoring(params)

    search_service.process_new_items.assert_awaited_once_with(params)
    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_monitoring__cancelled_during_processing__stops_monitoring(
        search_service,
        make_search_params,
):
    search_service.process_new_items = AsyncMock(
        side_effect=asyncio.CancelledError,
    )
    params = make_search_params(timeout=10)

    await search_service.run_monitoring(params)

    search_service.process_new_items.assert_awaited_once_with(params)


@pytest.mark.asyncio
async def test_run_monitoring__periodic_timeout__processes_repeatedly(
        mocker,
        search_service,
        make_search_params,
):
    params = make_search_params(timeout=10)

    search_service.process_new_items = AsyncMock(
        side_effect=[
            None,
            asyncio.CancelledError,
        ],
    )

    sleep = mocker.patch(
        "asyncio.sleep",
        new_callable=AsyncMock,
    )

    await search_service.run_monitoring(params)

    assert search_service.process_new_items.await_count == 2
    sleep.assert_awaited_once_with(600)


@pytest.mark.asyncio
async def test_run_monitoring__timeout__sleeps_between_searches(
        mocker,
        search_service,
        make_search_params,
):
    search_service.process_new_items = AsyncMock()

    sleep = mocker.patch(
        "asyncio.sleep",
        new_callable=AsyncMock,
        side_effect=asyncio.CancelledError,
    )

    params = make_search_params(timeout=10)
    await search_service.run_monitoring(params)

    search_service.process_new_items.assert_awaited_once_with(params)
    sleep.assert_awaited_once_with(600)


@pytest.mark.asyncio
async def test_run_monitoring__unexpected_error__logs_exception(
        mocker,
        search_service,
        make_search_params,
):
    search_service.process_new_items = mocker.AsyncMock(
        side_effect=Exception("scraper failed"),
    )

    params = make_search_params(timeout=10, chat_id=123)

    logger = mocker.patch("services.search_control.logger")

    await search_service.run_monitoring(params)

    search_service.process_new_items.assert_awaited_once_with(params)

    logger.exception.assert_called_once_with(
        "Monitoring failed for user %s",
        123,
    )


@pytest.mark.asyncio
async def test_run_monitoring__cancelled__logs_stop(
        mocker,
        search_service,
        make_search_params,
):
    search_service.process_new_items = mocker.AsyncMock(
        side_effect=asyncio.CancelledError,
    )
    params = make_search_params(timeout=10, chat_id=123)
    logger = mocker.patch("services.search_control.logger")

    await search_service.run_monitoring(params)

    logger.info.assert_called_once_with(
        "Stopped monitoring user %s",
        123,
    )

    logger.exception.assert_not_called()
