"""Data side of the People First engine build.

1. The People key: adds the binding to the game's data/raw/keybindings.json.  A plain text insertion after the
   "mutations" binding (the rest of the vanilla file is untouched; a copy of the original is kept as
   keybindings.json.pf-orig).  The official exe ignores the unknown action id, so the shared data folder stays safe for
   both exes.  The key is ',' (free in the default keymap and in the user's custom one, 2026-10-11); rebind it in game
   like any other action.
2. The title screen: copies engine/people_first.title (built by engine/make_title.py) to data/title/people_first.title.
   Only the patched exe reads that file (patch 11); the official exe keeps the vanilla art.

Usage: python -I engine/install_data.py <game folder>
Idempotent.
"""
import pathlib, shutil, sys

game = pathlib.Path(sys.argv[1])
here = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------- 1. the People key
path = game / "data" / "raw" / "keybindings.json"
s = path.read_text(encoding="utf-8")
if '"id": "people_first"' in s:
    print("  keybindings.json: people_first already bound")
else:
    orig = path.with_name("keybindings.json.pf-orig")
    if not orig.exists():
        shutil.copy2(path, orig)
    anchor = '''    "id": "mutations",
    "bindings": [ { "input_method": "keyboard_any", "key": "[" } ]
  },
'''
    if s.count(anchor) != 1:
        raise SystemExit("keybindings.json: mutations anchor not found once")
    entry = '''  {
    "type": "keybinding",
    "name": "People First menu",
    "category": "DEFAULTMODE",
    "id": "people_first",
    "bindings": [ { "input_method": "keyboard_any", "key": "," } ]
  },
'''
    path.write_text(s.replace(anchor, anchor + entry), encoding="utf-8", newline="\n")
    print("  keybindings.json: added people_first on ','")

# ---------------------------------------------------------------- 2. the title screen
src = here / "people_first.title"
dst = game / "data" / "title" / "people_first.title"
if not src.exists():
    raise SystemExit("engine/people_first.title is missing: run python engine/make_title.py first")
shutil.copy2(src, dst)
print(f"  title: installed {dst.name}")
