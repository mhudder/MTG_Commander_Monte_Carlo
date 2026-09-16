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
DOC_PATH = re.compile(r"(?:docs/)?[A-Za-z0-9_\-]+\.md")


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

    43 ids are cited from code today. The ids are load-bearing precisely
    because code cites them, and nothing has ever checked that they land.
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

    The index is how anyone navigates a 4,345-line file. A heading with no row
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


# Docs exempt from the cross-reference check, and WHAT THAT MAKES IT BLIND TO
# -- §0z15's rule, because a checker's exemptions are where its bugs live.
# HISTORY.md is a dated record and legitimately names paths that have since
# moved; holding it to today's tree would flag provenance as breakage. The cost
# is that a genuinely broken link inside HISTORY.md is NOT caught here. Read it
# as a record, and follow its paths with a grep rather than a click.
XREF_EXEMPT = (os.path.join("docs", "HISTORY.md"),)


def check_doc_xrefs(docs: dict[str, str]) -> Result:
    """Every `docs/...md` path a LIVE doc names actually exists.

    Archiving `docs/DECK_CHANGES.md` broke three references in one move, and
    nothing would have noticed: a wrong path in a doc fails silently, at the
    moment someone is already lost.
    """
    bad = []
    for path, body in docs.items():
        if os.path.normpath(path) in [os.path.normpath(x)
                                      for x in XREF_EXEMPT]:
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


def check_generated_current(name: str, ok: bool, detail: str) -> Result:
    return Result(name, ok, detail)


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
    """Every cache on disk has a fingerprint, and it is the live one.

    The repo's rule is "if the fingerprint differs, DELETE the cache". That
    rule is only safe if something checks it, because the cost of ignoring it
    is a run that reprints old numbers while looking like it measured.
    """
    try:
        from tools.status import recorded_fingerprints, live_fingerprints, \
            caches_on_disk
    except Exception as exc:
        return Result("ablation caches match their recorded fingerprints",
                      False, f"could not import: {exc}")
    rec, live, disk = recorded_fingerprints(), live_fingerprints(), \
        caches_on_disk()
    problems = []
    for c in disk:
        deck = c[len("ablation_cache_"):].split("_")[0]
        if c not in rec:
            problems.append(f"{c}: on disk, no recorded fingerprint")
        elif rec[c] != live.get(deck):
            problems.append(f"{c}: recorded {rec[c]}, live {live.get(deck)}")
    for c in rec:
        if c not in disk:
            problems.append(f"{c}: recorded, not on disk")
    return Result(f"ablation caches match their fingerprints "
                  f"({len(disk)} on disk, {len(rec)} recorded)",
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
    results = [
        check_sections_resolve(code_text, issues),
        check_index_matches_headings(issues),
        check_doc_paths_exist(code_text),
        check_doc_xrefs(docs),
        check_commands_exist(docs),
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
}

# Which checks each mutation must break. Written before running it: a
# mutation list composed after reading the output is a transcript, not a test.
EXPECTED = {
    "cite an unknown section from code": {"every §id cited from code resolves"},
    "drop a heading's index row": {"KNOWN_ISSUES index matches its headings"},
    "cite a docs/ path that does not exist": {"every docs/ path cited from code exists"},
    "document a command that does not exist": {"every `python -m` command in the docs resolves"},
    "a live doc points at a moved file": {"every docs/ path named in a live doc exists"},
}


def mutate() -> int:
    code_text = "\n".join(read(p) for p in code_files())
    issues = read(KNOWN_ISSUES)
    docs = live_docs()

    failures = 0
    for label, fn in MUTATIONS.items():
        c, i, d = fn(code_text, issues, docs)
        results = [
            check_sections_resolve(c, i),
            check_index_matches_headings(i),
            check_doc_paths_exist(c),
            check_doc_xrefs(d),
            check_commands_exist(d),
        ]
        broke = {r.name.split(" (")[0] for r in results if not r.ok}
        want = EXPECTED[label]
        ok = broke == want
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
        print(f"         broke: {sorted(broke) or 'nothing'}")
        if not ok:
            print(f"         EXPECTED: {sorted(want)}")
            failures += 1
    print()
    if failures:
        print(f"{failures} of {len(MUTATIONS)} mutations did not produce the "
              f"expected failure set.")
        return 1
    print(f"all {len(MUTATIONS)} mutations produced exactly the expected "
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
