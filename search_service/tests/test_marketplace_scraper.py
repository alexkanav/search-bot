from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from config import SEARCH_RESULTS_TIMEOUT_MS
from models.items import ItemCard
from scraper.locators import SearchPageLocators
from scraper.marketplace_scraper import MarketplaceScraper


@pytest.fixture
def scraper():
    return MarketplaceScraper()


def test_init__creates_empty_scraper():
    scraper = MarketplaceScraper()

    assert scraper.browser is None
    assert scraper.context is None
    assert scraper.playwright is None
    assert scraper.seen_card_ids == {}


@pytest.mark.asyncio
async def test_create__starts_playwright_and_browser(mocker):
    playwright = AsyncMock()
    browser = AsyncMock()
    context = AsyncMock()
    mock_async_playwright = mocker.patch("scraper.marketplace_scraper.async_playwright")

    mock_async_playwright.return_value.start = mocker.AsyncMock(
        return_value=playwright
    )
    playwright.chromium.launch = mocker.AsyncMock(return_value=browser)
    browser.new_context = mocker.AsyncMock(return_value=context)

    scraper = await MarketplaceScraper.create()

    assert scraper.playwright is playwright
    assert scraper.browser is browser
    assert scraper.context is context

    mock_async_playwright.return_value.start.assert_awaited_once()

    playwright.chromium.launch.assert_awaited_once_with(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )

    browser.new_context.assert_awaited_once()


@pytest.mark.asyncio
async def test_close__started_scraper__closes_browser_and_playwright():
    scraper = MarketplaceScraper()

    scraper.browser = AsyncMock()
    scraper.playwright = AsyncMock()

    await scraper.close()

    scraper.browser.close.assert_awaited_once()
    scraper.playwright.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_close__not_started_scraper__does_nothing():
    scraper = MarketplaceScraper()

    await scraper.close()


@pytest.mark.asyncio
async def test_close__browser_only__closes_browser(scraper):
    scraper.browser = AsyncMock()

    await scraper.close()

    scraper.browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close__playwright_only__stops_playwright(scraper):
    scraper.playwright = AsyncMock()

    await scraper.close()

    scraper.playwright.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_page_session__scraper_not_started__raises_runtime_error(scraper):
    with pytest.raises(
            RuntimeError,
            match="Scraper has not been started.",
    ):
        async with scraper.page_session("https://example.com"):
            pass


