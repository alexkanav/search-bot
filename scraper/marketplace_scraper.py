import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urljoin

from playwright.async_api import Browser, Page, Locator
from playwright.async_api import TimeoutError

from config import DEFAULT_IMAGE
from models.item_card import ItemCard
from models.search_params import SearchParams
from scraper.locators import SearchPageLocators

logger = logging.getLogger(__name__)

from redis.asyncio import Redis

from utils.cache import redis_cache

SECONDS_PER_DAY = 24 * 60 * 60


class MarketplaceScraper:
    def __init__(self, browser: Browser, redis: Redis | None) -> None:
        self.browser = browser
        self.redis = redis
        self.seen_card_ids: dict[int, set[str]] = {}

    @asynccontextmanager
    async def page_session(self, url: str) -> AsyncIterator[Page]:
        page = await self.browser.new_page()

        try:
            await page.goto(url)
            yield page
        finally:
            await page.close()

    @redis_cache(expire=7 * SECONDS_PER_DAY)
    async def get_regions(self, url: str) -> list[str]:
        async with self.page_session(url) as page:
            await page.fill(SearchPageLocators.REGION_INPUT, "")

            buttons = page.locator(SearchPageLocators.REGION_BUTTON)
            await buttons.first.wait_for()

            labels = await buttons.evaluate_all(
                "(els, attr) => els.map(el => el.getAttribute(attr))",
                SearchPageLocators.REGION_BUTTON_ATTR,
            )
            return [
                label.removesuffix(SearchPageLocators.REGION_SUFFIX)
                for label in labels
                if label
            ]

    @redis_cache(expire=2 * SECONDS_PER_DAY)
    async def get_locations(self, region: str, url: str) -> list[str]:
        async with self.page_session(url) as page:
            await page.fill(SearchPageLocators.REGION_INPUT, "")

            region_button = page.locator(f'button:has-text("{region}")')
            await region_button.click()

            locations = page.locator(SearchPageLocators.LOCATION_BUTTON)
            await locations.first.wait_for()

            return await locations.all_inner_texts()

    async def _search_cards(self, page: Page, search_params: SearchParams) -> Locator:
        await page.fill(SearchPageLocators.SEARCH_FIELD, search_params.query)

        if search_params.region:
            await page.locator(SearchPageLocators.REGION_INPUT).click()
            await page.get_by_text(search_params.region).click()
            await page.get_by_text(search_params.location).click()

        await page.locator(SearchPageLocators.SEARCH_BUTTON).click()

        cards = page.locator(SearchPageLocators.CARD)
        await cards.first.wait_for(timeout=5000)
        return cards

    async def _extract_item(self, card: Locator, search_params: SearchParams, seen_ids: set) -> ItemCard | None:
        card_id = await card.get_attribute(SearchPageLocators.CARD_ID)

        if not card_id or card_id in seen_ids:
            return None

        try:
            price_text = await card.locator(SearchPageLocators.PRICE).text_content(timeout=3000)
            price_digits = ''.join(filter(str.isdigit, price_text or ""))
            price = int(price_digits) if price_digits else 0

            if price > search_params.max_price:
                return None

        except TimeoutError:
            price = 0

        try:
            description = await card.locator(SearchPageLocators.TITLE_TAG).text_content(timeout=3000)
            location_and_date = await card.locator(SearchPageLocators.LOCATION_DATE).text_content(timeout=3000)
            href = await card.locator("a").first.get_attribute("href")

            item_url = urljoin(search_params.url, href or "")

            src = await card.locator("a img").first.get_attribute("src")
            image_url = (
                urljoin(search_params.url, src)
                if src
                else DEFAULT_IMAGE
            )
            return ItemCard(
                query=search_params.query,
                card_id=card_id,
                description=description,
                image_url=image_url,
                price=price,
                location_and_date=location_and_date,
                item_url=item_url,
            )

        except TimeoutError:
            return None

    async def _collect_new_items(self, cards: Locator, user_id: int, search_params: SearchParams) -> list[ItemCard]:
        seen_ids = self.seen_card_ids.setdefault(user_id, set())
        items = []
        card_count = await cards.count()
        for i in range(card_count):
            item = await self._extract_item(cards.nth(i), search_params, seen_ids)

            if not item:
                continue

            seen_ids.add(item.card_id)
            items.append(item)
        return items

    async def find_new_items(self, user_id: int, search_params: SearchParams) -> list[ItemCard]:
        async with self.page_session(search_params.url) as page:
            cards = await self._search_cards(page, search_params)
            return await self._collect_new_items(cards, user_id, search_params)
