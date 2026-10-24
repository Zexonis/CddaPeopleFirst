# People First

A mod and a small engine patch set for **Cataclysm: Dark Days Ahead 0.I "Ito"**. The survivors get an inner life: they remember what happened to you and to each other, fall in love and raise families, keep a watch, build a town with its own meetings, laws and walls, and go on living when you aren't looking.

**Full guide:** https://zexonis.github.io/CddaPeopleFirst/

## Download (Windows x64, Linux x64)

Get the zip from the [latest release](https://github.com/Zexonis/CddaPeopleFirst/releases/latest). It's the whole game, ready to play: CDDA 0.I with People First built in.

1. Unzip it anywhere and run `cataclysm-tiles.exe`.
2. New Game, then Create World. People First and People First: Engine are already in the mod list.
3. Press `,` in game for the People menu.

Downloads are built for 64-bit Windows 10 and 11 (`.zip`: run `cataclysm-tiles.exe`) and 64-bit Linux (`.tar.gz`: run `./cataclysm-launcher`; it needs the SDL2 libraries most desktops have). The Linux build comes from `.github/workflows/linux-release.yml`, CleverRaven's own Linux release recipe with our patches applied. On macOS, copy `mods/PeopleFirst` into the official 0.I game's `mods/` folder. It runs without the engine extras (you can't name your children, and people only defend each other up close).

## Bugs and feedback

[Report a bug](https://github.com/Zexonis/CddaPeopleFirst/issues/new?template=bug_report.yml) or [send feedback or an idea](https://github.com/Zexonis/CddaPeopleFirst/issues/new?template=feedback.yml). You need a free GitHub account. The end of `config/debug.log` in the game folder helps with any bug.

## What's here

| Folder | Contents |
|---|---|
| `mods/PeopleFirst` | The mod (`people_first`): JSON and effect-on-condition scripts. Loads on stock 0.I. |
| `mods/PeopleFirstEngine` | The companion mod (`people_first_engine`) for the patched executable. |
| `engine/` | The engine patch set: `apply_patches.py` (25 anchored, idempotent patches on 0.I commit `27939e2`), `people-first.patch` (the full diff), `build.ps1` (Visual Studio + vcpkg build), `install_data.py` (the People key and title screen), `make_title.py` (the title art), and `README.md` (every patch explained). |
| `tools/` | The generators that write most of the mod's JSON (`gen_*.py`), checks (`textcheck.py`, `check.ps1`, `lint.ps1`) and `make_release.py`, which builds the download from the official 0.I zip. The `.ps1` helpers and `make_release.py` contain this project's local paths, so adjust them before use. |
| `index.html` | The guide, served by GitHub Pages. |

## Credits and license

- **Cataclysm: Dark Days Ahead** is made by [CleverRaven and its contributors](https://github.com/CleverRaven/Cataclysm-DDA) under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). The download contains the official 0.I "Ito" release (build 2026-06-06, commit `27939e2`), with its art, sound, fonts and bundled mods, plus the changes listed above. Everything in it that isn't People First is their work.
- **People First** (the mods, the engine patches and the tools) is by u/LexEntityOfExistence, shared under the same license, CC BY-SA 3.0. See `LICENSE.md`.
- The game's fonts keep their own licenses (Terminus: SIL OFL; GNU Unifont: SIL OFL and GPL with the font embedding exception); see `LICENSE.txt` in the download.