@pytest.mark.asyncio
async def test_page_session__valid_context__opens_and_closes_page(scraper):
    page = AsyncMock()

    scraper.context = AsyncMock()
    scraper.context.new_page.return_value = page

    async with scraper.page_session("https://example.com") as result:
        assert result is page

    scraper.context.new_page.assert_awaited_once()
    page.goto.assert_awaited_once_with("https://example.com")
    page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_page_session__exception_inside_context__closes_page(scraper):
    page = AsyncMock()

    scraper.context = AsyncMock()
    scraper.context.new_page.return_value = page

    with pytest.raises(ValueError):
        async with scraper.page_session("https://example.com"):
            raise ValueError("test error")

    page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_page_session__goto_error__closes_page(scraper):
    page = AsyncMock()
    page.goto.side_effect = RuntimeError("navigation failed")

    scraper.context = AsyncMock()
    scraper.context.new_page.return_value = page

    with pytest.raises(RuntimeError, match="navigation failed"):
        async with scraper.page_session("https://example.com"):
            pass

    page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_regions__valid_page__returns_regions(scraper):
    page = MagicMock()
    buttons = MagicMock()

    scraper.context = AsyncMock()
    scraper.context.new_page = AsyncMock(return_value=page)

    page.goto = AsyncMock()
    page.close = AsyncMock()
    page.fill = AsyncMock()

    page.locator.return_value = buttons

    buttons.first.wait_for = AsyncMock()
    buttons.evaluate_all = AsyncMock(
        return_value=[
            "Київ область",
            "Львів область",
            None,
            "Одеса область",
        ]
    )

    result = await scraper.get_regions("https://example.com")

    assert result == [
        "Київ",
        "Львів",
        "Одеса",
    ]

    scraper.context.new_page.assert_awaited_once()
    page.goto.assert_awaited_once_with("https://example.com")
    page.fill.assert_awaited_once_with(
        SearchPageLocators.REGION_INPUT,
        "",
    )
    page.locator.assert_called_once_with(
        SearchPageLocators.REGION_BUTTON,
    )
    buttons.first.wait_for.assert_awaited_once()
    buttons.evaluate_all.assert_awaited_once_with(
        "(els, attr) => els.map(el => el.getAttribute(attr))",
        SearchPageLocators.REGION_BUTTON_ATTR,
    )
    page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_locations__valid_region__returns_locations(scraper):
    page = MagicMock()

    region_button = AsyncMock()
    locations = AsyncMock()

    scraper.context = AsyncMock()
    scraper.context.new_page.return_value = page

    page.goto = AsyncMock()
    page.close = AsyncMock()
    page.fill = AsyncMock()

    page.locator.return_value = locations

    def locator(selector):
        if selector == SearchPageLocators.REGION_TEXT.format("Kyiv"):
            return region_button

        if selector == SearchPageLocators.LOCATION_BUTTON:
            return locations

        return MagicMock()

    page.locator.side_effect = locator

    locations.first.wait_for = AsyncMock()
    locations.all_inner_texts.return_value = [
        "Kyiv",
        "Brovary",
        "Boryspil",
    ]

    result = await scraper.get_locations(
        "Kyiv",
        "https://example.com",
    )

    assert result == [
        "Kyiv",
        "Brovary",
        "Boryspil",
    ]

    region_button.first.wait_for.assert_awaited_once()
    region_button.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_cards__without_region__returns_cards(
        scraper,
        make_search_params,
):
    search_params = make_search_params()
    search_params.region = None

    page = MagicMock()
    page.fill = AsyncMock()

    cards = MagicMock()
    page.locator.return_value = cards
    cards.click = AsyncMock()
    cards.first.wait_for = AsyncMock()

    result = await scraper._search_cards(page, search_params)

    assert result is cards

    page.fill.assert_awaited_once_with(
        SearchPageLocators.SEARCH_FIELD,
        search_params.query,
    )

    page.locator.assert_any_call(
        SearchPageLocators.SEARCH_BUTTON
    )

    cards.first.wait_for.assert_awaited_once_with(
        timeout=SEARCH_RESULTS_TIMEOUT_MS
    )


@pytest.mark.asyncio
async def test_search_cards__region_and_location__selects_filters(
        scraper,
        make_search_params,
):
    search_params = make_search_params()
    page = MagicMock()
    page.fill = AsyncMock()
    cards = MagicMock()
    page.locator.return_value = cards
    page.get_by_text.return_value.click = AsyncMock()

    cards.click = AsyncMock()
    cards.first.wait_for = AsyncMock()

    result = await scraper._search_cards(page, search_params)
    assert result is cards

    page.fill.assert_awaited_once_with(
        SearchPageLocators.SEARCH_FIELD,
        search_params.query,
    )

    page.locator.assert_any_call(
        SearchPageLocators.REGION_INPUT
    )

    page.get_by_text.assert_any_call(search_params.region)
    page.get_by_text.assert_any_call(search_params.location)

    page.locator.assert_any_call(
        SearchPageLocators.SEARCH_BUTTON
    )


@pytest.mark.asyncio
async def test_extract_item__valid_card__returns_item(
        scraper,
        make_search_params,
):
    search_params = make_search_params()
    card = MagicMock()

    card.get_attribute = AsyncMock(return_value="12345")

    price_locator = AsyncMock()
    price_locator.text_content.return_value = "900"

    title_locator = AsyncMock()
    title_locator.text_content.return_value = "iPhone 13"

    location_locator = AsyncMock()
    location_locator.text_content.return_value = "Kyiv, today"

    link_locator = AsyncMock()
    link_locator.first.get_attribute.return_value = "/item/12345"

    image_locator = AsyncMock()
    image_locator.first.get_attribute.return_value = "/images/123.jpg"

    def locator(selector):
        if selector == SearchPageLocators.PRICE:
            return price_locator

        if selector == SearchPageLocators.TITLE_TAG:
            return title_locator

        if selector == SearchPageLocators.LOCATION_DATE:
            return location_locator

        if selector == SearchPageLocators.IMAGE_LINK:
            return image_locator

        if selector == "a":
            return link_locator

        return MagicMock()

    card.locator.side_effect = locator

    result = await scraper._extract_item(
        card,
        search_params,
        set(),
    )

    assert isinstance(result, ItemCard)

    assert result.chat_id == search_params.chat_id
    assert result.query == search_params.query
    assert result.card_id == "12345"
    assert result.description == "iPhone 13"
    assert result.price == 900
    assert result.location_and_date == "Kyiv, today"
    assert str(result.item_url) == "https://example.com/item/12345"
    assert str(result.image_url) == "https://example.com/images/123.jpg"


