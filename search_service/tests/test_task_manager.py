import asyncio

import pytest

from services.task_manager import TaskManager


async def dummy():
    await asyncio.sleep(0)


@pytest.fixture
def manager():
    return TaskManager()


@pytest.mark.asyncio
async def test_start__new_task__creates_and_stores_task(manager):
    task = manager.start(1, dummy())

    assert isinstance(task, asyncio.Task)
    assert manager.get(1) is task

    await task


@pytest.mark.asyncio
async def test_start__existing_task__cancels_previous_task(manager):
    first_task = manager.start(1, asyncio.sleep(10))

    second_task = manager.start(1, asyncio.sleep(0))

    assert first_task.cancelled() or first_task.cancelling()
    assert manager.get(1) is second_task

    with pytest.raises(asyncio.CancelledError):
        await first_task

    await second_task


def test_get__unknown_chat_id__returns_none(manager):
    assert manager.get(999) is None


@pytest.mark.asyncio
async def test_done_callback__task_finishes__removes_task(manager):
    async def work():
        return 42

    task = manager.start(123, work())

    await task

    assert manager.get(123) is None


@pytest.mark.asyncio
async def test_cancel__existing_task__cancels_and_removes_task(manager):
    task = manager.start(1, asyncio.sleep(10))

    manager.cancel(1)

    assert manager.get(1) is None
    assert task.cancelling() == 1

    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()


@pytest.mark.asyncio
async def test_done_callback__task_raises__removes_task(manager):
    async def work():
        raise ValueError("boom")

    task = manager.start(1, work())

    with pytest.raises(ValueError, match="boom"):
        await task

    assert manager.get(1) is None


@pytest.mark.asyncio
async def test_cancel__completed_task__does_nothing(manager):
    task = manager.start(1, dummy())

    await task

    manager.cancel(1)

    assert manager.get(1) is None


def test_cancel__unknown_chat_id__does_nothing(manager):
    manager.cancel(999)

    assert manager.get(999) is None


@pytest.mark.asyncio
async def test_start__replaces_existing_task__old_callback_does_not_remove_new_task(
        manager,
):
    first_task = manager.start(1, asyncio.sleep(10))
    second_task = manager.start(1, asyncio.sleep(0))

    await asyncio.sleep(0)

    assert manager.get(1) is second_task

    await second_task
