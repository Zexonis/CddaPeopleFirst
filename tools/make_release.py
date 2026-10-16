"""Builds the player download: one zip that is CDDA 0.I "Ito" with People First already in it.

Unzip and run cataclysm-tiles.exe, like the official zip.  Starts from the untouched official 0.I download and:
- replaces cataclysm-tiles.exe with the People First engine build (both are static, no DLLs); drops the vanilla .pdb;
- installs the People key and the campfire title (engine/install_data.py);
- ships both mods in data/mods/ (the player's mods/ folder stays empty for their own);
- adds people_first and people_first_engine to the developers' default mod list (data/mods/default.json), so every
  new world has them already ticked;
- leaves out every save, config, cache, memorial and crash dump: a clean install with no world yet;
- adds PEOPLE_FIRST.txt (how to play) next to the vanilla README.

Usage:  python -I tools/make_release.py [version]      (default version 0.8; writes release/<name>.zip)
Deploy both mods first (tools/check.ps1), since the mods are copied from the game folder's linted mods/.
"""
import json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OFFICIAL = pathlib.Path(r"C:\Users\jmlbl\Downloads\cdda-windows-with-graphics-and-sounds-x64-2026-06-06-1535")
GAME = ROOT / "game" / "cdda-0.I-2026-06-06"
VERSION = sys.argv[1] if len(sys.argv) > 1 else "0.8"
NAME = f"cdda-0.I-people-first-{VERSION}-windows-x64"
OUT = ROOT / "release"
STAGE = OUT / NAME

# user state: kept as empty folders, never copied
EMPTY_DIRS = {"save", "config", "cache", "memorial", "graveyard", "achievements", "mods", "templates"}
SKIP_FILES = {"cataclysm-tiles.pdb", ".core"}

README = f"""People First {VERSION} for Cataclysm: Dark Days Ahead 0.I "Ito"
========================================================

Run cataclysm-tiles.exe.  This is the 0.I stable game with People First built in: survivors who remember, fall in
love, raise families, keep watch, build a town and go on living when you're not looking.

New game:
  1. New Game, then Create World.  People First and People First: Engine are already in the mod list.
  2. The Evacuee scenario is the one the mod was tested with.
  3. Press , (comma) in game to open the People menu.

The full guide: https://zexonis.github.io/CddaPeopleFirst/

Bugs and feedback (you need a free GitHub account):
  Report a bug:       https://github.com/Zexonis/CddaPeopleFirst/issues/new?template=bug_report.yml
  Feedback or ideas:  https://github.com/Zexonis/CddaPeopleFirst/issues/new?template=feedback.yml
  Existing reports:   https://github.com/Zexonis/CddaPeopleFirst/issues
For a bug, include the end of config/debug.log from this folder and a screenshot of any error.  The log may show your
Windows user name in file paths; blank it out before posting.

What's different from the official 0.I zip
  - cataclysm-tiles.exe is built from the 0.I source (commit 27939e2) with the People First engine patches.  It plays
    every other mod and old 0.I save like the official build.
  - data/mods/PeopleFirst and data/mods/PeopleFirstEngine: the two mods.
  - data/mods/default.json: new worlds get both mods by default.
  - data/raw/keybindings.json: the People key (,).  data/title/people_first.title: the title screen.

Cataclysm: Dark Days Ahead is by CleverRaven and contributors, under CC BY-SA 3.0 (see LICENSE.txt).  People First (the
mods and the engine patches) is by r/LexEntityOfExistence, shared under the same license.  Source and engine patches:
https://github.com/Zexonis/CddaPeopleFirst
"""


def main():
    if not OFFICIAL.is_dir():
        raise SystemExit(f"official 0.I download not found: {OFFICIAL}")
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    for item in OFFICIAL.iterdir():
        dst = STAGE / item.name
        if item.is_dir():
            if item.name in EMPTY_DIRS:
                dst.mkdir()
            else:
                shutil.copytree(item, dst)
        elif item.name not in SKIP_FILES:
            shutil.copy2(item, dst)
    print("  copied the official 0.I build")

    shutil.copy2(GAME / "cataclysm-tiles-pf.exe", STAGE / "cataclysm-tiles.exe")
    print("  cataclysm-tiles.exe: the People First engine build")

    subprocess.run([sys.executable, "-I", str(ROOT / "engine" / "install_data.py"), str(STAGE)], check=True)
    orig = STAGE / "data" / "raw" / "keybindings.json.pf-orig"
    if orig.exists():
        orig.unlink()

    for folder in ("PeopleFirst", "PeopleFirstEngine"):
        shutil.copytree(GAME / "mods" / folder, STAGE / "data" / "mods" / folder)
    print("  mods: data/mods/PeopleFirst, data/mods/PeopleFirstEngine")

    path = STAGE / "data" / "mods" / "default.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    deps = data[0]["dependencies"]
    for mod in ("people_first", "people_first_engine"):
        if mod not in deps:
            deps.append(mod)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  default mods: {', '.join(deps)}")

    (STAGE / "PEOPLE_FIRST.txt").write_text(README, encoding="utf-8", newline="\r\n")
    print("  PEOPLE_FIRST.txt")

    # The official zip ships a JSON cache (data/cache/<path>.<mtime>.fb, flexbuffer_cache.cpp) keyed by each file's
    # exact mtime, and any mismatch is a "Stale game data" error popup.  Our changed files mismatch, and unzip tools
    # differ in timestamp precision, so ship no cache: the game builds its own on the first start.
    shutil.rmtree(STAGE / "data" / "cache")
    print("  data/cache: left out (built on first start)")


def pack():
    """Zip the stage (after any checks have run and been cleaned up)."""
    # what a test run leaves behind: options, logs, caches
    for d in ("config", "cache", "data/cache"):
        p = STAGE / d
        if p.exists():
            shutil.rmtree(p)
        if d != "data/cache":
            p.mkdir()
    zip_path = OUT / f"{NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()
    subprocess.run(["tar", "-a", "-c", "-f", str(zip_path), "-C", str(OUT), NAME], check=True)
    print(f"  wrote {zip_path} ({zip_path.stat().st_size / 2**20:.0f} MB)")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "--pack":
        pack()
    else:
        main()
