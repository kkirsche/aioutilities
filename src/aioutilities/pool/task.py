from asyncio import Future
from typing import Any, Dict, Generic, Tuple, TypeVar

_T = TypeVar("_T")


class Task(Generic[_T]):
    """An individual task for a worker."""

    future: Future[_T]
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]

    def __init__(
        self,
        future: Future[_T],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> None:
        self.future = future
        self.args = args
        self.kwargs = kwargs
