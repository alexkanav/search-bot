from typing import Any, Callable
from unittest.mock import MagicMock, AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError

from models.items import ItemCard
from models.search import SearchResult
from services.notification_service import notify_user


@pytest.fixture
def make_item() -> Callable[..., ItemCard]:
    def wrap(**kwargs: Any) -> ItemCard:
        defaults = {
            "chat_id": 456,
            "query": "Phone",
            "card_id": "123",
            "description": "iPhone 15",
            "image_url": "https://example.com/image.jpg",
            "price": 800,
            "location_and_date": "Kyiv, today",
            "item_url": "https://example.com",
        }

        return ItemCard.model_validate(defaults | kwargs)

    return wrap


@pytest.mark.asyncio
async def test_notify_user__image_exists__sends_photo(make_item):
    item = make_item()
    search_result = SearchResult(items=[item])

    message = MagicMock()
    bot = AsyncMock()

    message.body = search_result.model_dump_json().encode()

    await notify_user(message, bot)

    bot.send_photo.assert_awaited_once()
    bot.send_message.assert_not_awaited()

    call = bot.send_photo.await_args
    assert call.kwargs["chat_id"] == item.chat_id
    assert call.kwargs["photo"] == str(item.image_url)
    assert f"ID: {item.card_id}" in call.kwargs["caption"]
    assert f"Товар: {item.query}" in call.kwargs["caption"]
    assert f"Опис: {item.description}" in call.kwargs["caption"]
    assert f"Ціна: {item.price}" in call.kwargs["caption"]
    assert f"Опубліковано: {item.location_and_date}" in call.kwargs["caption"]
    assert f"Дивитись на сайті: {item.item_url}" in call.kwargs["caption"]


@pytest.mark.asyncio
async def test_notify_user__no_image__sends_message(make_item):
    item = make_item(image_url=None)
    search_result = SearchResult(items=[item])

    message = MagicMock()
    bot = AsyncMock()

    message.body = search_result.model_dump_json().encode()

    await notify_user(message, bot)

    bot.send_photo.assert_not_awaited()
    bot.send_message.assert_awaited_once()

    call = bot.send_message.await_args
    assert call.kwargs["chat_id"] == item.chat_id
    assert f"ID: {item.card_id}" in call.kwargs["text"]
    assert f"Товар: {item.query}" in call.kwargs["text"]
    assert f"Ціна: {item.price}" in call.kwargs["text"]
    assert f"Дивитись на сайті: {item.item_url}" in call.kwargs["text"]


@pytest.mark.asyncio
async def test_notify_user__multiple_items__notifies_each_item(make_item):
    item1 = make_item(card_id="111", image_url="https://example.com/image1.jpg")
    item2 = make_item(card_id="222", image_url=None)
    search_result = SearchResult(items=[item1, item2])

    message = MagicMock()
    bot = AsyncMock()

    message.body = search_result.model_dump_json().encode()

    await notify_user(message, bot)

    bot.send_photo.assert_awaited_once()
    photo_call = bot.send_photo.await_args
    assert photo_call.kwargs["chat_id"] == item1.chat_id
    assert f"ID: {item1.card_id}" in photo_call.kwargs["caption"]
    assert photo_call.kwargs["photo"] == str(item1.image_url)

    bot.send_message.assert_awaited_once()
    message_call = bot.send_message.await_args
    assert message_call.kwargs["chat_id"] == item2.chat_id
    assert f"ID: {item2.card_id}" in message_call.kwargs["text"]


@pytest.mark.asyncio
async def test_notify_user__photo_bad_request__falls_back_to_message(mocker, make_item):
    item = make_item()
    search_result = SearchResult(items=[item])

    message = MagicMock()
    bot = AsyncMock()

    message.body = search_result.model_dump_json().encode()

    bot.send_photo.side_effect = TelegramBadRequest(
        method=MagicMock(),
        message="Bad Request: wrong file",
    )

    mock_logger = mocker.patch("services.notification_service.logger")

    await notify_user(message, bot)

    bot.send_photo.assert_awaited_once()
    bot.send_message.assert_awaited_once()

    mock_logger.warning.assert_called_once_with(
        "Failed to send image for card %s, "
        "falling back to text message",
        item.card_id,
    )

    call = bot.send_message.await_args

    assert call.kwargs["chat_id"] == item.chat_id
    assert f"ID: {item.card_id}" in call.kwargs["text"]


@pytest.mark.asyncio
async def test_notify_user__message_api_error__handles_exception(mocker, make_item):
    item = make_item(image_url=None)
    search_result = SearchResult(items=[item])

    message = MagicMock()
    bot = AsyncMock()

    message.body = search_result.model_dump_json().encode()

    bot.send_message.side_effect = TelegramAPIError(
        method=MagicMock(),
        message="Telegram API error",
    )

    mock_logger = mocker.patch("services.notification_service.logger")

    await notify_user(message, bot)

    bot.send_message.assert_awaited_once()
    mock_logger.exception.assert_called_once_with(
        "Failed to notify user about card %s",
        item.card_id,
    )
