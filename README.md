# Rotating Frame

An interactive teaching tool for
**pseudo-forces in a rotating frame**,
built for a graduate physics course and generated from the
[`physdemo`](https://github.com/UMKC-CPG/physdemo) suite's member-tool
skeleton.

## Status

**The chain is ratified through pseudocode and every section is
coded.** `rfsim turntable`, `rfsim merry_go_round`, `rfsim
earth_drop`, `rfsim earth_throw`, and `rfsim earth_vertical` run the
packaged examples; `dev/TODO.md` lists what is still open.

## What It Does

- Shows one motion in two views at once: the inertial frame, where
  the stage turns and the path is what the true force alone makes;
  and the rotating frame, where the stage stands still and the path
  bends under the centrifugal, Coriolis, and Euler terms, each drawn
  as a labeled arrow.
- Three stages: a turntable, a merry-go-round, and the Earth at a
  chosen latitude, with a dropped, thrown, or vertically launched
  projectile, or a ring of them.
- Draws the ghost path, what a person in an inertial frame would
  expect, and the check's path, so that the difference between
  physics and numerics is on screen.
- Reports an error budget in three columns, numerical,
  approximation, and distortion, that are never combined.
- Every key is a Ctrl chord; Ctrl+h shows the legend in the window.

## Documents

Development follows a five-level chain, each level citing the one
above it. All design documents live in `dev/`:

| Document | Question it answers |
| --- | --- |
| `dev/VISION.md` | Why does this project exist? |
| `dev/ARCHITECTURE.md` | How is it organized? |
| `dev/DESIGN.md` | How do the algorithms work? |
| `dev/PSEUDOCODE.md` | What are the steps, precisely? |
| `src/` | The implementation. |

`DESIGN.md` and `PSEUDOCODE.md` are indexes; their sections live in
`dev/design/` and `dev/pseudocode/`. `dev/TODO.md` tracks tasks by
level, and `dev/README.md` explains everything else in `dev/`.

When a change is made at any level, check upward (does this
invalidate a parent claim?) and downward (does this require child
updates?) before committing.

## Layout

```
dev/            Design document chain and development material
runs            Symbolic link to src/rotating_frame/examples/
src/
  rotating_frame/      The importable library, plus:
    cli/        the bodies of the commands, and what they share
    defaults/   the shipped rc file, rfsimrc.py
    examples/   ready-to-run example run files (TOML)
  scripts/      Thin executable fronts for cli/
tests/          Test suite (pytest)
pyproject.toml  Packaging, for `pip install`
```

## Installing

There are two ways, for two situations; they run the same code.

**On your own computer (Windows, macOS, or Linux).** You need Python
3.10 or later. Make an environment, install the tool into it, and
check that the computer can draw:

```bash
python -m venv physdemo
source physdemo/bin/activate        # Windows: physdemo\Scripts\activate
pip install https://github.com/UMKC-CPG/rotating_frame/archive/refs/heads/main.zip
rfsim --check
```

`pip` fetches the numerical and graphics libraries (about 1 GB) and
creates the `rfsim` command. No `git`, compiler, or GPU is needed.
In later sessions only the `activate` line is repeated. To update
later, `pip install --upgrade` with the same URL picks up a new
release; between releases the version number does not change and
`pip` will do nothing, so use
`pip install --force-reinstall --no-deps <the same URL>`.

**On a shared computer (a teaching cluster).** The tool is one member
of the `physdemo` suite, which one person installs for everybody: a
single Python environment and a directory of commands. Nothing is
installed per user. The instructor follows the suite's README; a
student only turns it on:

```bash
source /path/to/the/shared/physdemo/activate.sh
rfsim --check
```

## Running

```bash
rfsim turntable          # run a packaged example by name
rfsim --examples         # copy the example run files here, to edit
rfsim earth_drop.toml    # run your edited copy
rfsim earth_throw --view rotating --set frame.exaggeration=100
rfsim --write-rc         # copy the window/palette defaults here
rfsim --help
```

Run from a directory you can write in: screenshots and the `command`
log go to the working directory. In a directory you cannot write, the
tool still runs and says what it could not save.

Every run appends its invocation to a `command` file in the working
directory, so the exact call that produced a result can be recovered
later.

## Testing

```bash
pytest tests/ -v
```

## License

GPL-3.0-or-later; see `LICENSE`. If you build on this tool, by hand
or with an AI assistant, carry the attribution and the citations in
the design sections forward.

## Citation

Not yet published. Each design section cites its sources.
