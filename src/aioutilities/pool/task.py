from asyncio import Future
from typing import Any, Generic, TypeVar

_T = TypeVar("_T")


class Task(Generic[_T]):
    """An individual task for a worker."""

    future: Future[_T]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    def __init__(
        self,
        future: Future[_T],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        self.future = future
        self.args = args
        self.kwargs = kwargs
