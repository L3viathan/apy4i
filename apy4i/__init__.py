import os
import logging
from functools import wraps

from quart_trio import QuartTrio
from quart import request, jsonify
from trio import sleep

from textflip import flip
from .slack import slack
from .storage import Store, Log

logging.basicConfig(
    filename="api.log", level=logging.INFO, format="%(asctime)s\t%(message)s"
)

app = QuartTrio(__name__)


def debug_route(*args, **kwargs):
    def decorator(fn):
        if os.environ.get("DEBUG_STUFF") == "yep":
            return app.route(*args, **kwargs)(fn)
    return decorator


@app.route("/")
async def hello():
    return "Hello"


@app.route("/flip/<path:text>")
async def flip_text(text):
    return flip(text)


@debug_route("/put/<path:key>/<path:val>")
async def put(key, val):
    async with Store("what") as s:
        s[key] = val
        return "stored"


@debug_route("/get/<path:key>")
async def get(key):
    async with Store("what") as s:
        return s.get(key, "not found")


@debug_route("/stall/<path:key>")
async def stall(key):
    async with Store("what"):
        await sleep(5)
        return "stalled"


@debug_route("/log/<path:data>")
async def log(data):
    async with Log("who") as l:
        await l.log({"storing": data})
        return "logged"


@debug_route("/logs")
async def logs():
    entries = []
    async for entry in Log("who"):
        entries.append(entry)
    return jsonify(entries)


app.route("/slack", methods=["POST"])(slack)

if __name__ == "__main__":
    app.run()
