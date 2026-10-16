"""Catches the game's text-style errors that --check-mods doesn't report (they only show in debug.log on world load):
three dots instead of an ellipsis, and one space after a sentence-ending period in player-facing text.
Also catches duplicate object ids (top-level and inline EOCs) across the mod: the engine reports those as a modal
"Error loading data" popup, which stalls --check-mods and the game.
Usage: python tools/textcheck.py mods/PeopleFirst"""
import json, os, re, sys

KEYS = {"u_message", "description", "dynamic_line", "text", "str", "str_pl", "yes", "no", "name", "title"}
bad = []
ids = {}  # (type-ish, id) -> first file

def note_id(o, f, path):
    t = o.get("type", "effect_on_condition" if ("effect" in o and "id" in o) else None)
    if t and isinstance(o.get("id"), str) and ("effect" in o or path == ""):
        key = (t, o["id"])
        if key in ids and ids[key] != (f, path):
            bad.append((f, path, f"duplicate {t} id (also in {ids[key][0]})", o["id"]))
        else:
            ids[key] = (f, path)

def walk(o, path, f, top=False):
    if isinstance(o, dict):
        if top or "effect" in o:
            note_id(o, f, "" if top else path)
        for k, v in o.items():
            if isinstance(v, str) and k in KEYS:
                check(v, f, path + "." + k)
            walk(v, path + "." + k, f)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, str) and path.endswith(("names", "descriptions")):
                check(v, f, path)
            walk(v, path + f"[{i}]", f, top=(path == ""))

def check(t, f, path):
    t2 = re.sub(r"<[^>]*>", "X", t)  # tags don't count
    if "..." in t2:
        bad.append((f, path, "three dots; use …", t))
    if re.search(r"[a-z][.!?]\"? [A-Z\"]", t2):
        bad.append((f, path, "one space after a sentence end; use two", t))

for root, _, files in os.walk(sys.argv[1]):
    for fn in files:
        if fn.endswith(".json"):
            fp = os.path.join(root, fn)
            walk(json.load(open(fp, encoding="utf-8")), "", fp)
for f, path, why, t in bad:
    print(f"{f} {path}: {why}: {t[:100]}")
print(f"textcheck: {len(bad)} problem(s)")
sys.exit(1 if bad else 0)
