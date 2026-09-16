"""Shared helpers for the generated docs -- and the reason `--check` can pass.

TWO THINGS LIVE HERE, BOTH BECAUSE THEY WERE ABOUT TO BE WRITTEN THREE TIMES.

`head()` already existed in three copies, in `knobs.py`, `status.py` and
`cache_manifest.py`. That is the §0u shape -- the same rule implemented twice
is implemented two different ways -- caught before it could drift rather than
after, for once.

`comparable()` is the fix for a bug the checks found in themselves on the first
commit. Each generated doc records the git ref it was derived at, so **writing
the file and then committing it makes the file stale by its own test**: the ref
in the body names the commit BEFORE the one that added the file. `--check`
would then fail forever, on every generated doc, immediately after every
commit -- a check that fires when nothing is wrong, which
`cache_manifest.py` warns about by name and which is how a check becomes
something everybody ignores.

So the provenance line is normalised out of the COMPARISON while staying in the
file. What the check still catches is everything that matters: a knob added, a
table regenerated, a swap staged, a cache deleted. What it deliberately stops
catching is "someone committed".

THE PATTERN IS DELIBERATELY NARROW AND HERE IS WHAT IT WOULD BREAK IF IT WERE
NOT. `docs/STATUS.md` prints 16-character CACHE FINGERPRINTS, which are also
lowercase hex, and those are the whole signal of the staleness check -- a
blanket "normalise anything that looks like a hash" would have silently
stopped comparing them. It therefore anchors on the two prose prefixes that
introduce a git ref and on nothing else.
"""

from __future__ import annotations

import re
import subprocess

# Anchored on the prose that introduces a git ref, NOT on "looks like hex".
# See the docstring: cache fingerprints are hex too, and they must keep being
# compared.
_PROVENANCE = re.compile(
    r"(Derived at|Fingerprints recorded at) `[0-9a-f]{7,40}`")


def head() -> str:
    """Short git ref of HEAD, or 'unknown' outside a repo."""
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def comparable(text: str) -> str:
    """A generated doc with the volatile bits masked, for equality testing.

    Masks the git ref in the provenance line and normalises trailing newlines.
    Everything else -- every row, every number, every name -- still compares.
    """
    return _PROVENANCE.sub(r"\1 `<ref>`", text).rstrip("\n") + "\n"
