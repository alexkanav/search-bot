import pytest

from config import MARKETPLACE_URLS, MIN_SEARCH_TIMEOUT_MINUTES, MAX_SEARCH_TIMEOUT_MINUTES
from constants import (ALL_UKRAINE, ALL_REGION, CANCEL_BUTTON, SEARCH_BUTTON, UNSUPPORTED_BUTTON_MESSAGE)
from constants import SELECT_REGION
from handlers.data_collector import (
    process_marketplace,
    process_price,
    process_search_scope,
    process_region,
    process_location,
    process_action,
    process_timeout,
)
from states import SearchFlow
from utils.enums import Command


@pytest.fixture
def message(mocker):
    message = mocker.AsyncMock()
    message.text = "ABC"
    message.chat.id = 123

    return message


@pytest.fixture
def state(mocker):
    state = mocker.AsyncMock()
    state.get_data.return_value = {}

    return state


@pytest.fixture
def search_service(mocker):
    return mocker.AsyncMock()


@pytest.fixture
def rabbitmq(mocker):
    return mocker.AsyncMock()


@pytest.mark.asyncio
async def test_process_marketplace__valid_marketplace__stores_url_and_selects_price(
        message,
        state,
):
    message.text = next(iter(MARKETPLACE_URLS))

    await process_marketplace(message, state)

    url = MARKETPLACE_URLS[message.text]

    state.update_data.assert_awaited_once_with(url=url)
    state.set_state.assert_awaited_once_with(SearchFlow.selecting_price)

    message.answer.assert_awaited_once()

    kwargs = message.answer.call_args.kwargs
    assert kwargs["text"] == "Максимальна ціна?"


@pytest.mark.asyncio
async def test_process_marketplace__unsupported_marketplace__shows_error(
        message,
        state,
):
    message.text = "Unknown marketplace"

    await process_marketplace(message, state)

    message.answer.assert_awaited_once_with(UNSUPPORTED_BUTTON_MESSAGE)

    state.update_data.assert_not_awaited()
    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_price__valid_price__stores_price_and_selects_scope(
        message,
        state,
):
    message.text = "1500"

    await process_price(message, state)

    state.update_data.assert_awaited_once_with(price=1500)

    state.set_state.assert_awaited_once_with(SearchFlow.selecting_search_scope)

    message.answer.assert_awaited_once()

    kwargs = message.answer.call_args.kwargs

    assert kwargs["text"] == "Оберіть регіон для пошуку"


@pytest.mark.asyncio
async def test_process_price__non_numeric__shows_error(
        message,
        state,
):
    message.text = "1500 грн"

    await process_price(message, state)

    message.answer.assert_awaited_once_with("Помилка. Ви ввели не число.")

    state.update_data.assert_not_awaited()
    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_price__spaces_around_number__accepts_price(
        message,
        state,
):
    message.text = " 1500 "

    await process_price(message, state)

    state.update_data.assert_awaited_once_with(price=1500)


