from importlib.metadata import version
from aioutilities.pool import AioPool, Terminate, Task

__distribution_name__ = "aioutilities"
__version__ = version(distribution_name=__distribution_name__)

# isort: unique-list
__all__ = ["AioPool", "Terminate", "Task"]
