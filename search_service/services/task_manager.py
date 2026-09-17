import asyncio
from collections.abc import Coroutine
from typing import Any


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task[Any]] = {}

    def start(self, chat_id: int, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        self.cancel(chat_id)

        task = asyncio.create_task(coro)
        self._tasks[chat_id] = task

        def remove_task(done_task: asyncio.Task) -> None:
            if self._tasks.get(chat_id) is done_task:
                self._tasks.pop(chat_id, None)

        task.add_done_callback(remove_task)
        return task

    def cancel(self, chat_id: int) -> None:
        task = self._tasks.pop(chat_id, None)
        if task:
            task.cancel()

    def get(self, chat_id: int) -> asyncio.Task | None:
        return self._tasks.get(chat_id)
