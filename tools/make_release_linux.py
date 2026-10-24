"""Builds the Linux player download.  Runs on Linux, in CI (publish/.github/workflows/linux-release.yml).

Like make_release.py for Windows, it starts from the untouched official 0.I download (Linux, with graphics and sounds) and:
- swaps in the People First engine build of cataclysm-tiles (the executable bit is kept: a tarball made on Linux);
- installs the People key and the campfire title (engine/install_data.py);
- ships both mods in data/mods/ and lists them in data/mods/default.json, so every new world has them;
- leaves out data/cache (keyed by each file's exact mtime: a "Stale game data" popup otherwise, see make_release.py)
  and any save, config or cache;
- adds PEOPLE_FIRST.txt.

Usage (from the repository root):
  python3 tools/make_release_linux.py stage <official.tar.gz> <built cataclysm-tiles> <version> <out dir>
  python3 tools/make_release_linux.py pack <version> <out dir>
"""
import json, os, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
USER_DIRS = ("save", "config", "cache", "memorial", "graveyard", "achievements", "templates")


def name(version):
    return f"cdda-0.I-people-first-{version}-linux-x64"


README = """People First {v} for Cataclysm: Dark Days Ahead 0.I "Ito" (Linux x64)
==================================================================

Run ./cataclysm-launcher in this folder.  This is the 0.I stable game with People First built in: survivors who
remember, fall in love, raise families, keep watch, build a town, make homes of their own, and go on living when
you're not looking.

New game:
  1. New Game, then Create World.  People First and People First: Engine are already in the mod list.
  2. The Evacuee scenario is the one the mod was tested with.
  3. Press , (comma) in game to open the People menu.

If it doesn't start, your system needs the SDL2 libraries:
  Debian, Ubuntu, Mint:  sudo apt install libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0 libsdl2-ttf-2.0-0
  Fedora:                sudo dnf install SDL2 SDL2_image SDL2_mixer SDL2_ttf
  Arch:                  sudo pacman -S sdl2 sdl2_image sdl2_mixer sdl2_ttf
Saves live in this folder (save/).  Coming from an older version: copy your save folder into the new one.

The full guide: https://zexonis.github.io/CddaPeopleFirst/

Bugs and feedback (you need a free GitHub account):
  Report a bug:       https://github.com/Zexonis/CddaPeopleFirst/issues/new?template=bug_report.yml
  Feedback or ideas:  https://github.com/Zexonis/CddaPeopleFirst/issues/new?template=feedback.yml
For a bug, include the end of config/debug.log from this folder and a screenshot of any error.

What's different from the official 0.I download
  - cataclysm-tiles is built from the 0.I source (commit 27939e2) with the People First engine patches.  It plays
    every other mod and old 0.I save like the official build.
  - data/mods/PeopleFirst and data/mods/PeopleFirstEngine: the two mods.
  - data/mods/default.json: new worlds get both mods by default.
  - data/raw/keybindings.json: the People key (,).  data/title/people_first.title: the title screen.

Cataclysm: Dark Days Ahead is by CleverRaven and contributors, under CC BY-SA 3.0 (see LICENSE.txt).  People First (the
mods and the engine patches) is by u/LexEntityOfExistence, shared under the same license.  Source and engine patches:
https://github.com/Zexonis/CddaPeopleFirst
"""


def stage(official, binary, version, out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    work = out / "unpack"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    subprocess.run(["tar", "-xzf", official, "-C", str(work)], check=True)   # tar keeps permissions and links
    tops = [p for p in work.iterdir() if p.is_dir()]
    if len(tops) != 1:
        raise SystemExit(f"expected one top folder in the official tarball, found {[p.name for p in tops]}")
    st = out / name(version)
    if st.exists():
        shutil.rmtree(st)
    tops[0].rename(st)
    shutil.rmtree(work)
    print(f"  official 0.I unpacked: {sorted(p.name for p in st.iterdir())}")

    for d in USER_DIRS:
        if (st / d).exists():
            shutil.rmtree(st / d)
    exe = st / "cataclysm-tiles"
    if not exe.exists():
        raise SystemExit("no cataclysm-tiles in the official tarball")
    shutil.copyfile(binary, exe)
    os.chmod(exe, 0o755)
    print("  cataclysm-tiles: the People First engine build")

    subprocess.run([sys.executable, "-I", str(ROOT / "engine" / "install_data.py"), str(st)], check=True)
    orig = st / "data" / "raw" / "keybindings.json.pf-orig"
    if orig.exists():
        orig.unlink()

    for folder in ("PeopleFirst", "PeopleFirstEngine"):
        dst = st / "data" / "mods" / folder
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(ROOT / "mods" / folder, dst)
    print("  mods: data/mods/PeopleFirst, data/mods/PeopleFirstEngine")

    path = st / "data" / "mods" / "default.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    deps = data[0]["dependencies"]
    for mod in ("people_first", "people_first_engine"):
        if mod not in deps:
            deps.append(mod)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"  default mods: {', '.join(deps)}")

    if (st / "data" / "cache").exists():
        shutil.rmtree(st / "data" / "cache")
        print("  data/cache: left out (built on first start)")
    (st / "PEOPLE_FIRST.txt").write_text(README.format(v=version), encoding="utf-8")
    print(f"  staged {st}")


def pack(version, out):
    out = pathlib.Path(out)
    st = out / name(version)
    for d in ("config", "cache", "save", "data/cache"):   # what a check run leaves behind
        if (st / d).exists():
            shutil.rmtree(st / d)
    tgz = out / f"{name(version)}.tar.gz"
    if tgz.exists():
        tgz.unlink()
    subprocess.run(["tar", "--owner=0", "--group=0", "-czf", str(tgz), "-C", str(out), name(version)], check=True)
    print(f"  wrote {tgz} ({tgz.stat().st_size / 2**20:.0f} MB)")


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "stage":
        stage(*sys.argv[2:])
    elif len(sys.argv) == 4 and sys.argv[1] == "pack":
        pack(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
