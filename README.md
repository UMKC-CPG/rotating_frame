# Rotating Frame

An interactive teaching tool for
**pseudo-forces in a rotating frame**,
built for a graduate physics course and generated from the
[`physdemo`](https://github.com/UMKC-CPG/physdemo) suite's member-tool
skeleton.

## Status

**Generated from the skeleton; the tool's own chain is not yet
written.** `rfsim circle` runs the placeholder (a point on a circle)
so that every route, the self-check, and the tests work from the
first commit. `dev/VISION.md` is the first thing to write; see
`dev/TODO.md`.

## What It Will Do

- (Write the goals here once `dev/VISION.md` is ratified.)

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
rfsim circle             # run a packaged example by name
rfsim --examples         # copy the example run files here, to edit
rfsim circle.toml        # run your edited copy
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
