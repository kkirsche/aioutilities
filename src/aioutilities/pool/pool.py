from asyncio import AbstractEventLoop, Future, Queue
from asyncio import Task as AsyncIOTask
from asyncio import ensure_future, gather, get_running_loop, wait_for
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from logging import Logger, getLogger
from types import TracebackType
from typing import Any, Generic, List, Optional, Type, TypeVar, Union

from aioutilities.pool.task import Task
from aioutilities.pool.terminate import Terminate

_T = TypeVar("_T")


class AioPool(Generic[_T]):
    """The asyncio worker pool implementation."""

    _accept_tasks_for: Optional[timedelta]
    _first_task_received_at: Optional[datetime]
    _joined_at: Optional[datetime]
    _logger: Logger
    _loop: AbstractEventLoop
    _name: str
    _queue: Queue[Union[Task[_T], Terminate]]
    _raise_on_join: bool
    _started_at: Optional[datetime]
    _timeout: Union[float, int]
    _worker_qty: int
    _workers: Optional[List[AsyncIOTask[None]]]
    exceptions: bool
    total_queued: int

    def __init__(
        self,
        name: str,
        task: Callable[..., Any],
        worker_qty: int = 4,
        timeout: Union[float, int] = 300,
        raise_on_join: bool = True,
        accept_tasks_for: Optional[timedelta] = None,
        loop: Optional[AbstractEventLoop] = None,
    ) -> None:
        self._accept_tasks_for = accept_tasks_for
        self._first_task_received_at = None
        self._logger = getLogger(__name__)
        self._loop = loop or get_running_loop()
        self._name = name
        self._queue = Queue(worker_qty)
        self._raise_on_join = raise_on_join
        self._started_at = None
        self._timeout = timeout
        self._worker_coro = task
        self._worker_qty = worker_qty
        self._workers = None
        self.exceptions = False
        self.total_queued = 0

    async def _worker_loop(self) -> None:
        """The loop workers will execute until they are terminated."""
        while True:
            task: Optional[Union[Task[_T], Terminate]] = None
            task_received = False
            try:
                task = await self._queue.get()
                task_received = True
                if isinstance(task, Terminate):
                    break

                task_result = await wait_for(
                    self._worker_coro(*task.args, **task.kwargs), timeout=self._timeout
                )
                task.future.set_result(task_result)
            except (KeyboardInterrupt, MemoryError, SystemExit) as e:
                if isinstance(task, Terminate):
                    break
                if task is None:
                    continue
                task.future.set_exception(e)
                self.exceptions = True
                raise e
            except BaseException as e:
                if isinstance(task, Terminate):
                    break

                self.exceptions = True
                if task:
                    # don't log the failure when the client is receiving the future
                    task.future.set_exception(e)
                else:
                    self._logger.exception("Worker call failed", exc_info=True)
            finally:
                if task_received:
                    self._queue.task_done()

    async def __aenter__(self) -> "AioPool[_T]":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.join()

    async def start(self) -> None:
        if self._workers is not None:
            raise ValueError("Workers already initialized.")
        self._workers = [
            ensure_future(self._worker_loop()) for _ in range(self._worker_qty)
        ]

    async def join(self) -> None:
        # no-op if workers aren't running
        if not self._workers:
            return

        self._joined_at = datetime.now(tz=timezone.utc)
        self._logger.debug("joining %s", self._name)
        # Terminate each worker
        for _ in range(self._worker_qty):
            await self._queue.put(Terminate())

        try:
            await gather(*self._workers)
            self._workers = None
        except Exception as e:
            self._logger.exception("Exception joining %s", self._name, exc_info=True)
            raise e
        finally:
            self._logger.debug("Completed %s", self._name)

        if self.exceptions and self._raise_on_join:
            raise Exception("Exception occurred in pool %s", self._name)

    @asynccontextmanager
    async def spawn(self) -> AsyncGenerator["AioPool[_T]", None]:
        await self.start()
        yield self
        await self.join()

    async def _is_accepting_tasks(self) -> bool:
        if self._accept_tasks_for is None:
            return True

        if self._started_at is None:
            return False

        tasks_accepted_for = datetime.now(tz=timezone.utc) - self._started_at
        return self._accept_tasks_for > tasks_accepted_for

    async def push(self, *args: Any, **kwargs: Any) -> Future[_T]:
        """Method to push work to `worker_co` passed to `__init__`.
        :param args: position arguments to be passed to `worker_co`
        :param kwargs: keyword arguments to be passed to `worker_co`
        :return: future of result"""
        if self._first_task_received_at is None:
            self._first_task_received_at = datetime.now(tz=timezone.utc)

        accepting_tasks = await self._is_accepting_tasks()
        if not accepting_tasks:
            raise TimeoutError(
                f"Maximum lifetime of {self._accept_tasks_for} seconds of "
                + f"AsyncWorkerPool: {self._name} exceeded"
            )

        future = Future[_T]()
        await self._queue.put(Task(future=future, args=args, kwargs=kwargs))
        self.total_queued += 1
        return future
