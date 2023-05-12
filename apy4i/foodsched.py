from datetime import date, timedelta
from random import choice

from quart import Blueprint, request
from .storage import Store
from .auth import simple_token

views = Blueprint("food", __name__)


async def generate_food(dt, part):
    async with Store("foods") as foods:
        return choice(foods[part])


@views.route("/add", methods=["POST"])
@simple_token("VIZ_TOKEN")
async def add_food():
    data = await request.json
    part, food = data["part"], data["food"]
    async with Store("foods") as foods:
        foods.setdefault(part, []).append(food)
    return "Okay"


@views.route("/schedule/<dt>/<part>/reroll", methods=["POST"])
async def reroll(dt, part):
    async with Store("foodsched") as schedule:
        key = f"{dt}-{part}"
        del schedule[key]
    return await food_for(dt, part)


@views.route("/schedule")
async def index():
    parts = [
        """
        <meta charset="utf-8">
        <script
        src="https://unpkg.com/htmx.org@1.9.2"
        integrity="sha384-L6OqL9pRWyyFU3+/bjdSri+iIphTN/bvYyM37tICVyOJkWZLpP2vGn6VUEXgzg6h"
        crossorigin="anonymous"
        ></script>
        <link rel="stylesheet" href="https://cdn.simplecss.org/simple.min.css">
        <style>
            .reload {
                float: right;
                user-select: none;
            }
        </style>
        <h2>Food schedule</h2>
        <table>
        """
    ]
    today = date.today()
    for time_of_day in None, "breakfast", "lunch", "dinner":
        if time_of_day:
            parts.append("<tr>")
            parts.append(f"<td>{time_of_day}</td>")
        else:
            parts.append("<th>")
        for i in range(3):
            dt = today + timedelta(days=i)
            if time_of_day:
                parts.append(await food_for(str(dt), time_of_day))
            else:
                parts.append(f"<td><strong>{dt:%A}</strong></td>")
        if time_of_day:
            parts.append("</tr>")
        else:
            parts.append("</th>")
    parts.append("</table>")
    return "\n".join(parts)


async def food_for(dt, part):
    async with Store("foodsched") as schedule:
        key = f"{dt}-{part}"
        if key not in schedule:
            schedule[key] = await generate_food(dt, part)
        return f"""<td>{schedule[key]}<div
            class="reload"
            hx-post="/food/schedule/{dt}/{part}/reroll"
            hx-trigger="click"
            hx-swap="outerHTML"
            hx-target="closest td"
        >↻</div></td>"""
