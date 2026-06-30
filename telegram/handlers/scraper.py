from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from config import MARKETPLACE_URLS
from infrastructure.mongo_repository import ItemRepository
from models.search_params import SearchParams
from scraper.marketplace_scraper import MarketplaceScraper
from services.search_control import start_monitoring, stop_search, ask_for_action
from services.task_manager import TaskManager
from telegram import keyboards
from telegram.constants import SEARCH_BUTTON, CANCEL_BUTTON, ALL_UKRAINE, SELECT_REGION, ALL_REGION, ERROR_MESSAGE
from telegram.states import SearchFlow

router = Router()


@router.message(SearchFlow.selecting_marketplace)
async def select_marketplace(message: Message, state: FSMContext) -> None:
    url = MARKETPLACE_URLS.get(message.text)
    if url is None:
        await message.answer(ERROR_MESSAGE)
        return

    await state.update_data(url=url)

    await message.answer(text="Максимальна ціна?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(SearchFlow.selecting_price)


@router.message(SearchFlow.selecting_price)
async def select_price(message: Message, state: FSMContext) -> None:
    price_raw = message.text.strip()
    if not price_raw.isdigit():
        await message.answer("Помилка. Ви ввели не число.")
        return

    price = int(price_raw)
    await state.update_data(price=price)

    await message.answer(
        text="Оберіть регіон пошуку",
        reply_markup=keyboards.make_row_keyboard([ALL_UKRAINE, SELECT_REGION])
    )
    await state.set_state(SearchFlow.selecting_search_scope)


@router.message(SearchFlow.selecting_search_scope)
async def handle_search_scope(message: Message, state: FSMContext, scraper: MarketplaceScraper) -> None:
    if message.text == ALL_UKRAINE:
        await ask_for_action(message, state)
        return

    if message.text == SELECT_REGION:
        data = await state.get_data()
        url = data["url"]
        await message.answer(text="Почекайте, шукаю доступні регіони ...", reply_markup=ReplyKeyboardRemove())

        regions = await scraper.get_regions(url)
        await message.answer(
            "Виберіть область:",
            reply_markup=keyboards.make_multiline_keyboard(regions, 4),
        )
        await state.update_data(regions=regions)
        await state.set_state(SearchFlow.selecting_region)
        return

    await message.answer(ERROR_MESSAGE)


@router.message(SearchFlow.selecting_region)
async def select_region(message: Message, state: FSMContext, scraper: MarketplaceScraper) -> None:
    data = await state.get_data()
    regions = data["regions"]

    if message.text not in regions:
        await message.answer(ERROR_MESSAGE)
        return

    region = message.text
    await state.update_data(region=region)

    await message.answer(text="Почекайте, шукаю доступні локації ...", reply_markup=ReplyKeyboardRemove())
    url = data["url"]
    locations = await scraper.get_locations(region, url)
    await message.answer(
        "Виберіть локацію:",
        reply_markup=keyboards.make_multiline_keyboard([ALL_REGION] + locations, 4),
    )
    await state.update_data(locations=locations)
    await state.set_state(SearchFlow.selecting_location)


@router.message(SearchFlow.selecting_location)
async def select_location(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    locations = data["locations"]

    if message.text not in locations:
        await message.answer(ERROR_MESSAGE)
        return

    await state.update_data(location=message.text)
    await ask_for_action(message, state)


@router.message(SearchFlow.confirming_search)
async def handle_action_selection(
        message: Message,
        state: FSMContext,
        task_manager: TaskManager
) -> None:
    if message.text == SEARCH_BUTTON:
        await message.answer(
            text="Вкажіть періодичність пошукових запитів (від 10 до 1000) у хвилинах? Для одноразового пошуку вкажіть 0",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(SearchFlow.selecting_timeout)
        return

    if message.text == CANCEL_BUTTON:
        await stop_search(message, state, task_manager)
        return

    await message.answer(ERROR_MESSAGE)


@router.message(SearchFlow.selecting_timeout)
async def select_timeout(
        message: Message,
        state: FSMContext,
        repository: ItemRepository,
        scraper: MarketplaceScraper,
        task_manager: TaskManager
) -> None:
    timeout_text = message.text

    if not timeout_text.isdigit():
        await message.answer(
            "Помилка. Ви ввели не число."
        )
        return

    timeout = int(timeout_text)

    if timeout != 0 and not (10 <= timeout <= 1000):
        await message.answer(
            "Помилка. Вкажіть коректний таймаут: 0 або число між 10 та 1000."
        )
        return

    data = await state.get_data()
    search_params = SearchParams(
        url=data["url"],
        query=data["query"],
        region=data.get("region"),
        location=data.get("location"),
        max_price=data["price"],
        timeout=timeout,
    )

    await start_monitoring(message, repository, scraper, task_manager, search_params)

    await state.clear()
