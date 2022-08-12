from asyncio import Queue, ensure_future, run, sleep

from aioutilities.pool import aioutilities


async def example_coro(initial_number: int, result_queue: Queue[int]) -> None:
    result = initial_number * 2
    print(f"Processing Value! -> {initial_number} * 2 = {result}")
    await sleep(1)
    await result_queue.put(initial_number * 2)


async def result_reader(queue: Queue[int | None]) -> None:
    while True:
        value = await queue.get()
        if value is None:
            break
        print(f"Got value! -> {value}")


async def example() -> None:
    result_queue = Queue[int | None]()
    reader_future = ensure_future(result_reader(result_queue))

    # Start a worker pool with 10 coroutines, invokes `example_coro` and waits for
    # it to complete or 5 minutes to pass.
    pool = aioutilities[int](
        name="ExamplePool",
        task=example_coro,
        worker_qty=10,
        timeout=300,
    )
    async with pool.spawn() as workers:
        for i in range(50):
            await workers.push(i, result_queue)

    await result_queue.put(None)
    await reader_future


def run_example() -> None:
    run(example())