@pytest.mark.asyncio
async def test_process_search_scope__all_ukraine__clears_region_and_location(
        mocker,
        message,
        state,
        search_service,
):
    message.text = ALL_UKRAINE
    mock_ask_for_action = mocker.patch("handlers.data_collector.ask_for_action")
    await process_search_scope(
        message,
        state,
        search_service,
    )

    state.update_data.assert_awaited_once_with(
        region=None,
        location=None,
    )
    mock_ask_for_action.assert_awaited_once_with(
        message,
        state,
    )

    search_service.get_regions.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_search_scope__regions_found__selects_region(
        mocker,
        message,
        state,
        search_service,
):
    mock_ask_for_action = mocker.patch("handlers.data_collector.ask_for_action")

    keyboard = mocker.MagicMock()
    mock_keyboard = mocker.patch(
        "handlers.data_collector.keyboards.make_multiline_keyboard",
        return_value=keyboard,
    )

    message.text = SELECT_REGION

    state.get_data.return_value = {"url": "https://example.com"}

    regions = ["Kyiv", "Lviv", "Odesa"]
    search_service.get_regions.return_value = regions

    await process_search_scope(message, state, search_service)

    search_service.get_regions.assert_awaited_once_with("https://example.com")

    mock_keyboard.assert_called_once_with(regions, 4)

    state.update_data.assert_awaited_once_with(regions=regions)
    state.set_state.assert_awaited_once_with(SearchFlow.selecting_region)

    mock_ask_for_action.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_search_scope__no_regions__searches_all_regions(
        mocker,
        message,
        state,
        search_service,
):
    mock_ask_for_action = mocker.patch("handlers.data_collector.ask_for_action")

    message.text = SELECT_REGION

    state.get_data.return_value = {"url": "https://example.com"}

    search_service.get_regions.return_value = []

    await process_search_scope(message, state, search_service)

    search_service.get_regions.assert_awaited_once_with("https://example.com")

    state.update_data.assert_awaited_once_with(
        region=None,
        location=None,
    )

    mock_ask_for_action.assert_awaited_once_with(message, state)

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_search_scope__unsupported_scope__shows_error(
        message,
        state,
        search_service,
):
    message.text = "Unknown"

    await process_search_scope(message, state, search_service)

    message.answer.assert_awaited_once_with(UNSUPPORTED_BUTTON_MESSAGE)

    search_service.get_regions.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_region__unsupported_region__shows_error(
        message,
        state,
        search_service,
):
    message.text = "Kharkiv"

    state.get_data.return_value = {
        "regions": ["Kyiv", "Lviv"],
        "url": "https://example.com",
    }

    await process_region(message, state, search_service)

    message.answer.assert_awaited_once_with(UNSUPPORTED_BUTTON_MESSAGE)

    search_service.get_locations.assert_not_awaited()
    state.update_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_region__locations_found__selects_location(
        mocker,
        message,
        state,
        search_service,
):
    keyboard = mocker.MagicMock()
    mock_keyboard = mocker.patch(
        "handlers.data_collector.keyboards.make_multiline_keyboard",
        return_value=keyboard,
    )

    message.text = "Kyiv"

    state.get_data.return_value = {
        "regions": ["Kyiv", "Lviv"],
        "url": "https://example.com",
    }

    locations = ["Kyiv", "Brovary", "Boryspil"]
    search_service.get_locations.return_value = locations

    await process_region(message, state, search_service)

    state.update_data.assert_any_await(region="Kyiv")

    search_service.get_locations.assert_awaited_once_with(
        "https://example.com",
        "Kyiv",
    )

    mock_keyboard.assert_called_once_with(
        [ALL_REGION, *locations],
        4,
    )

    state.set_state.assert_awaited_once_with(SearchFlow.selecting_location)


@pytest.mark.asyncio
async def test_process_region__no_locations__searches_whole_region(
        mocker,
        message,
        state,
        search_service,
):
    mock_ask_for_action = mocker.patch("handlers.data_collector.ask_for_action")

    message.text = "Kyiv"

    state.get_data.return_value = {
        "regions": ["Kyiv"],
        "url": "https://example.com",
    }

    search_service.get_locations.return_value = []

    await process_region(message, state, search_service)

    search_service.get_locations.assert_awaited_once_with(
        "https://example.com",
        "Kyiv",
    )

    state.update_data.assert_any_await(region="Kyiv")

    state.update_data.assert_any_await(location=None)

    mock_ask_for_action.assert_awaited_once_with(message, state)

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_location__all_region__sets_location_none(
        mocker,
        message,
        state,
):
    mock_ask_for_action = mocker.patch("handlers.data_collector.ask_for_action")

    message.text = ALL_REGION

    await process_location(message, state)

    state.update_data.assert_awaited_once_with(location=None)

    mock_ask_for_action.assert_awaited_once_with(message, state)


@pytest.mark.asyncio
async def test_process_location__valid_location__stores_location(
        mocker,
        message,
        state,
):
    mock_ask_for_action = mocker.patch("handlers.data_collector.ask_for_action")

    message.text = "Brovary"

    state.get_data.return_value = {"locations": ["Kyiv", "Brovary", "Boryspil"]}

    await process_location(message, state)

    state.update_data.assert_awaited_once_with(location="Brovary")

    mock_ask_for_action.assert_awaited_once_with(message, state)


