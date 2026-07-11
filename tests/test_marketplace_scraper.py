from unittest.mock import AsyncMock, MagicMock, call
from urllib.parse import urljoin

import pytest

from models.item_card import ItemCard
from models.search_params import SearchParams
from scraper.locators import SearchPageLocators
from scraper.marketplace_scraper import MarketplaceScraper


@pytest.fixture
def browser():
    browser = AsyncMock()
    page = AsyncMock()
    browser.new_page.return_value = page
    return browser


@pytest.fixture
def scraper(browser):
    return MarketplaceScraper(browser=browser, redis=None)


@pytest.fixture
def search_params():
    return SearchParams(
        url="https://example.com",
        query="iphone",
        region=None,
        location=None,
        max_price=500,
    )


@pytest.mark.asyncio
async def test_page_session__valid_url__opens_page_and_closes_it(browser, scraper):
    page = browser.new_page.return_value

    async with scraper.page_session("https://example.com") as p:
        assert p is page

    browser.new_page.assert_awaited_once()
    page.goto.assert_awaited_once_with("https://example.com")
    page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_collect_new_items__some_items_are_new__returns_only_new_items_and_updates_seen_ids(
        scraper,
        search_params,
):
    cards = AsyncMock()
    cards.count.return_value = 3
    cards.nth.side_effect = ["c1", "c2", "c3"]

    item1 = ItemCard(
        query="iphone",
        card_id="1",
        description="A",
        image_url="https://example.com/img1.jpg",
        price=100,
        location_and_date="Kyiv",
        item_url="https://example.com/1",
    )

    item2 = ItemCard(
        query="iphone",
        card_id="2",
        description="B",
        image_url="https://example.com/img2.jpg",
        price=200,
        location_and_date="Kyiv",
        item_url="https://example.com/2",
    )

    scraper._extract_item = AsyncMock(
        side_effect=[item1, None, item2]
    )

    items = await scraper._collect_new_items(
        cards,
        1,
        search_params,
    )

    assert items == [item1, item2]
    assert scraper.seen_card_ids[1] == {"1", "2"}


@pytest.mark.asyncio
async def test_find_new_items__search_returns_cards__collects_and_returns_items(scraper, search_params):
    cards = MagicMock()

    scraper._search_cards = AsyncMock(return_value=cards)
    scraper._collect_new_items = AsyncMock(return_value=["item"])

    page = scraper.browser.new_page.return_value

    result = await scraper.find_new_items(
        10,
        search_params,
    )

    assert result == ["item"]

    scraper._search_cards.assert_awaited_once_with(page, search_params)
    scraper._collect_new_items.assert_awaited_once_with(
        cards,
        10,
        search_params,
    )


@pytest.mark.asyncio
async def test_search_cards__without_region__returns_cards(scraper, search_params):
    page = MagicMock()
    page.fill = AsyncMock()

    search_button = MagicMock()
    search_button.click = AsyncMock()

    cards = MagicMock()
    cards.first = MagicMock()
    cards.first.wait_for = AsyncMock(return_value=None)

    page.locator.side_effect = [search_button, cards]

    result = await scraper._search_cards(page, search_params)

    page.fill.assert_awaited_once_with(
        SearchPageLocators.SEARCH_FIELD,
        search_params.query,
    )
    page.locator.assert_has_calls([
        call(SearchPageLocators.SEARCH_BUTTON),
        call(SearchPageLocators.CARD),
    ])
    search_button.click.assert_awaited_once()
    cards.first.wait_for.assert_awaited_once_with(timeout=5000)

    assert result is cards


