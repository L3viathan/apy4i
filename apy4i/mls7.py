import re
from datetime import timedelta, datetime

from quart import Blueprint, request
import requests
import vvspy

from .utils import cached


# TODO: https://stuttgarterbaeder.de/baeder/jsonData/baeder.json

views = Blueprint("mls7", __name__)

STOPS = [
    ("de:08111:322", 4),  # Kursaal
    ("de:08111:32", 5),  # Uff-Kirchhof
]

CITY_DIRECTIONS = "Botnang", "Marienplatz", "Vaihingen", "Charlottenplatz", "Vogelsang"


@cached(max_age=timedelta(minutes=2))
def _get_departures(max_distance=timedelta(minutes=20), min_results=5):
    departures = []
    now = datetime.now()
    for station, walking_minutes in STOPS:
        for departure in vvspy.get_departures(station, limit=5):
            direction = departure.serving_line.direction
            departures.append(
                {
                    "datetime": departure.real_datetime,
                    "reachable": now + timedelta(minutes=walking_minutes) <= departure.real_datetime,
                    "direction": direction,
                    "line": departure.serving_line.number,
                    "city-bound": direction in CITY_DIRECTIONS,
                    "stop": departure.stop_name,
                    "countdown": departure.countdown,
                }
            )
    departures.sort(key=lambda d: d["datetime"])
    result = []
    for departure in departures:
        if len(result) >= min_results and departure["datetime"] > (now + max_distance):
            continue
        result.append(departure)
    return result


@cached(max_age=timedelta(hours=2))
def _get_biergarten_event():
    r = requests.get("https://www.augustiner-biergarten-stuttgart.de/home/")
    events = re.findall(r'schema.org/Event.*?itemprop="startDate" content="([^"]+)".*?feed_title" itemprop="name">([^<]+)', r.text)
    today = datetime.today().date()
    for date, title in events:
        start = datetime.strptime(date, '%Y-%m-%dT%H:%M')
        if start.date() == today:
            return title, start


@views.route("/departures")
async def get_departures():
    departures = "\n".join(
        f"""<li>
            <span class='u'>U</span>{d['line'].strip('U')}
            <span class='city-bound-{d['city-bound'] and 'yes' or 'no'}'>{d['direction']}</span>
            (<span class='reachable-{d['reachable'] and 'yes' or 'no'}'>in {d['countdown']}&rsquo;</span>)
            <small>[{d['stop']}]</small>
            </li>"""
        for d in _get_departures(max_distance=timedelta(minutes=20), min_results=3)
    )
    return f"""<h3>Departures</h3>
    <ul>
    {departures}
    </ul>"""


@views.route("/biergarten")
async def get_biergarten_events():
    if event := _get_biergarten_event():
        title, time = event
        message = f"Heute ab {time:%H:%M}: {title}"
    else:
        message = "Heute keine Veranstaltung"
    return f"""<h3>Biergarten</h3>
    {message}
    """


@views.route("/")
async def index():
    return """<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MLS7</title>
        <script src="https://unpkg.com/htmx.org@1.9.2"></script>
        <style>
            #cards {
                max-width: 1080px;
                margin: auto;
                display: flex;
                flex-direction: row;
                align-items: flex-start;
                flex-wrap: wrap;
                font-family: sans-serif;
            }
            .card {
                display: inline-block;
                width: 100vw;
                padding: 1em;
                border-radius: 15px;
                margin: 10px;
                background: #ddd;
                text-align: left;
                font-size: x-large;
            }
            .u {
                color: #0e519d;
            }
            ul {
                list-style: none;
                padding-left: 0
            }
            .city-bound-yes {
                font-weight: bold;
            }
            .reachable-no {
                color: crimson;
            }
        </style>
    </head>
    <body>
        <div id="cards">
            <div class="card" hx-get="/mls7/departures" hx-trigger="load every 30s">
            </div>
            <div class="card" hx-get="/mls7/biergarten" hx-trigger="load">
            </div>
        </div>
    </body>
</html>
"""
