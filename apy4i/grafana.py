from datetime import datetime, timezone
from quart import request, jsonify, Blueprint, abort
from .auth import simple_token

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
    abort(500)


def get_table(target):
    ...


def get_timeseries(target):
    # tuples of value, datetime
    if target == "languageday":
        now = datetime.now().astimezone(timezone.utc)
        yield [
            "german/romanian",
            "german",
            "german",
            "german",
            "romanian",
            "free",
            "german/romanian",
        ], now
    else:
        abort(400)


def make_target(*, target=None, type="timeseries", refId="A", data=None):
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
        data = get_table(target)
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
    abort(400)


@views.route("/")
@simple_token("GRAFANA_TOKEN")
async def grafana_index():
    return "", 200


@views.route("/search", methods=["POST"])
@simple_token("GRAFANA_TOKEN")
async def grafana_search():
    return jsonify([])


@views.route("/query", methods=["POST"])
@simple_token("GRAFANA_TOKEN")
async def grafana_query():
    data = await request.get_data()
    # ignoring these for now; FIXME
    start, stop = get_time_range(data.get("range"))
    interval = data["intervalMs"] / 1000
    filters = data.get("adhocFilters", [])

    return jsonify([make_target(**target) for target in data["targets"]])


@views.route("/annotations", methods=["POST"])
@simple_token("GRAFANA_TOKEN")
async def grafana_annotations():
    return jsonify([])
