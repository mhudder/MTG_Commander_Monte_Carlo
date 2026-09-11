"""Entry points. Run from the repo root as `python -m tools.<name>`.

The `-m` form is not a style preference. These scripts import `edhmc.*`, and
running `python tools/ablation.py` puts `tools/` on `sys.path` instead of the
repo root, so the import fails. `-m` keeps the root on the path, which also
keeps every relative output path (`results/`, `docs/`, `spreadsheets/`)
resolving against the root rather than against whichever directory a script
happens to live in.
"""
