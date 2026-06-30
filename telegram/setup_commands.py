from aiogram import Bot
from aiogram.types import BotCommand

from telegram.constants import SEARCH_BUTTON, CANCEL_BUTTON, STOP_BUTTON


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description=SEARCH_BUTTON),
        BotCommand(command="cancel", description=CANCEL_BUTTON),
        BotCommand(command="stop", description=STOP_BUTTON),
    ])
