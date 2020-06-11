import logging
from quart_trio import QuartTrio
from quart import request
from trio import sleep

from textflip import flip
from .slack import slack
from .storage import Store

logging.basicConfig(
    filename="api.log", level=logging.INFO, format="%(asctime)s\t%(message)s"
)

app = QuartTrio(__name__)


@app.route("/")
async def hello():
    return "Hello"


@app.route("/flip/<path:text>")
async def flip_text(text):
    return flip(text)


@app.route("/put/<path:key>/<path:val>")
async def put(key, val):
    async with Store("what") as s:
        s[key] = val
        return "stored"


@app.route("/get/<path:key>")
async def get(key):
    async with Store("what") as s:
        return s.get(key, "not found")


@app.route("/stall/<path:key>")
async def stall(key):
    async with Store("what"):
        await sleep(5)
        return "stalled"


app.route("/slack", methods=["POST"])(slack)

if __name__ == "__main__":
    app.run()
