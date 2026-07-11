from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramBadRequest

from models.item_card import ItemCard
from services.telegram_service import notify_user


@pytest.fixture
def message():
    message = MagicMock()
    message.chat.id = 123
    message.bot = AsyncMock()
    message.answer = AsyncMock()
    return message


@pytest.fixture
def card():
    return ItemCard(
        query="iPhone",
        card_id="123",
        description="Excellent condition",
        image_url="https://example.com/image.jpg",
        price=500,
        location_and_date="Kyiv, today",
        item_url="https://example.com/item",
    )


@pytest.fixture
def expected_text(card):
    return (
        f"ID: {card.card_id}\n"
        f"Товар: {card.query}\n"
        f"Опис: {card.description}\n"
        f"Ціна: {card.price}\n"
        f"Опубліковано: {card.location_and_date}\n"
        f"Дивитись на сайті: {card.item_url}\n"
    )


@pytest.mark.asyncio
async def test_notify_user__image_exists__sends_photo(message, card, expected_text):
    await notify_user(message, card)

    message.bot.send_photo.assert_awaited_once_with(
        chat_id=123,
        photo="https://example.com/image.jpg",
        caption=expected_text,
    )

    message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_notify_user__image_missing__sends_text_message(message, card, expected_text):
    card.image_url = None

    await notify_user(message, card)

    message.answer.assert_awaited_once_with(expected_text)
    message.bot.send_photo.assert_not_awaited()


@pytest.mark.asyncio
async def test_notify_user__send_photo_raises_bad_request__falls_back_to_text_message(message, card, expected_text):
    message.bot.send_photo.side_effect = TelegramBadRequest(
        method=MagicMock(),
        message="Bad Request",
    )

    await notify_user(message, card)

    message.bot.send_photo.assert_awaited_once_with(
        chat_id=123,
        photo="https://example.com/image.jpg",
        caption=expected_text,
    )

    message.answer.assert_awaited_once_with(expected_text)
