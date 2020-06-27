import json
import uuid
import pickle
from trio import Semaphore, Path

locks = {"kv": {}, "log": {}}

STORE_PATH = Path("store")
LOGS_PATH = Path("logs")
BLOB_PATH = Path("blobs")


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
        self.in_context = False
        self.buffer = []

    async def __aenter__(self):
        self.in_context = True
        return self

    async def log(self, data):
        if not self.in_context:
            async with self:
                self.log(data)
        else:
            self.buffer.append(data)

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc is None:
                await self.lock.acquire()
                try:
                    async with await self.path.open("a") as f:
                        for row in self.buffer:
                            await f.write(json.dumps(row))
                            await f.write("\n")
                finally:
                    self.lock.release()
        finally:
            self.buffer = []
            self.in_context = False

    async def __aiter__(self):
        async with await self.path.open() as f:
            async for line in f:
                yield json.loads(line)


async def write_blob(data):
    # automatic mode?
    identifier = uuid.uuid4().hex
    if isinstance(data, str):
        fmode, conversion, mode = "w", None, "string"
    elif isinstance(data, bytes):
        fmode, conversion, mode = "wb", None, "bytes"
    else:
        fmode, conversion, mode = "wb", pickle.dumps, "pickle"

    conversion = conversion or (lambda x: x)

    async with await (BLOB_PATH / identifier).open(fmode) as f:
        await f.write(conversion(data))

    async with Store("blobs") as s:
        s[identifier] = mode
    return identifier


async def read_blob(identifier, mode="auto"):
    # raw, string, pickle?
    if mode == "auto":
        async with Store("blobs") as s:
            mode = s[identifier]

    fmode = "r" if mode == "string" else "rb"
    conversion = pickle.loads if mode == "pickle" else (lambda x: x)
    async with await (BLOB_PATH / identifier).open(fmode) as f:
        return conversion(await f.read())
