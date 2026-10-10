#!/usr/bin/env python3
"""Print one or more KNOWN_ISSUES.md sections by id, without reading the file.

    python -m tools.issue 0z36            # the whole of §0z36
    python -m tools.issue 0j 0z23 0z36    # several, in the order asked
    python -m tools.issue --find wipe     # index rows whose text matches

WHY THIS EXISTS. `KNOWN_ISSUES.md` is the evidence behind every rule in
`CLAUDE.md`, and it is hundreds of kilobytes. `CLAUDE.md` cites a `§` for each
rule instead of carrying the evidence, which only saves anything if following
the citation costs one section rather than the file. A session that opens the
whole file to read §0z36 has paid for every other section to read one.

A section runs from its `## <id>.` heading to the next `## ` heading -- the
same heading shape `check_docs` resolves citations against, so an id this
prints is an id that check accepts, and the reverse.
"""

from __future__ import annotations

import re
import sys

KNOWN_ISSUES = "KNOWN_ISSUES.md"
HEADING = re.compile(r"^## ([0-9][0-9a-z]*)\.", re.M)
INDEX_ROW = re.compile(r"^\|\s*\[([0-9a-z]+)\]\(#[0-9a-z]+\)\s*\|(.*)$", re.M)


def sections(text: str) -> dict[str, str]:
    """{id: the section's text, heading included}."""
    out = {}
    for m in HEADING.finditer(text):
        pos, sid = m.start(), m.group(1)
        nxt = text.find("\n## ", pos + 1)
        out[sid] = text[pos: nxt if nxt != -1 else len(text)].rstrip() + "\n"
    return out


def find(text: str, pattern: str) -> list[str]:
    """Index rows (`| [id](#id) | status | finding |`) matching a regex."""
    rx = re.compile(pattern, re.I)
    return [m.group(0) for m in INDEX_ROW.finditer(text) if rx.search(m.group(2))]


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().split("\n\n")[1])
        return 2
    with open(KNOWN_ISSUES, encoding="utf-8") as fh:
        text = fh.read()
    if argv[0] == "--find":
        rows = find(text, " ".join(argv[1:]))
        print("\n".join(rows) if rows else "no index row matches")
        return 0 if rows else 1
    secs = sections(text)
    missing = []
    for raw in argv:
        sid = raw.lstrip("§").rstrip(".")
        if sid in secs:
            sys.stdout.write(secs[sid] + "\n")
        else:
            missing.append(raw)
    if missing:
        print("no such section: " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
