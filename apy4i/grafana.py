import os
import json
from datetime import datetime, timezone, timedelta

import asks
from quart import request, jsonify, Blueprint, abort
from .auth import simple_token
from .storage import Store

views = Blueprint("grafana", __name__)


def get_time_range(the_range):
    if not the_range:
        return None, None

    def parse_time(string):
        return datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.%fZ").astimezone(
            timezone.utc
        )

    return parse_time(the_range["from"]), parse_time(the_range["to"])


def to_grafana_type(some_type):
    if isinstance(some_type, list):
        some_type = type(some_type[0])
    return {
        int: "number",
        float: "number",
        bool: "number",
        str: "string",
        datetime: "time",
    }[some_type]


def to_grafana_value(some_value):
    if isinstance(some_value, (int, float, bool, str)):
        return some_value
    if isinstance(some_value, datetime):
        return int(some_value.timestamp() * 1000)
    raise RuntimeError(f"Unknown value type {type(some_value)}: {some_value}")
    abort(500)


async def get_table(target):
    if target == "schika":
        async with Store("schika_ranks") as ranks:
            players = sorted(
                ranks, key=lambda player: ranks[player]["score"], reverse=True
            )
            players = [player for player in players if ranks[player]["active"]]
            scores = [ranks[player]["score"] for player in players]
            return {"player": players, "score": scores}
    else:
        raise RuntimeError(f"Unknown target {target}")
        abort(400)


async def get_timeseries(target):
    # tuples of value, datetime
    now = datetime.now().astimezone(timezone.utc)
    if target == "languageday":
        yield ["🇩🇪", "🇩🇪", "🇩🇪", "🇷🇴", "🏴‍☠️", "🇩🇪/🇷🇴", "🇩🇪/🇷🇴",][
            now.weekday()
        ], now - timedelta(hours=3)
    elif target == "weather":
        weather_location = os.environ.get("WEATHER_LOCATION", "Stuttgart,BW,DE")
        weather_api_key = os.environ.get("WEATHER_API_KEY")
        r = await asks.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={weather_location}&appid={weather_api_key}&units=metric"
        )
        yield {
            200: "⛈",
            201: "⛈",
            202: "⛈",
            230: "⛈",
            231: "⛈",
            232: "⛈",
            210: "🌩",
            211: "🌩",
            212: "🌩",
            221: "🌩",
            300: "🌧",
            301: "🌧",
            302: "🌧",
            310: "🌧",
            311: "🌧",
            312: "🌧",
            313: "🌧",
            314: "🌧",
            321: "🌧",
            500: "🌧",
            501: "🌧",
            502: "🌧",
            503: "🌧",
            504: "🌧",
            511: "🌧",
            520: "🌧",
            521: "🌧",
            522: "🌧",
            531: "🌧",
            600: "🌨",
            601: "🌨",
            602: "🌨",
            611: "🌨",
            612: "🌨",
            613: "🌨",
            615: "🌨",
            616: "🌨",
            620: "🌨",
            621: "🌨",
            622: "🌨",
            701: "🌫",
            711: "🌫",
            721: "🌫",
            731: "🌫",
            741: "🌫",
            751: "🌫",
            761: "🌫",
            762: "🌋",
            771: "🌬",
            781: "🌪",
            800: "☀",
            801: "⛅",
            802: "⛅",
            803: "☁",
            804: "☁",
        }[r.json()["weather"][0]["id"]], now - timedelta(hours=3)
    else:
        raise RuntimeError(f"Unknown target {target}")
        abort(400)


async def make_target(
    *, target=None, type="timeseries", refId="A", data=None, datasource=None
):
    # return a single JSON object
    if type == "timeseries":
        return {
            "target": target,
            "datapoints": [
                # tuples of data, timestamp in ms
                [to_grafana_value(value) for value in row]
                async for row in get_timeseries(target)
            ],
        }
    elif type == "table":
        data = await get_table(target)
        keys = list(data)
        return {
            "type": "table",
            "columns": [
                # dicts with text and type (e.g. time, string, number)
                {"text": key, "type": to_grafana_type(data[key])}
                for key in keys
            ],
            "rows": [
                [to_grafana_value(element) for element in elements]
                for elements in zip(*(data[key] for key in keys))
            ],
        }
    raise RuntimeError(f"Unknown type {type}")
    abort(400)


@views.route("/")
@simple_token("GRAFANA_TOKEN")
async def grafana_index():
    return "", 200


@views.route("/search", methods=["POST"])
@simple_token("GRAFANA_TOKEN")
async def grafana_search():
    return jsonify(["languageday", "schika", "weather"])


@views.route("/query", methods=["POST"])
@simple_token("GRAFANA_TOKEN")
async def grafana_query():
    data = json.loads((await request.get_data()).decode("utf-8"))
    # ignoring these for now; FIXME
    start, stop = get_time_range(data.get("range"))
    interval = int(data.get("intervalMs", 0)) / 1000
    filters = data.get("adhocFilters", [])

    result = [await make_target(**target) for target in data["targets"]]
    print(result)
    return jsonify(result)


@views.route("/annotations", methods=["POST"])
@simple_token("GRAFANA_TOKEN")
async def grafana_annotations():
    return jsonify([])
