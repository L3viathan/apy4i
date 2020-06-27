from quart import Blueprint, request, abort, jsonify
from chordy.song import Song
from chordy.chord import Chord
from .storage import read_blob, write_blob

views = Blueprint("chords", __name__)


@views.route("/convert", methods=["POST"], defaults={"format_": "html"})
@views.route("/convert/<format_>", methods=["POST"])
async def convert(format_):
    if format_ not in ["html", "txt", "tex"]:
        abort(405)
    data = await request.json
    song = Song.from_file(filter(bool, data["lines"]))
    song.title = data.get("title")
    return getattr(song, f"to_{format_}")(flags=data.get("flags", ""))


@views.route("/save", methods=["POST"])
async def save():
    data = await request.json
    song = Song.from_file(filter(bool, data["lines"]))
    song.title = data.get("title")
    return await write_blob(song)


@views.route("/show/<identifier>", defaults={"format_": "html"})
@views.route("/show/<identifier>/<format>")
async def show(identifier, format_):
    song = await read_blob(identifier)
    if transpose := request.args.get("transpose"):
        song = song.transpose(int(transpose))
    if request.args.get("simplify"):
        song = song.simplify()
    if not (flags := request.args.get("flags")):
        flags = ""
    return getattr(song, f"to_{format_}")(flags=flags)


@views.route("/detect/<path:chord>")
async def detect(chord):
    chord = chord.rstrip("/")
    if not Chord.is_chord(chord):
        return (404, "No such chord found")
    chord = Chord.from_string(chord)
    return jsonify(
        {
            "tone": chord.tone,
            "minor": chord.minor,
            "bass": chord.bass,
            "modifiers": chord.modifiers,
            "optional": chord.optional,
        }
    )
