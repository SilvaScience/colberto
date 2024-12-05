import asyncio
import time
from dumSpec import dumSpec1000

async def say_after(delay, what):
    await asyncio.sleep(delay)
    print(what)

#async def say_after(delay, what):
#    await asyncio.sleep(delay)
#    print(what)

async def main():
    spec=dumSpec1000(integration_time=2)
    loop = asyncio.get_running_loop()
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(
            say_after(1, 'hello'))

        task2 = tg.create_task(
            say_after(2, 'world'))

        print(f"started at {time.strftime('%X')}")

    # The await is implicit when the context manager exits.

    print(f"finished at {time.strftime('%X')}")#
if __name__=='__main__':
    asyncio.run(main())