@pytest.mark.asyncio
async def test_extract_item__missing_card_id__returns_none(
        scraper,
        make_search_params,
):
    search_params = make_search_params()
    card = MagicMock()
    card.get_attribute = AsyncMock(return_value=None)

    result = await scraper._extract_item(
        card,
        search_params,
        set(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_extract_item__already_seen_card__returns_none(
        scraper,
        make_search_params,
):
    search_params = make_search_params()
    card = MagicMock()
    card.get_attribute = AsyncMock(return_value="12345")

    result = await scraper._extract_item(
        card,
        search_params,
        {"12345"},
    )

    assert result is None


@pytest.mark.asyncio
async def test_extract_item__price_above_max__returns_none(
        scraper,
        make_search_params,
):
    search_params = make_search_params()
    card = MagicMock()

    card.get_attribute = AsyncMock(return_value="12345")

    price_locator = AsyncMock()
    price_locator.text_content.return_value = str(search_params.max_price + 1)

    card.locator.return_value = price_locator

    result = await scraper._extract_item(
        card,
        search_params,
        set(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_extract_item__price_without_digits__uses_zero(
        scraper,
        make_search_params,
):
    search_params = make_search_params()
    card = MagicMock()

    card.get_attribute = AsyncMock(return_value="12345")

    price_locator = AsyncMock()
    price_locator.text_content.return_value = "договірна"

    title_locator = AsyncMock()
    title_locator.text_content.return_value = "iPhone"

    location_locator = AsyncMock()
    location_locator.text_content.return_value = "Kyiv"

    link_locator = AsyncMock()
    link_locator.first.get_attribute.return_value = "/item/123"

    image_locator = AsyncMock()
    image_locator.first.get_attribute.return_value = None

    def locator(selector):
        if selector == SearchPageLocators.PRICE:
            return price_locator
        if selector == SearchPageLocators.TITLE_TAG:
            return title_locator
        if selector == SearchPageLocators.LOCATION_DATE:
            return location_locator
        if selector == SearchPageLocators.IMAGE_LINK:
            return image_locator
        if selector == "a":
            return link_locator
        return MagicMock()

    card.locator.side_effect = locator

    result = await scraper._extract_item(
        card,
        search_params,
        set(),
    )

    assert result.price == 0


@pytest.mark.asyncio
async def test_extract_item__price_timeout__uses_zero(
        scraper,
        make_search_params,
):
    search_params = make_search_params()
    card = MagicMock()

    card.get_attribute = AsyncMock(return_value="12345")

    price_locator = AsyncMock()
    price_locator.text_content.side_effect = PlaywrightTimeoutError("Mocked locator")

    title_locator = AsyncMock()
    title_locator.text_content.return_value = "iPhone"

    location_locator = AsyncMock()
    location_locator.text_content.return_value = "Kyiv"

    link_locator = AsyncMock()
    link_locator.first.get_attribute.return_value = "/item/123"

    image_locator = AsyncMock()
    image_locator.first.get_attribute.return_value = None

    def locator(selector):
        if selector == SearchPageLocators.PRICE:
            return price_locator
        if selector == SearchPageLocators.TITLE_TAG:
            return title_locator
        if selector == SearchPageLocators.LOCATION_DATE:
            return location_locator
        if selector == SearchPageLocators.IMAGE_LINK:
            return image_locator
        if selector == "a":
            return link_locator
        return MagicMock()

    card.locator.side_effect = locator

    result = await scraper._extract_item(
        card,
        search_params,
        set(),
    )

    assert result is not None
    assert result.price == 0


@pytest.mark.asyncio
async def test_extract_item__item_data_timeout__returns_none(
        scraper,
        make_search_params,
):
    search_params = make_search_params()
    card = MagicMock()

    card.get_attribute = AsyncMock(return_value="12345")

    price_locator = AsyncMock()
    price_locator.text_content.return_value = "900"

    title_locator = AsyncMock()
    title_locator.text_content.side_effect = PlaywrightTimeoutError("Mocked locator")

    def locator(selector):
        if selector == SearchPageLocators.PRICE:
            return price_locator

        if selector == SearchPageLocators.TITLE_TAG:
            return title_locator

        return MagicMock()

    card.locator.side_effect = locator

    result = await scraper._extract_item(
        card,
        search_params,
        set(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_collect_new_items__new_cards__returns_items(
        scraper,
        make_search_params,
        make_item,
):
    search_params = make_search_params()
    item_1 = make_item(card_id="card-1")
    item_2 = make_item(card_id="card-2")

    cards = AsyncMock()
    cards.count.return_value = 2
    cards.nth = MagicMock(return_value=MagicMock())

    scraper._extract_item = AsyncMock(
        side_effect=[item_1, item_2]
    )

    result = await scraper._collect_new_items(
        cards,
        search_params,
    )

    assert result == [item_1, item_2]

    assert scraper.seen_card_ids[123] == {"card-1", "card-2"}

    assert scraper._extract_item.await_count == 2


@pytest.mark.asyncio
async def test_collect_new_items__item_not_extracted__skips_it(
        scraper,
        make_search_params,
        make_item,
):
    search_params = make_search_params()
    cards = AsyncMock()
    cards.nth = MagicMock(return_value=MagicMock())
    cards.count.return_value = 2

    item = make_item()

    scraper._extract_item = AsyncMock(
        side_effect=[None, item]
    )

    result = await scraper._collect_new_items(
        cards,
        search_params,
    )

    assert result == [item]
    assert scraper.seen_card_ids[123] == {"card-1"}


@pytest.mark.asyncio
async def test_collect_new_items__different_chats__keeps_separate_seen_ids(
        scraper,
        make_search_params,
        make_item,
):
    cards = AsyncMock()
    cards.nth = MagicMock(return_value=MagicMock())
    cards.count.return_value = 1

    params1 = make_search_params(chat_id=1)
    params2 = make_search_params(chat_id=2)
    item1 = make_item(card_id="10")
    item2 = make_item(card_id="10")

    scraper._extract_item = AsyncMock(
        side_effect=[item1, item2]
    )

    await scraper._collect_new_items(cards, params1)
    await scraper._collect_new_items(cards, params2)

    assert scraper.seen_card_ids == {
        1: {"10"},
        2: {"10"},
    }


@pytest.mark.asyncio
async def test_find_new_items__searches_and_collects(
        scraper,
        make_search_params,
):
    search_params = make_search_params()
    page = AsyncMock()
    cards = MagicMock()

    scraper._search_cards = AsyncMock(return_value=cards)

    expected = [
        MagicMock(),
    ]

    scraper._collect_new_items = AsyncMock(
        return_value=expected
    )

    @asynccontextmanager
    async def fake_page_session(url):
        yield page

    scraper.page_session = fake_page_session

    result = await scraper.find_new_items(search_params)

    assert result == expected

    scraper._search_cards.assert_awaited_once_with(
        page,
        search_params,
    )

    scraper._collect_new_items.assert_awaited_once_with(
        cards,
        search_params,
    )


def test_clear_seen_cards__existing_chat__removes_seen_cards(scraper):
    scraper.seen_card_ids = {
        123: {"1", "2"},
        456: {"3"},
    }

    scraper.clear_seen_cards(123)

    assert scraper.seen_card_ids == {
        456: {"3"},
    }


def test_clear_seen_cards__unknown_chat__does_nothing(scraper):
    scraper.seen_card_ids = {
        123: {"1", "2"},
    }

    scraper.clear_seen_cards(999)

    assert scraper.seen_card_ids == {
        123: {"1", "2"},
    }
