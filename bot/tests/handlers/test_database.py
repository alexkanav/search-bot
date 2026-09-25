import pytest

from handlers.database import process_db_query


@pytest.mark.asyncio
async def test_process_db_query__invalid_card_id__returns_error(mocker):
    mock_is_valid_card_id = mocker.patch(
        "handlers.database.is_valid_card_id",
        return_value=False,
    )
    message = mocker.MagicMock()
    message.text = "invalid-id"
    message.answer = mocker.AsyncMock()

    state = mocker.AsyncMock()
    rabbitmq = mocker.AsyncMock()

    await process_db_query(message, state, rabbitmq)

    mock_is_valid_card_id.assert_called_once_with("invalid-id")
    message.answer.assert_awaited_once_with("Помилка. Ви ввели некоректний ID картки.")

    state.get_data.assert_not_awaited()
    rabbitmq.publish.assert_not_awaited()
    state.clear.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_db_query__valid_card_id__publishes_db_request(mocker):
    mock_is_valid_card_id = mocker.patch(
        "handlers.database.is_valid_card_id",
        return_value=True,
    )

    message = mocker.MagicMock()
    message.text = " 123456 "
    message.chat.id = 987
    message.answer = mocker.AsyncMock()

    state = mocker.AsyncMock()
    state.get_data.return_value = {"query": "iPhone 15"}

    rabbitmq = mocker.AsyncMock()

    await process_db_query(message, state, rabbitmq)

    mock_is_valid_card_id.assert_called_once_with("123456")

    state.get_data.assert_awaited_once()

    rabbitmq.publish.assert_awaited_once_with(
        queue="db_request",
        body={
            "card_id": "123456",
            "chat_id": 987,
            "query": "iPhone 15",
        },
    )
    message.answer.assert_awaited_once_with(text="Почекайте, завантажую...")

    state.clear.assert_awaited_once()
