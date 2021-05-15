import asyncio


async def io_task():
    await asyncio.sleep(0.01)


async def main():
    t1 = asyncio.create_task(io_task())
    t2 = asyncio.create_task(io_task())
    t3 = asyncio.create_task(io_task())

    await t1
    await t2
    await t3


if __name__ == "__main__":
    asyncio.run(main())
