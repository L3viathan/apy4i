import json
from datetime import datetime, timezone, timedelta
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


def get_timeseries(target):
    # tuples of value, datetime
    if target == "languageday":
        now = datetime.now().astimezone(timezone.utc)
        yield ["🇩🇪", "🇩🇪", "🇩🇪", "🇷🇴", "🏴‍☠️", "🇩🇪/🇷🇴", "🇩🇪/🇷🇴",][
            now.weekday()
        ], now - timedelta(hours=3)
    else:
        raise RuntimeError(f"Unknown target {target}")
        abort(400)


async def make_target(
    *, target=None, type="timeseries", refId="A", data=None, datasource=None
):
    # return a single JSON object
    if type == "timeseries":
        data = get_timeseries(target)
        return {
            "target": target,
            "datapoints": [
                # tuples of data, timestamp in ms
                [to_grafana_value(value) for value in row]
                for row in data
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
    return jsonify(["languageday", "schika"])


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