@pytest.mark.asyncio
async def test_process_location__unsupported_location__shows_error(
        message,
        state,
):
    message.text = "Unknown"

    state.get_data.return_value = {"locations": ["Kyiv", "Brovary"]}

    await process_location(message, state)

    message.answer.assert_awaited_once_with(UNSUPPORTED_BUTTON_MESSAGE)

    state.update_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_action__search__selects_timeout(
        message,
        state,
):
    message.text = SEARCH_BUTTON

    await process_action(message, state)

    message.answer.assert_awaited_once()

    state.set_state.assert_awaited_once_with(SearchFlow.selecting_timeout)


@pytest.mark.asyncio
async def test_process_action__cancel__stops_search(
        mocker,
        message,
        state,
):
    mock_stop_search = mocker.patch("handlers.data_collector.stop_search")

    message.text = CANCEL_BUTTON

    await process_action(message, state)

    mock_stop_search.assert_awaited_once_with(message, state)


@pytest.mark.asyncio
async def test_process_action__unsupported_action__shows_error(
        message,
        state,
):
    message.text = "Unknown"

    await process_action(message, state)

    message.answer.assert_awaited_once_with(UNSUPPORTED_BUTTON_MESSAGE)

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_timeout__non_numeric__shows_error(
        message,
        state,
        rabbitmq,
):
    message.text = "abc"

    await process_timeout(message, state, rabbitmq)

    message.answer.assert_awaited_once_with("Помилка. Ви ввели не число.")

    rabbitmq.publish.assert_not_awaited()
    state.clear.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value",
    [
        str(MIN_SEARCH_TIMEOUT_MINUTES - 1),
        str(MAX_SEARCH_TIMEOUT_MINUTES + 1),
    ],
    ids=[
        "below_minimum",
        "above_maximum",
    ],
)
async def test_process_timeout__invalid_timeout__shows_error(
        value,
        message,
        state,
        rabbitmq,
):
    message.text = value

    await process_timeout(message, state, rabbitmq)

    message.answer.assert_awaited_once_with(
        "Помилка. Вкажіть коректний таймаут у хвилинах: "
        f"0 або число між {MIN_SEARCH_TIMEOUT_MINUTES} та {MAX_SEARCH_TIMEOUT_MINUTES}.",

    )
    message.answer.assert_awaited_once()

    rabbitmq.publish.assert_not_awaited()
    state.clear.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value",
    [
        "0",
        str(MIN_SEARCH_TIMEOUT_MINUTES),
        str(MIN_SEARCH_TIMEOUT_MINUTES + 1),
        str(MAX_SEARCH_TIMEOUT_MINUTES - 1),
        str(MAX_SEARCH_TIMEOUT_MINUTES),
    ],
    ids=[
        "zero",
        "minimum",
        "above_minimum",
        "below_maximum",
        "maximum"
    ],
)
async def test_process_timeout__valid_timeout__publishes_search(
        value,
        message,
        state,
        rabbitmq,
):
    message.text = value

    state.get_data.return_value = {
        "url": "https://example.com",
        "query": "iphone",
        "region": "Kyiv",
        "location": "Brovary",
        "price": 1000,
    }

    await process_timeout(message, state, rabbitmq)

    rabbitmq.publish.assert_awaited_once()

    kwargs = rabbitmq.publish.call_args.kwargs

    assert kwargs["queue"] == "search_request"

    request = kwargs["body"]

    assert request["command"] == Command.START
    assert request["chat_id"] == 123
    assert request["url"] == "https://example.com/"
    assert request["query"] == "iphone"
    assert request["region"] == "Kyiv"
    assert request["location"] == "Brovary"
    assert request["max_price"] == 1000
    assert request["timeout"] == int(value)

    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_timeout__all_ukraine__publishes_search_without_region(
        message,
        state,
        rabbitmq,
):
    message.text = "0"

    state.get_data.return_value = {
        "url": "https://example.com",
        "query": "iphone",
        "price": 1000,
        "region": None,
        "location": None,
    }

    await process_timeout(message, state, rabbitmq)

    rabbitmq.publish.assert_awaited_once()

    request = rabbitmq.publish.call_args.kwargs["body"]

    assert request["region"] is None
    assert request["location"] is None
