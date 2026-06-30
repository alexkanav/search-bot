from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from infrastructure.mongo_repository import ItemRepository
from models.search_params import SearchParams
from scraper.marketplace_scraper import MarketplaceScraper
from services.item_monitor import run_monitoring
from services.task_manager import TaskManager
from telegram import keyboards
from telegram.constants import SEARCH_BUTTON, CANCEL_BUTTON, STOP_BUTTON
from telegram.states import SearchFlow


async def start_search_flow(message: Message, state: FSMContext) -> None:
    await message.answer("Що шукаєте?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(SearchFlow.selecting_item)


async def cancel_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(text="Дію відхилено.", reply_markup=ReplyKeyboardRemove())


async def stop_search(
        message: Message,
        state: FSMContext,
        task_manager: TaskManager,
) -> None:
    task_manager.cancel(message.from_user.id)
    await state.clear()

    await message.answer(
        text="Пошук зупинено.\nЗвертайтесь ще, в мене немає вихідних)",
        reply_markup=ReplyKeyboardRemove(),
    )


async def ask_for_action(message: Message, state: FSMContext) -> None:
    await message.answer(
        text="Оберіть дію",
        reply_markup=keyboards.make_row_keyboard([SEARCH_BUTTON, CANCEL_BUTTON]),
    )
    await state.set_state(SearchFlow.confirming_search)


async def start_monitoring(
        message: Message,
        repository: ItemRepository,
        scraper: MarketplaceScraper,
        task_manager: TaskManager,
        search_params: SearchParams,
) -> None:
    await message.answer(
        text="Почекайте, шукаю усі варіанти ...",
        reply_markup=keyboards.make_row_keyboard([STOP_BUTTON]),
    )

    task_manager.start(
        message.from_user.id,
        run_monitoring(repository, scraper, message, search_params)
    )
