import json
from trio import Semaphore, Path

locks = {"kv": {}, "log": {}}

STORE_PATH = Path("store")
LOGS_PATH = Path("logs")


class Store:
    def __init__(self, key):
        self.key = key
        if key not in locks["kv"]:
            locks["kv"][key] = Semaphore(1)
        self.lock = locks["kv"][key]
        self.path = STORE_PATH / key
        self.data = None

    async def __aenter__(self):
        await self.lock.acquire()
        if await self.path.exists():
            async with await self.path.open() as f:
                self.data = json.loads(await f.read())
        else:
            self.data = {}
        return self.data

    async def __aexit__(self, exc_type, exc, tb):
        if exc is None:
            async with await self.path.open("w") as f:
                await f.write(json.dumps(self.data))
        self.lock.release()


class Log:
    def __init__(self, key):
        self.key = key
        self.path = LOGS_PATH / key
        if key not in locks["log"]:
            locks["log"][key] = Semaphore(1)
        self.lock = locks["log"][key]
        self.has_lock = False

    async def __aenter__(self):
        await self.lock.acquire()
        self.has_lock = True
        return self

    async def log(self, data):
        if not self.has_lock:
            try:
                await self.lock.acquire()
                await self._log(data)
            finally:
                self.lock.release()
        else:
            await self._log(data)

    async def _log(self, data):
        assert self.has_lock
        async with await self.path.open("a") as f:
            await f.write(json.dumps(data))
            await f.write("\n")

    async def __aexit__(self, exc_type, exc, tb):
        self.has_lock = False
        self.lock.release()

    async def __aiter__(self):
        try:
            await self.lock.acquire()
            async with await self.path.open() as f:
                async for line in f:
                    yield json.loads(line)
        finally:
            self.lock.release()
