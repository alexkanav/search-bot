import pytest
from unittest.mock import AsyncMock, patch
from bot import main

@pytest.mark.asyncio
async def test_main():
    with patch("bot.Dispatcher") as MockDispatcher, \
         patch("bot.Bot") as MockBot, \
         patch("bot.handlers.router") as mock_router:

        # Setup mocks
        mock_dp_instance = AsyncMock()
        mock_bot_instance = AsyncMock()
        MockDispatcher.return_value = mock_dp_instance
        MockBot.return_value = mock_bot_instance

        # Assign router to mock dispatcher
        mock_dp_instance.include_router.return_value = None
        mock_dp_instance.start_polling = AsyncMock()

        # Run main
        await main()

        # Assertions
        mock_bot_instance.delete_webhook.assert_awaited_once_with(drop_pending_updates=True)
        mock_dp_instance.include_router.assert_called_once_with(mock_router)
        mock_dp_instance.start_polling.assert_awaited_once_with(mock_bot_instance)
