from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from services.search_control import start_search_flow, cancel_search, stop_search
from services.task_manager import TaskManager
from telegram.constants import STOP_BUTTON

router = Router()


@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext) -> None:
    await start_search_flow(message, state)


@router.message(Command("cancel"))
@router.message(F.text.lower() == "cancel")
async def cancel_cmd(message: Message, state: FSMContext) -> None:
    await cancel_search(message, state)


@router.message(Command("stop"))
@router.message(F.text == STOP_BUTTON)
async def stop_cmd(message: Message, state: FSMContext, task_manager: TaskManager) -> None:
    await stop_search(message, state, task_manager)
