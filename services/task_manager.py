import asyncio
from collections.abc import Coroutine
from typing import Any


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task] = {}

    def start(self, user_id: int, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        self.cancel(user_id)
        task = asyncio.create_task(coro)
        self._tasks[user_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(user_id, None))
        return task

    def cancel(self, user_id: int) -> None:
        task = self._tasks.pop(user_id, None)
        if task:
            task.cancel()

    def get(self, user_id: int) -> asyncio.Task | None:
        return self._tasks.get(user_id)
