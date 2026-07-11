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

    assert manager.get(1) is task
    assert isinstance(task, asyncio.Task)

    await task


@pytest.mark.asyncio
async def test_start__existing_task__cancels_previous_task(manager):
    async def never_finishes():
        await asyncio.Event().wait()

    first = manager.start(1, never_finishes())

    second = manager.start(1, dummy())

    assert not first.cancelled()

    await asyncio.sleep(0)

    assert first.cancelled()
    assert manager.get(1) is second

    await second


@pytest.mark.asyncio
async def test_start__task_completes__removes_task_from_storage(manager):
    task = manager.start(1, dummy())

    await task

    await asyncio.sleep(0)

    assert manager.get(1) is None


@pytest.mark.asyncio
async def test_cancel__existing_task__cancels_and_removes_task(manager):
    async def never_finishes():
        await asyncio.Event().wait()

    task = manager.start(1, never_finishes())

    manager.cancel(1)

    await asyncio.sleep(0)

    assert task.cancelled()
    assert manager.get(1) is None


def test_cancel__missing_task__does_nothing(manager):
    manager.cancel(999)

    assert manager.get(999) is None


@pytest.mark.asyncio
async def test_get__existing_task__returns_task(manager):
    task = manager.start(123, dummy())

    assert manager.get(123) is task

    await task


def test_get__missing_task__returns_none(manager):
    assert manager.get(123) is None
