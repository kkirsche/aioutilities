from importlib.metadata import version

from aioutilities.pool import AioPool, Task, Terminate

__distribution_name__ = "aioutilities"
__version__ = version(distribution_name=__distribution_name__)

# isort: unique-list
__all__ = ["AioPool", "Task", "Terminate"]
