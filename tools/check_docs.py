#!/usr/bin/env python3
"""Fail when the documentation stops describing the repository.

WHY THIS EXISTS. This project's own standing finding, §0q, says a
hand-maintained name set is a claim and claims rot, and that **the fix is not
vigilance, it is derivation** -- with a check that raises when the derived set
drifts. That discipline was applied to card names five times
(`check_scripted_coverage`, `discover_current_decks`,
`check_land_enabler_coverage`, `check_planeswalker_coverage`,
`check_dynamic_cost_coverage`) and never once to the documentation, which is
the largest hand-maintained name set in the repo.

It was rotting exactly as predicted. When this file was written:

  * seven scripts on disk appeared in none of `CLAUDE.md`'s command lists;
  * 36 of 107 engine knobs were named in no `.md` file at all;
  * `docs/ABLATION_CACHES.md` -- a GENERATED file that says "do not edit by
    hand" -- listed fourteen caches of which four existed, because the commit
    that deleted the other ten did not regenerate it;
  * every surviving cache's recorded fingerprint disagreed with its live one,
    so the repo's own "delete a cache whose fingerprint differs" rule pointed
    at all four.

The last two are the instructive ones: **a generated file is only as current as
the last time someone remembered to generate it.** So the checks below verify
that the generators were RUN, not merely that they exist.

    python -m tools.check_docs             # check; exit 1 on any failure
    python -m tools.check_docs --mutate    # prove the checks can fail

THE MUTATION RUN IS NOT OPTIONAL PRACTICE HERE. `CLAUDE.md` requires it -- "a
check that cannot fail reads like assurance and is worse than none" -- and
§0z15 found four checks in this repo that could not fail, one of which had been
silently broken for days. `--mutate` corrupts the repo in memory, once per
check, and asserts an EXACT set of failures, so a check that stops mattering is
as loud as one that breaks. **Write the expectation before you run it.**
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

from tools._generated import comparable

SECTION_CITE = re.compile(r"§([0-9][0-9a-z]*)")
KNOWN_ISSUES = "KNOWN_ISSUES.md"
CODE_DIRS = ("edhmc", "tools", "diagnostics", "tests")


class Result:
    def __init__(self, name: str, ok: bool, detail: str = ""):
        self.name = name
        self.ok = ok
        self.detail = detail


# This file is excluded from its own scan. It necessarily CONTAINS a bogus
# section id and a bogus doc path -- they are the mutation fixtures below --
# and a checker that reads its own test data as evidence reports a failure it
# invented. Found on the first run, when it flagged `§0zz99` as an unresolved
# citation from code.
SELF = os.path.join("tools", "check_docs.py")


def code_files() -> list[str]:
    out = []
    for d in CODE_DIRS:
        if not os.path.isdir(d):
            continue
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in sorted(files):
                if f.endswith((".py", ".sh")):
                    p = os.path.join(root, f)
                    if os.path.normpath(p) != os.path.normpath(SELF):
                        out.append(p)
    return sorted(out)


def read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


# --------------------------------------------------------------------------
# The checks. Each returns a Result and takes its inputs as arguments so the
# mutation run can hand it a corrupted copy.


def check_sections_resolve(code_text: str, issues: str) -> Result:
    """Every §id cited from code resolves to a heading in KNOWN_ISSUES.md.

    The ids are load-bearing precisely because code cites them (the count
    is printed in the result), and nothing had ever checked that they land.
    """
    cited = set(SECTION_CITE.findall(code_text))
    headings = set(re.findall(r"^## ([0-9][0-9a-z]*)\.", issues, re.M))
    missing = sorted(cited - headings)
    return Result(
        f"every §id cited from code resolves ({len(cited)} cited)",
        not missing,
        "unresolved: " + ", ".join("§" + m for m in missing) if missing else "")


def check_index_matches_headings(issues: str) -> Result:
    """The index table and the headings are the same set, both ways.

    The index is how anyone navigates a file thousands of lines long. A heading with no row
    is invisible; a row with no heading is a dead link.
    """
    headings = set(re.findall(r"^## ([0-9][0-9a-z]*)\.", issues, re.M))
    rows = set(re.findall(r"^\|\s*\[([0-9a-z]+)\]\(#[0-9a-z]+\)\s*\|",
                          issues, re.M))
    only_head = sorted(headings - rows)
    only_row = sorted(rows - headings)
    bits = []
    if only_head:
        bits.append("heading with no index row: "
                    + ", ".join("§" + x for x in only_head))
    if only_row:
        bits.append("index row with no heading: "
                    + ", ".join("§" + x for x in only_row))
    return Result(
        f"KNOWN_ISSUES index matches its headings ({len(headings)} sections)",
        not bits, "; ".join(bits))


def check_doc_paths_exist(code_text: str) -> Result:
    """Every `docs/*.md` path named in code exists.

    `edhmc/pending.py` and `edhmc/experiment.py` both cite
    `docs/CANDIDATES_2026-09-04.md`. Moving or archiving a doc that code
    points at breaks a reference nothing would otherwise notice.
    """
    cited = {m for m in re.findall(r"docs/[A-Za-z0-9_\-]+\.md", code_text)}
    missing = sorted(p for p in cited if not os.path.isfile(p))
    return Result(
        f"every docs/ path cited from code exists ({len(cited)} cited)",
        not missing, "missing: " + ", ".join(missing) if missing else "")


# Docs exempt from every check that holds a doc to TODAY'S tree, and WHAT
# THAT MAKES THEM BLIND TO
# -- §0z15's rule, because a checker's exemptions are where its bugs live.
# HISTORY.md is a dated record and legitimately names paths that have since
# moved; holding it to today's tree would flag provenance as breakage. The cost
# is that a genuinely broken link inside HISTORY.md is NOT caught here. Read it
# as a record, and follow its paths with a grep rather than a click.
# ONE list, shared by check_doc_xrefs and check_shell_commands_exist. They had
# separate opinions for about five minutes and immediately disagreed --
# HISTORY.md names the pre-reorganisation `./regen_tables.sh`, which the xref
# check excused and the shell check flagged. That is §0z16 in miniature: the
# same rule, written twice, means two different things. Any future check of
# this shape reads this list.
HISTORICAL = (os.path.join("docs", "HISTORY.md"),)


def _exempt(path: str) -> bool:
    return os.path.normpath(path) in [os.path.normpath(x) for x in HISTORICAL]


def check_doc_xrefs(docs: dict[str, str]) -> Result:
    """Every `docs/...md` path a LIVE doc names actually exists.

    Archiving `docs/DECK_CHANGES.md` broke three references in one move, and
    nothing would have noticed: a wrong path in a doc fails silently, at the
    moment someone is already lost.
    """
    bad = []
    for path, body in docs.items():
        if _exempt(path):
            continue
        for ref in set(re.findall(r"docs/[A-Za-z0-9_\-/]+\.md", body)):
            if not os.path.isfile(ref):
                bad.append(f"{path} -> {ref}")
    return Result("every docs/ path named in a live doc exists",
                  not bad, "; ".join(sorted(set(bad))))


def check_commands_exist(docs: dict[str, str]) -> Result:
    """Every `python -m X.y` in a live doc names a module that exists.

    This is the one that catches the seven scripts `CLAUDE.md` had never heard
    of, from the other direction: a command that cannot run.
    """
    bad = []
    for path, body in docs.items():
        for mod in re.findall(r"python -m ([a-z_]+\.[a-z_0-9]+)", body):
            parts = mod.split(".")
            target = os.path.join(*parts) + ".py"
            pkg = os.path.join(*parts, "__init__.py")
            if not (os.path.isfile(target) or os.path.isfile(pkg)):
                bad.append(f"{path}: python -m {mod}")
    return Result("every `python -m` command in the docs resolves",
                  not bad, "; ".join(sorted(set(bad))))


def check_shell_commands_exist(docs: dict[str, str]) -> Result:
    """Every `./path/script.sh` in a live doc exists AND is executable.

    `check_commands_exist` covers `python -m`, and that exemption hid a real
    defect for the life of the repo: `tools/regen_tables.sh` was committed
    mode 100644, so the `./tools/regen_tables.sh` that CLAUDE.md and HANDOFF.md
    both document as THE way to rebuild the tables died with "Permission
    denied" in any fresh clone. It was found by running it, not by reading it.

    An unexecutable script is worse than a missing one: the path resolves, the
    file is right there, and the failure looks like an environment problem
    rather than a repository one. §0z15 -- a check that skips a category is
    blind exactly where the bug is, and "commands" meant "python commands"
    until now.
    """
    bad = []
    for path, body in docs.items():
        if _exempt(path):
            continue
        for cmd in set(re.findall(r"(?<![\w/])\./([A-Za-z0-9_\-./]+\.sh)", body)):
            if not os.path.isfile(cmd):
                bad.append(f"{path}: ./{cmd} does not exist")
            elif not os.access(cmd, os.X_OK):
                bad.append(f"{path}: ./{cmd} is not executable")
    return Result("every `./...sh` command in the docs exists and is executable",
                  not bad, "; ".join(sorted(set(bad))))


ARCHITECTURE = os.path.join("docs", "ARCHITECTURE.md")


DURABLE = ("CLAUDE.md", "HANDOFF.md")
# The phrasings that HAD rotted when this check was written (2026-09-17): a
# §-id range, "all N knobs", a cite count, a line count. It is blind to any
# other way of quoting the same figure (§0z15: an exemption is a blind spot,
# written down) -- the durable rule is "carry no number the repo derives",
# and this pins the four shapes that broke it. A dated finding that quotes
# a fraction ("36 of 107 knobs named in no .md", 2026-09-15) is a measurement
# with its date on it, and is deliberately NOT matched.
DERIVED_COUNT = re.compile(
    r"§0a`?\.\.`?§|"                    # `§0a`..`§0z22`
    r"\ball\s+\d+(?:,\s*GENERATED|\s+(?:simulation\s+)?knobs)\b|"
    r"\b\d+ of them, derived|"
    r"\b\d+ places in the code|"
    r"~\d[\d,]* lines\b")


def check_durable_docs_derive_counts(docs: dict[str, str]) -> Result:
    """CLAUDE.md and HANDOFF.md quote no count that STATUS.md derives.

    CLAUDE.md says of itself that it carries no dated numbers. It carried
    four -- the issue-id range, the knob count, the cite count and its own
    line count -- and every one had drifted from the repo it described.
    `docs/STATUS.md` derives them now; this fails if they are typed back.
    """
    bad = []
    for path in DURABLE:
        text = docs.get(path, "")
        for m in DERIVED_COUNT.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            bad.append(f"{path}:{line} quotes `{m.group(0)}`")
    return Result("the durable docs quote no count the repo derives",
                  not bad, "; ".join(bad))


def evasion_sets() -> tuple[set[str], set[str]]:
    """(cards the deck modules construct today, cards _evasion.py scanned)."""
    from tools.tag_flying import current_cards
    from edhmc.decks import _evasion
    _creatures, everything = current_cards()
    return set(everything), set(getattr(_evasion, "SCANNED", ()))


def check_evasion_current(live: set[str], scanned: set[str]) -> Result:
    """decks/_evasion.py was regenerated after the last card was added.

    `Card.flying`, `indestructible` and the subtype sets are read from that
    GENERATED file at construction, and the generator needs Scryfall, so
    nothing here can check the TAGS. It can check the coverage: the file
    records every name it scanned, and a card the modules construct that it
    never saw is a card measured with no evasion (§0z29: a 5/5 flier scored
    as a ground creature for a day and a table).
    """
    if not scanned:
        return Result("decks/_evasion.py was regenerated after the last deck change",
                      False, "no SCANNED set -- run `python -m tools.tag_flying --write`")
    missing = sorted(live - scanned)
    stale = sorted(scanned - live)
    bits = []
    if missing:
        bits.append("never scanned: " + ", ".join(missing))
    if stale:
        bits.append("no longer in any module: " + ", ".join(stale))
    return Result("decks/_evasion.py was regenerated after the last deck change",
                  not bits, "; ".join(bits)
                  + ("  -- run `python -m tools.tag_flying --write` (needs Scryfall)"
                     if bits else ""))


def check_architecture_names_modules(docs: dict[str, str]) -> Result:
    """Every module under edhmc/ and tools/ is named in docs/ARCHITECTURE.md.

    The architecture map is hand-written prose, which is to say a claim. This
    is the §0q rule applied to it: a module can be added to the package
    without the map saying where it sits, and then the map is the thing a new
    agent reads and the module is the thing they never find. Named means the
    file's basename appears anywhere in the doc, with or without `.py`.

    BLIND TO, said out loud (§0z15): deck modules matching `<name>_v<N>.py`
    are documented as a PATTERN and are exempt individually, as is any
    `__init__.py`. `diagnostics/` and `tests/` are inventoried by
    `docs/STATUS.md` per script and are only required here as directories.
    """
    name = "docs/ARCHITECTURE.md names every module in edhmc/ and tools/"
    text = docs.get(ARCHITECTURE) or docs.get(ARCHITECTURE.replace(os.sep, "/"), "")
    if not text:
        return Result(name, False, f"{ARCHITECTURE} is missing")
    versioned = re.compile(r"^[a-z0-9]+_v\d+\.py$")
    missing = []
    for d in ("edhmc", "tools"):
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in sorted(files):
                if not f.endswith((".py", ".sh")) or f == "__init__.py":
                    continue
                if versioned.match(f):
                    continue
                stem = f.rsplit(".", 1)[0]
                if not re.search(r"\b" + re.escape(stem) + r"\b", text):
                    missing.append(os.path.join(root, f))
    for d in ("diagnostics/", "tests/"):
        if d not in text:
            missing.append(d)
    return Result(name, not missing,
                  "not named: " + ", ".join(missing) if missing else "")


def generated_checks() -> list[Result]:
    """The generated docs were actually REGENERATED.

    `docs/ABLATION_CACHES.md` is the cautionary tale: generated, marked "do not
    edit by hand", and describing ten cache files that a later commit deleted
    without re-running the generator.
    """
    out = []
    for label, module in (("docs/KNOBS.md", "tools.knobs"),
                          ("docs/STATUS.md", "tools.status"),
                          ("docs/ABLATION_CACHES.md", "tools.cache_manifest")):
        try:
            mod = __import__(module, fromlist=["render"])
            if hasattr(mod, "render"):
                body = mod.render()
            else:  # noqa: RET505
                # cache_manifest.py builds its body inside main() and has no
                # render(). Run it as a subprocess rather than refactor it:
                # SKIPPING was the first version, and a check that skips a
                # category is blind exactly where the bug is (§0z15) -- this
                # was the one generator that turned out to be stale.
                body = subprocess.run(
                    [sys.executable, "-m", module],
                    capture_output=True, text=True, check=True).stdout
            # Normalise BOTH sides identically. The first version rstripped
            # only the file, so a generator whose body ends in a blank line
            # compared unequal to its own output and every generated doc
            # reported stale -- a check that fires when nothing is wrong,
            # which is the failure `cache_manifest.py` warns about by name.
            # Both sides through the SAME normaliser -- see
            # tools/_generated.comparable. It masks the git ref in the
            # provenance line, which otherwise makes every generated doc stale
            # the instant it is committed, and masks nothing else: the cache
            # fingerprints STATUS.md prints are hex too and still compare.
            ok = comparable(have := read(label)) == comparable(body)
            del have
            out.append(Result(
                f"{label} is current",
                ok,
                f"stale -- run `python -m {module} --write`" if not ok else ""))
        except Exception as exc:
            out.append(Result(f"{label} is current", False,
                              f"generator failed: {exc}"))
    return out


def check_caches_recorded() -> Result:
    """Every cache on disk has PROVENANCE, and none is SUSPECT.

    THIS CHECK DELIBERATELY DOES NOT FAIL ON A MOVED FINGERPRINT. It used to,
    and that was §0z23's defect in miniature: `engine.py`, `opponents.py`,
    `experiment.py` and `ablation.py` are in every deck's fingerprint, so any
    shared-file edit turned this red and the only green path was a four-hour
    regeneration. A check whose remedy is unaffordable gets skipped.

    What it fails on now is the thing that is actually wrong:
      UNRECORDED -- a cache nothing knows the origin of;
      SUSPECT    -- the fingerprint moved and NOBODY HAS CHECKED whether the
                    numbers did. The remedy is seconds
                    (`check_unchanged_decks` + `--verified`), not hours.
    CURRENT and VERIFIED both pass. VERIFIED means someone ran the check and
    recorded what it showed, which is a stronger statement than CURRENT.
    """
    try:
        from tools.cache_manifest import (load_provenance, status_of, caches,
                                          CACHE_DIR)
    except Exception as exc:
        return Result("ablation caches have provenance and none is suspect",
                      False, f"could not import: {exc}")
    if not os.path.isdir(CACHE_DIR):
        return Result("ablation caches have provenance and none is suspect",
                      True, "no caches tracked")
    prov = load_provenance()
    problems, states = [], {}
    for name, _deck, _body in caches():
        st, why = status_of(name, prov)
        states[st] = states.get(st, 0) + 1
        if st in ("SUSPECT", "UNRECORDED"):
            problems.append(f"{name}: {st} -- {why}")
    mix = ", ".join(f"{v} {k}" for k, v in sorted(states.items())) or "none"
    return Result(f"ablation caches have provenance and none is suspect ({mix})",
                  not problems, "; ".join(problems))


def live_docs() -> dict[str, str]:
    """Docs that are meant to be current. `docs/archive/` is excluded on
    purpose -- an archived doc is provenance, and holding it to today's repo
    would be the check crying wolf."""
    out = {}
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs
                   if d not in (".git", "__pycache__", "archive")]
        for f in sorted(files):
            if f.endswith(".md"):
                p = os.path.join(root, f)
                out[os.path.relpath(p, ".")] = read(p)
    return out


def run_all() -> list[Result]:
    code_text = "\n".join(read(p) for p in code_files())
    issues = read(KNOWN_ISSUES)
    docs = live_docs()
    live, scanned = evasion_sets()
    results = [
        check_evasion_current(live, scanned),
        check_sections_resolve(code_text, issues),
        check_index_matches_headings(issues),
        check_doc_paths_exist(code_text),
        check_doc_xrefs(docs),
        check_commands_exist(docs),
        check_shell_commands_exist(docs),
        check_architecture_names_modules(docs),
        check_durable_docs_derive_counts(docs),
        check_caches_recorded(),
    ]
    results.extend(generated_checks())
    return results


def report(results: list[Result]) -> int:
    bad = [r for r in results if not r.ok]
    for r in results:
        mark = "ok  " if r.ok else "FAIL"
        print(f"  [{mark}] {r.name}")
        if r.detail:
            for line in r.detail.split("; "):
                print(f"         {line}")
    print()
    if bad:
        print(f"{len(bad)} of {len(results)} checks FAILED.")
        return 1
    print(f"all {len(results)} checks passed.")
    return 0


# --------------------------------------------------------------------------
# Mutation. THE EXPECTED SET IS WRITTEN HERE, BEFORE THE RUN, and is exact.

MUTATIONS = {
    "cite an unknown section from code":
        lambda code, issues, docs: (code + "\n# see §0zz99\n", issues, docs),
    "drop a heading's index row":
        lambda code, issues, docs: (
            code, re.sub(r"^\|\s*\[0j\]\(#0j\).*$", "", issues, count=1,
                         flags=re.M), docs),
    "cite a docs/ path that does not exist":
        lambda code, issues, docs: (
            code + "\n# see docs/NO_SUCH_DOC.md\n", issues, docs),
    "document a command that does not exist":
        lambda code, issues, docs: (
            code, issues, dict(docs, **{"FAKE.md":
                                        "run `python -m tools.nonexistent`"})),
    "a live doc points at a moved file":
        lambda code, issues, docs: (
            code, issues, dict(docs, **{"FAKE2.md": "see docs/MOVED_AWAY.md"})),
    "document a shell script that does not exist":
        lambda code, issues, docs: (
            code, issues, dict(docs, **{"FAKE3.md": "run `./tools/nope.sh`"})),
    "a module vanishes from the architecture map":
        lambda code, issues, docs: (
            code, issues, dict(docs, **{ARCHITECTURE:
                                        docs[ARCHITECTURE].replace("voting", "v0ting")})),
    "a knob count is typed back into CLAUDE.md":
        lambda code, issues, docs: (
            code, issues, dict(docs, **{"CLAUDE.md":
                                        docs["CLAUDE.md"] + "\nall 107 knobs\n"})),
}

# Which checks each mutation must break. Written before running it: a
# mutation list composed after reading the output is a transcript, not a test.
EXPECTED = {
    "cite an unknown section from code": {"every §id cited from code resolves"},
    "drop a heading's index row": {"KNOWN_ISSUES index matches its headings"},
    "cite a docs/ path that does not exist": {"every docs/ path cited from code exists"},
    "document a command that does not exist": {"every `python -m` command in the docs resolves"},
    "a live doc points at a moved file": {"every docs/ path named in a live doc exists"},
    "document a shell script that does not exist":
        {"every `./...sh` command in the docs exists and is executable"},
    "a module vanishes from the architecture map":
        {"docs/ARCHITECTURE.md names every module in edhmc/ and tools/"},
    "a knob count is typed back into CLAUDE.md":
        {"the durable docs quote no count the repo derives"},
    "a card is added to a deck and _evasion.py is not regenerated":
        {"decks/_evasion.py was regenerated after the last deck change"},
}

# Mutations of the evasion coverage sets, (live, scanned) -> (live, scanned).
SET_MUTATIONS = {
    "a card is added to a deck and _evasion.py is not regenerated":
        lambda live, scanned: (live | {"Not A Real Card"}, scanned),
}


def mutate() -> int:
    code_text = "\n".join(read(p) for p in code_files())
    issues = read(KNOWN_ISSUES)
    docs = live_docs()
    live, scanned = evasion_sets()

    failures = 0
    for label in list(MUTATIONS) + list(SET_MUTATIONS):
        if label in MUTATIONS:
            c, i, d = MUTATIONS[label](code_text, issues, docs)
            lv, sc = live, scanned
        else:
            c, i, d = code_text, issues, docs
            lv, sc = SET_MUTATIONS[label](live, scanned)
        results = [
            check_evasion_current(lv, sc),
            check_sections_resolve(c, i),
            check_index_matches_headings(i),
            check_doc_paths_exist(c),
            check_doc_xrefs(d),
            check_commands_exist(d),
            check_shell_commands_exist(d),
            check_architecture_names_modules(d),
            check_durable_docs_derive_counts(d),
        ]
        broke = {r.name.split(" (")[0] for r in results if not r.ok}
        want = EXPECTED[label]
        ok = broke == want
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
        print(f"         broke: {sorted(broke) or 'nothing'}")
        if not ok:
            print(f"         EXPECTED: {sorted(want)}")
            failures += 1
    total = len(MUTATIONS) + len(SET_MUTATIONS)
    print()
    if failures:
        print(f"{failures} of {total} mutations did not produce the "
              f"expected failure set.")
        return 1
    print(f"all {total} mutations produced exactly the expected "
          f"failures -- the checks can fail.")
    return 0


def main() -> int:
    if "--mutate" in sys.argv:
        print("MUTATION RUN -- each mutation must break an exact set of checks\n")
        return mutate()
    print("Checking that the documentation still describes the repository\n")
    return report(run_all())


if __name__ == "__main__":
    raise SystemExit(main())
