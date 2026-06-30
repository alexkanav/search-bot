from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from models.item_card import ItemCard


async def notify_user(message: Message, card: ItemCard) -> None:
    text = (
        f"ID: {card.card_id}\n"
        f"Товар: {card.query}\n"
        f"Опис: {card.description}\n"
        f"Ціна: {card.price}\n"
        f"Опубліковано: {card.location_and_date}\n"
        f"Дивитись на сайті: {str(card.item_url)}\n"
    )
    try:
        if card.image_url:
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=str(card.image_url),
                caption=text,
            )
        else:
            await message.answer(text)

    except TelegramBadRequest:
        await message.answer(text)
