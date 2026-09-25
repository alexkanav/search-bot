from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def settings_env(monkeypatch):
    monkeypatch.setenv("RABBITMQ_URL", "amqp://localhost")
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "test")
    monkeypatch.setenv("MONGODB_COLLECTION", "test_collection")
    monkeypatch.setenv("LOG_FILE", "test.log")


@pytest.mark.asyncio
async def test_lifespan__successful_startup__initializes_services(settings_env, mocker):
    from main import lifespan

    app_settings = mocker.patch(
        "main.app_settings",
        new=MagicMock(),
    )

    scraper = AsyncMock()
    mocker.patch(
        "main.MarketplaceScraper.create",
        return_value=scraper,
    )

    repository = MagicMock()
    mongo_client = MagicMock()

    create_repository = mocker.patch(
        "main.create_mongodb_repository",
        return_value=(repository, mongo_client),
    )

    task_manager = mocker.patch(
        "main.TaskManager",
        return_value=MagicMock(),
    )

    rabbit_instance = MagicMock()
    rabbit_instance.connect = AsyncMock()
    rabbit_instance.consume = AsyncMock()
    rabbit_instance.close = AsyncMock()

    rabbit = mocker.patch(
        "main.RabbitMQ",
        return_value=rabbit_instance,
    )

    service_instance = MagicMock()
    service = mocker.patch(
        "main.SearchService",
        return_value=service_instance,
    )

    app = MagicMock()

    async with lifespan(app):
        assert app.state.scraper is scraper

    scraper.close.assert_awaited_once()

    create_repository.assert_awaited_once_with(app_settings)

    task_manager.assert_called_once()

    rabbit.assert_called_once_with(str(app_settings.RABBITMQ_URL))
    rabbit_instance.connect.assert_awaited_once()
    assert rabbit_instance.consume.await_count == 2
    rabbit_instance.consume.assert_any_await(
        "search_request",
        service_instance.search_handle,
    )
    rabbit_instance.consume.assert_any_await(
        "db_request",
        service_instance.repository_handler,
    )
    rabbit_instance.close.assert_awaited_once()

    service.assert_called_once_with(
        repository,
        scraper,
        rabbit_instance,
        task_manager.return_value,
    )

    mongo_client.close.assert_called_once()