@pytest.mark.asyncio
async def test_search_cards__with_region__selects_region_and_returns_cards(scraper, search_params):
    search_params.region = "Kyiv"
    search_params.location = "Kyiv city"

    page = MagicMock()
    page.fill = AsyncMock()

    region_input = MagicMock()
    region_input.click = AsyncMock()

    search_button = MagicMock()
    search_button.click = AsyncMock()

    cards = MagicMock()
    cards.first = MagicMock()
    cards.first.wait_for = AsyncMock()

    region_option = MagicMock()
    region_option.click = AsyncMock()

    location_option = MagicMock()
    location_option.click = AsyncMock()

    page.locator.side_effect = [
        region_input,
        search_button,
        cards,
    ]

    page.get_by_text.side_effect = [
        region_option,
        location_option,
    ]

    result = await scraper._search_cards(page, search_params)

    page.fill.assert_awaited_once_with(
        SearchPageLocators.SEARCH_FIELD,
        search_params.query,
    )

    page.locator.assert_has_calls([
        call(SearchPageLocators.REGION_INPUT),
        call(SearchPageLocators.SEARCH_BUTTON),
        call(SearchPageLocators.CARD),
    ])

    page.get_by_text.assert_has_calls([
        call(search_params.region),
        call(search_params.location),
    ])

    region_input.click.assert_awaited_once()
    region_option.click.assert_awaited_once()
    location_option.click.assert_awaited_once()

    search_button.click.assert_awaited_once()
    cards.first.wait_for.assert_awaited_once_with(timeout=5000)

    assert result is cards


@pytest.mark.asyncio
async def test_extract_item__valid_card__returns_item(scraper, search_params):
    card = MagicMock()
    card.get_attribute = AsyncMock(return_value="123")

    price_locator = MagicMock()
    price_locator.text_content = AsyncMock(return_value="499")

    title_locator = MagicMock()
    title_locator.text_content = AsyncMock(return_value="iPhone")

    location_locator = MagicMock()
    location_locator.text_content = AsyncMock(return_value="Kyiv")

    a_locator = MagicMock()
    a_locator.first = MagicMock()
    a_locator.first.get_attribute = AsyncMock(return_value="/item")

    img_locator = MagicMock()
    img_locator.first = MagicMock()
    img_locator.first.get_attribute = AsyncMock(return_value="/img.jpg")

    def locator(selector):
        return {
            SearchPageLocators.PRICE: price_locator,
            SearchPageLocators.TITLE_TAG: title_locator,
            SearchPageLocators.LOCATION_DATE: location_locator,
            "a": a_locator,
            "a img": img_locator,
        }[selector]

    card.locator.side_effect = locator

    item = await scraper._extract_item(card, search_params, set())

    card.get_attribute.assert_awaited_once_with(SearchPageLocators.CARD_ID)
    price_locator.text_content.assert_awaited_once_with(timeout=3000)
    title_locator.text_content.assert_awaited_once_with(timeout=3000)
    location_locator.text_content.assert_awaited_once_with(timeout=3000)
    a_locator.first.get_attribute.assert_awaited_once_with("href")
    img_locator.first.get_attribute.assert_awaited_once_with("src")

    assert isinstance(item, ItemCard)
    assert item.query == search_params.query
    assert item.card_id == "123"
    assert item.description == "iPhone"
    assert item.location_and_date == "Kyiv"
    assert item.price == 499
    assert str(item.item_url) == urljoin(search_params.url, "/item")
    assert str(item.image_url) == urljoin(search_params.url, "/img.jpg")


@pytest.mark.asyncio
async def test_extract_item__duplicate_item__returns_none(scraper, search_params):
    card = MagicMock()
    card.get_attribute = AsyncMock(return_value="123")

    item = await scraper._extract_item(card, search_params, {"123"})

    card.get_attribute.assert_awaited_once_with(SearchPageLocators.CARD_ID)
    card.locator.assert_not_called()
    assert item is None


@pytest.mark.asyncio
async def test_extract_item__price_exceeds_max_price__returns_none(
        scraper, search_params
):
    card = MagicMock()
    card.get_attribute = AsyncMock(return_value="123")

    price_locator = MagicMock()
    price_locator.text_content = AsyncMock(return_value="1000")

    card.locator.return_value = price_locator

    item = await scraper._extract_item(card, search_params, set())

    card.get_attribute.assert_awaited_once_with(
        SearchPageLocators.CARD_ID
    )
    price_locator.text_content.assert_awaited_once_with(timeout=3000)
    assert item is None
