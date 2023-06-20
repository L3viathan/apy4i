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

def is_valid(v):
    return datetime.strptime(v["from"], "%Y-%m-%d") <= datetime.now() < datetime.strptime(v["to"], "%Y-%m-%d")


def dt_replace(dt, t):
    return datetime.strptime(f"{dt:%Y-%m-%d}T{t}", "%Y-%m-%dT%H:%M")


def is_open(p):
    now = datetime.now()
    for suffix in ("", "1", "2"):
        key = {
            "Mon": "mo",
            "Tue": "di",
            "Wed": "mi",
            "Thu": "do",
            "Fri": "fr",
            "Sat": "sa",
            "Sun": "so",
        }[f"{now:%a}"] + suffix
        if times := p[key]:
            if dt_replace(now, times["from"]) <= now < dt_replace(now, times["to"]):
                return True
    return False


@cached(max_age=timedelta(hours=2))
def _get_pool_info():
    return requests.get("https://stuttgarterbaeder.de/baeder/jsonData/baeder.json").json()


@views.route("/swimming-pool")
async def get_swimming_pool():
    pool_data = _get_pool_info()
    solebad = next(part for part in pool_data if part["name"] == "SoleBad Cannstatt")
    hours = [h for t in j[0]["businesshours"].values() for h in t if is_valid(h["validity"])]
    parts = []
    for part in hours:
        part_open = is_open(part)
        parts.append(f"<li><span class='open-{part_open and "yes" or "no"}'>·</span> {part_open and "Offen" or "Geschlossen}</li>")
    return f"""<h3>SoleBad</h3>
    <ul>
    {" ".join(parts)}
    </ul>"""


@cached(max_age=timedelta(minutes=2))
def _get_departures():
    departures = []
    for station, walking_minutes in STOPS:
        for departure in vvspy.get_departures(station, limit=5):
            direction = departure.serving_line.direction
            departures.append(
                {
                    "datetime": departure.real_datetime,
                    "direction": direction,
                    "line": departure.serving_line.number,
                    "city-bound": direction in CITY_DIRECTIONS,
                    "stop": departure.stop_name,
                    "walking_minutes": walking_minutes,
                }
            )
    departures.sort(key=lambda d: d["datetime"])
    return departures


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
    now = datetime.now()
    departures = _get_departures()
    result = []
    for departure in departures:
        if len(result) >= 3 and departure["datetime"] > (now + timedelta(minutes=20)):
            continue
        result.append({
            "line": departure["line"],
            "city-bound": departure["city-bound"],
            "direction": departure["direction"],
            "stop": departure["stop"],
            "reachable": now + timedelta(minutes=departure["walking_minutes"]) <= departure["datetime"],
            "countdown": int((departure["datetime"] - now).total_seconds() // 60),
        })
    departures = "\n".join(
        f"""<li>
            <span class='u'>U</span>{d['line'].strip('U')}
            <span class='city-bound-{d['city-bound'] and 'yes' or 'no'}'>{d['direction']}</span>
            (<span class='reachable-{d['reachable'] and 'yes' or 'no'}'>in {d['countdown']}&rsquo;</span>)
            <small>[{d['stop']}]</small>
            </li>"""
        for d in result
        if d["countdown"] >= 0
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
            .open-no {
                color: crimson;
            }
            .open-yes {
                color: forestgreen;
            }
        </style>
    </head>
    <body>
        <div id="cards">
            <div class="card" hx-get="/mls7/departures" hx-trigger="load every 30s">
            </div>
            <div class="card" hx-get="/mls7/biergarten" hx-trigger="load">
            </div>
            <div class="card" hx-get="/mls7/swimming-pool" hx-trigger="load every 900s">
            </div>
        </div>
    </body>
</html>
"""
