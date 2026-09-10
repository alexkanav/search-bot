from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urljoin

from playwright.async_api import Browser, Page, Locator
from playwright.async_api import BrowserContext, Playwright
from playwright.async_api import TimeoutError
from playwright.async_api import async_playwright
from pydantic import HttpUrl

from config import SEARCH_RESULTS_TIMEOUT_MS, PRICE_TIMEOUT_MS, ITEM_TIMEOUT_MS
from models.items import ItemCard
from models.search import SearchParams
from scraper.locators import SearchPageLocators


class MarketplaceScraper:
    def __init__(self) -> None:
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.playwright: Playwright | None = None
        self.seen_card_ids: dict[int, set[str]] = {}

    @classmethod
    async def create(cls) -> "MarketplaceScraper":
        self = cls()

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self.context = await self.browser.new_context()

        return self

    async def close(self) -> None:
        if self.browser is not None:
            await self.browser.close()

        if self.playwright is not None:
            await self.playwright.stop()

    @asynccontextmanager
    async def page_session(self, url: HttpUrl) -> AsyncIterator[Page]:
        if self.context is None:
            raise RuntimeError("Scraper has not been started.")

        page = await self.context.new_page()
        try:
            await page.goto(str(url))
            yield page
        finally:
            await page.close()

    async def get_regions(self, url: HttpUrl) -> list[str]:
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

    async def get_locations(self, region: str, url: HttpUrl) -> list[str]:
        async with self.page_session(url) as page:
            await page.fill(SearchPageLocators.REGION_INPUT, "")

            region_button = page.locator(SearchPageLocators.REGION_TEXT.format(region))
            await region_button.first.wait_for()
            await region_button.click()

            locations = page.locator(SearchPageLocators.LOCATION_BUTTON)
            await locations.first.wait_for()

            return await locations.all_inner_texts()

    async def _search_cards(self, page: Page, search_params: SearchParams) -> Locator:
        await page.fill(SearchPageLocators.SEARCH_FIELD, search_params.query)

        if search_params.region:
            await page.locator(SearchPageLocators.REGION_INPUT).click()
            await page.get_by_text(search_params.region).click()
            if search_params.location:
                await page.get_by_text(search_params.location).click()

        await page.locator(SearchPageLocators.SEARCH_BUTTON).click()

        cards = page.locator(SearchPageLocators.CARD)
        await cards.first.wait_for(timeout=SEARCH_RESULTS_TIMEOUT_MS)
        return cards

    async def _extract_item(self, card: Locator, search_params: SearchParams, seen_ids: set[str]) -> ItemCard | None:
        card_id = await card.get_attribute(SearchPageLocators.CARD_ID)

        if not card_id or card_id in seen_ids:
            return None

        try:
            price_text = await card.locator(SearchPageLocators.PRICE).text_content(timeout=PRICE_TIMEOUT_MS)
            price_digits = ''.join(filter(str.isdigit, price_text or ""))
            price = int(price_digits) if price_digits else 0

            if price > search_params.max_price:
                return None

        except TimeoutError:
            price = 0

        try:
            description = await card.locator(SearchPageLocators.TITLE_TAG).text_content(timeout=ITEM_TIMEOUT_MS)
            location_and_date = await card.locator(SearchPageLocators.LOCATION_DATE).text_content(
                timeout=ITEM_TIMEOUT_MS)
            href = await card.locator("a").first.get_attribute("href")

            item_url = urljoin(str(search_params.url), href or "")

            src = await card.locator(SearchPageLocators.IMAGE_LINK).first.get_attribute(SearchPageLocators.IMAGE_SOURCE)
            image_url = (
                urljoin(str(search_params.url), src)
                if src
                else None
            )
            return ItemCard(
                chat_id=search_params.chat_id,
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

    async def _collect_new_items(self, cards: Locator, search_params: SearchParams) -> list[ItemCard]:
        seen_ids = self.seen_card_ids.setdefault(search_params.chat_id, set())
        items = []
        card_count = await cards.count()
        for i in range(card_count):
            item = await self._extract_item(cards.nth(i), search_params, seen_ids)

            if not item:
                continue

            seen_ids.add(item.card_id)
            items.append(item)
        return items

    async def find_new_items(self, search_params: SearchParams) -> list[ItemCard]:
        async with self.page_session(search_params.url) as page:
            cards = await self._search_cards(page, search_params)
            return await self._collect_new_items(cards, search_params)

    def clear_seen_cards(self, chat_id: int) -> None:
        self.seen_card_ids.pop(chat_id, None)
