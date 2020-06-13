import os
import logging
from functools import wraps

from quart_trio import QuartTrio
from quart import request, jsonify
from trio import sleep

from textflip import flip
from .slack import slack
from .storage import Store, Log
from .utils import timestamp, elo as _elo

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
    async with Log("flips") as l:
        await l.log(
            {
                "ts": timestamp(),
                "text": text,
                "ip": request.headers.get("X-Forwarded-For"),
            }
        )
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


@app.route("/elo/<outcome>/<team_a>/<team_b>")
@app.route("/elo/<outcome>/<team_a>/<team_b>/<int:k>")
def elo(outcome, team_a, team_b, k=16):
    outcome = {"win": "a", "loss": "b", "draw": "draw"}[outcome]
    listy = "," in team_a
    team_a = [int(score) for score in team_a.split(",")]
    team_b = [int(score) for score in team_b.split(",")]
    assert len(team_a) == len(team_b), "Teams have to have the same amount of players"
    mod_a, mod_b = _elo(team_a, team_b, outcome, k)
    if listy:
        return jsonify(
            [[round(x + mod_a) for x in team_a], [round(x + mod_b) for x in team_b]]
        )
    return jsonify([round(team_a[0] + mod_a), round(team_b[0] + mod_b)])


app.route("/slack", methods=["POST"])(slack)


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST"
    return response


if __name__ == "__main__":
    app.run()
