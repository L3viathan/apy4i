import logging

from quart_trio import QuartTrio
from quart import request

from textflip import flip
from .slack import slack

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


app.route("/slack", methods=["POST"])(slack)

if __name__ == '__main__':
    app.run()
