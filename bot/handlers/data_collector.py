from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

import keyboards
from config import MARKETPLACE_URLS, MIN_SEARCH_TIMEOUT_MINUTES, MAX_SEARCH_TIMEOUT_MINUTES
from constants import SEARCH_BUTTON, CANCEL_BUTTON, ALL_UKRAINE, SELECT_REGION, ALL_REGION, UNSUPPORTED_BUTTON_MESSAGE
from infrastructure.rabbitmq import RabbitMQ
from models.search import SearchRequest
from services.search_control import stop_search, ask_for_action
from services.search_service import SearchService
from states import SearchFlow
from utils.enums import Command

router = Router()


@router.message(SearchFlow.selecting_marketplace, F.text)
async def process_marketplace(message: Message, state: FSMContext) -> None:
    url = MARKETPLACE_URLS.get(message.text)
    if url is None:
        await message.answer(UNSUPPORTED_BUTTON_MESSAGE)
        return

    await state.update_data(url=url)

    await message.answer(text="Максимальна ціна?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(SearchFlow.selecting_price)


@router.message(SearchFlow.selecting_price, F.text)
async def process_price(message: Message, state: FSMContext) -> None:
    price_raw = message.text.strip()
    if not price_raw.isdigit():
        await message.answer("Помилка. Ви ввели не число.")
        return

    price = int(price_raw)
    await state.update_data(price=price)

    await message.answer(
        text="Оберіть регіон для пошуку",
        reply_markup=keyboards.make_row_keyboard([ALL_UKRAINE, SELECT_REGION])
    )
    await state.set_state(SearchFlow.selecting_search_scope)


@router.message(SearchFlow.selecting_search_scope, F.text)
async def process_search_scope(
        message: Message,
        state: FSMContext,
        search_service: SearchService,
) -> None:
    if message.text == ALL_UKRAINE:
        await state.update_data(region=None, location=None)
        await ask_for_action(message, state)
        return

    if message.text == SELECT_REGION:
        data = await state.get_data()
        url = data["url"]
        await message.answer(text="Зачекайте, шукаю доступні регіони ...", reply_markup=ReplyKeyboardRemove())

        regions = await search_service.get_regions(url)
        if not regions:
            await message.answer("Доступні регіони не знайдено. Буду шукати по всіх регіонах")
            await state.update_data(region=None, location=None)
            await ask_for_action(message, state)
            return

        await message.answer(
            "Виберіть область:",
            reply_markup=keyboards.make_multiline_keyboard(regions, 4),
        )
        await state.update_data(regions=regions)
        await state.set_state(SearchFlow.selecting_region)
        return

    await message.answer(UNSUPPORTED_BUTTON_MESSAGE)


@router.message(SearchFlow.selecting_region, F.text)
async def process_region(
        message: Message,
        state: FSMContext,
        search_service: SearchService,
) -> None:
    data = await state.get_data()
    regions = data["regions"]

    if message.text not in regions:
        await message.answer(UNSUPPORTED_BUTTON_MESSAGE)
        return

    region = message.text
    await state.update_data(region=region)

    await message.answer(text="Зачекайте, шукаю доступні локації ...", reply_markup=ReplyKeyboardRemove())
    url = data["url"]

    locations = await search_service.get_locations(url, region)
    if not locations:
        await message.answer("Доступні локації не знайдено. Буду шукати по всій області")
        await state.update_data(location=None)
        await ask_for_action(message, state)
        return

    await message.answer(
        "Виберіть локацію:",
        reply_markup=keyboards.make_multiline_keyboard([ALL_REGION] + locations, 4),
    )
    await state.update_data(locations=locations)
    await state.set_state(SearchFlow.selecting_location)


@router.message(SearchFlow.selecting_location, F.text)
async def process_location(message: Message, state: FSMContext) -> None:
    if message.text == ALL_REGION:
        await state.update_data(location=None)
        await ask_for_action(message, state)
        return

    data = await state.get_data()
    locations = data["locations"]

    if message.text not in locations:
        await message.answer(UNSUPPORTED_BUTTON_MESSAGE)
        return

    await state.update_data(location=message.text)
    await ask_for_action(message, state)


@router.message(SearchFlow.confirming_search, F.text)
async def process_action(
        message: Message,
        state: FSMContext,
) -> None:
    if message.text == SEARCH_BUTTON:
        await message.answer(
            text=("Вкажіть періодичність пошуку "
                  f"(від {MIN_SEARCH_TIMEOUT_MINUTES} до {MAX_SEARCH_TIMEOUT_MINUTES}) у хвилинах? "
                  "Для одноразового пошуку вкажіть 0"
                  ),
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(SearchFlow.selecting_timeout)
        return

    if message.text == CANCEL_BUTTON:
        await stop_search(message, state)
        return

    await message.answer(UNSUPPORTED_BUTTON_MESSAGE)


@router.message(SearchFlow.selecting_timeout, F.text)
async def process_timeout(
        message: Message,
        state: FSMContext,
        rabbitmq: RabbitMQ,
) -> None:
    timeout_text = message.text.strip()

    if not timeout_text.isdigit():
        await message.answer(
            "Помилка. Ви ввели не число.",
        )
        return

    timeout = int(timeout_text)

    if timeout != 0 and not (MIN_SEARCH_TIMEOUT_MINUTES <= timeout <= MAX_SEARCH_TIMEOUT_MINUTES):
        await message.answer(
            "Помилка. Вкажіть коректний таймаут у хвилинах: "
            f"0 або число між {MIN_SEARCH_TIMEOUT_MINUTES} та {MAX_SEARCH_TIMEOUT_MINUTES}.",
        )
        return

    data = await state.get_data()
    search_params = SearchRequest(
        command=Command.START,
        chat_id=message.chat.id,
        url=data["url"],
        query=data["query"],
        region=data.get("region"),
        location=data.get("location"),
        max_price=data["price"],
        timeout=timeout,
    )
    await rabbitmq.publish(
        queue="search_request",
        body=search_params.model_dump(mode="json"),
    )

    await message.answer(
        "Зачекайте, шукаю усі варіанти...",
    )

    await state.clear()
