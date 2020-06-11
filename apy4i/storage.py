import json
from pathlib import Path
from trio import Semaphore

locks = {}

# TODO: Append-only store ("logs"; for schika)
STORE_PATH = Path("store")


class Store:
    def __init__(self, key):
        self.key = key
        if key not in locks:
            locks[key] = Semaphore(1)
        self.lock = locks[key]
        self.path = STORE_PATH / self.key
        self.data = None

    async def __aenter__(self):
        await self.lock.acquire()
        if self.path.exists():
            with self.path.open() as f:
                self.data = json.load(f)
        else:
            self.data = {}
        return self.data

    async def __aexit__(self, exc_type, exc, tb):
        with self.path.open("w") as f:
            json.dump(self.data, f)
        self.lock.release()
