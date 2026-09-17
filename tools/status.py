#!/usr/bin/env python3
"""Derive the project's CURRENT STATE from the repo, instead of remembering it.

WHY THIS EXISTS. `CLAUDE.md` used to carry a 351-line "Current state" section:
58 date stamps and 82 point estimates, hand-written, describing which tables
were current, what each one's noise floor was, what was staged, and which
checks had last passed. That section was a THIRD of the file and every session
rewrote a chunk of it -- 3,548 lines of churn across twelve commits on a
1,042-line file. Keeping it accurate WAS the memory tax this tool exists to
remove.

Every number below is read off the artefact that produced it: the table headers
in `results/`, the fingerprints in `tools/cache_manifest`, the ledger in
`edhmc/pending`, the index in `KNOWN_ISSUES.md`, the modules on disk. Nothing
here is remembered, so nothing here can go stale without the underlying thing
having moved.

WHAT IT DELIBERATELY DOES NOT DO. It does not run the simulator. It cannot tell
you `validate.py` is `+0.00` today -- only that the tables and caches are
mutually consistent. Freshness of a CHECK is not derivable from the filesystem,
and printing a cheerful "all tests pass" that nothing verified is exactly the
failure mode this project keeps finding in its own documentation. Where the
answer needs a run, this prints the COMMAND instead of an answer.

    python -m tools.status            # print
    python -m tools.status --write    # regenerate docs/STATUS.md
    python -m tools.status --check    # exit 1 if docs/STATUS.md is out of date
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

from tools._generated import comparable, head

OUT = os.path.join("docs", "STATUS.md")
RESULTS = "results"
DECKS = ["rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa"]

RE_N = re.compile(r"N\s*=\s*([\d,]+)\s+paired games")
RE_HORIZ = re.compile(r"Horizons:\s*\(([^)]*)\)")
RE_FLOOR = re.compile(r"median win-rate CI half-width over this deck is "
                      r"\+-([\d.]*\d)")
RE_SEEDS = re.compile(r"seeds\s+([\d.]+\.\.[\d]+)")
SECTIONS = ("MODEL-EVALUATED", "PARTLY MODELLED", "MODEL-BLIND")
# A data row is identified SEMANTICALLY -- it carries a paired figure and
# ends in one of the signal classifications -- rather than by column
# offset. The first version keyed on a 38-character name field and
# counted ZERO rows in five of six tables, because the name field is
# exactly 38 wide and the value starts AT 38 with no space before it. A
# parser that silently returns nothing is the shape of bug this whole
# package exists to stop shipping.
SIGNALS = ("both", "dmg", "win", "--", "FLIP")
RE_ROW = re.compile(r"\+-\d")


def sh(*args: str) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return ""


def last_commit(path: str) -> str:
    """The date of the commit that last touched a file, or '' if untracked.

    This is the table's real date. The hand-written one in CLAUDE.md was a
    claim; this one cannot disagree with the repository.
    """
    return sh("git", "log", "-1", "--format=%ad", "--date=short", "--", path)


def dirty(path: str) -> bool:
    return bool(sh("git", "status", "--porcelain", "--", path))


# --------------------------------------------------------------------------
# Tables


class Table:
    def __init__(self, deck: str):
        self.deck = deck
        self.path = os.path.join(RESULTS, f"ablation_{deck}.txt")
        self.exists = os.path.isfile(self.path)
        self.n = self.horizons = self.floor = self.seeds = ""
        self.rows: dict[str, int] = {}
        self.date = ""
        self.dirty = False
        if self.exists:
            self._parse()

    def _parse(self) -> None:
        with open(self.path, "r", encoding="utf-8", errors="ignore") as fh:
            body = fh.read()
        lines = body.splitlines()
        for rx, attr in ((RE_N, "n"), (RE_HORIZ, "horizons"),
                         (RE_FLOOR, "floor"), (RE_SEEDS, "seeds")):
            m = rx.search(body)
            if m:
                setattr(self, attr, m.group(1).strip())
        current = None
        for line in lines:
            hit = next((s for s in SECTIONS if line.startswith(s)), None)
            if hit:
                current = hit
                self.rows.setdefault(current, 0)
                continue
            if (current and RE_ROW.search(line)
                    and line.rsplit(" ", 1)[-1].strip() in SIGNALS):
                self.rows[current] += 1
        self.date = last_commit(self.path)
        self.dirty = dirty(self.path)

    @property
    def total(self) -> int:
        return sum(self.rows.values())


# --------------------------------------------------------------------------
# Caches and fingerprints


def recorded_fingerprints() -> dict[str, str]:
    """Parse the fingerprint table out of the GENERATED cache manifest."""
    path = os.path.join("docs", "ABLATION_CACHES.md")
    out: dict[str, str] = {}
    if not os.path.isfile(path):
        return out
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            m = re.match(r"\|\s*`(ablation_cache_[^`]+)`\s*\|\s*(\w+)\s*\|"
                         r"\s*(\d+)\s*\|\s*`(\w+)`\s*\|", line)
            if m:
                out[m.group(1)] = m.group(4)
    return out


def live_fingerprints() -> dict[str, str]:
    try:
        from tools.cache_manifest import fingerprint, PER_DECK
        return {d: fingerprint(d)[0] for d in PER_DECK}
    except Exception as exc:                                # pragma: no cover
        print(f"  (fingerprints unavailable: {exc})", file=sys.stderr)
        return {}


def caches_on_disk() -> list[str]:
    d = os.path.join(RESULTS, "caches")
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d)
                  if f.startswith("ablation_cache_") and f.endswith(".json"))


# --------------------------------------------------------------------------
# Ledger


def ledger_counts():
    """Counts and staged entries straight out of `edhmc.pending`.

    `CLAUDE.md` has always said this module is the only trustworthy statement
    of what is staged, and then restated its contents in prose two sections
    later. This reads the module.
    """
    try:
        from edhmc import pending
    except Exception as exc:
        return None, f"could not import edhmc.pending: {exc}"
    buckets = {
        "COMMITTED": pending.COMMITTED,
        "STAGED": pending.CHANGES,
        "MEASURED": pending.MEASURED,
        "WITHDRAWN": pending.WITHDRAWN,
    }
    per: dict[str, dict[str, int]] = {}
    for label, items in buckets.items():
        for it in items:
            per.setdefault(it.deck, {}).setdefault(label, 0)
            per[it.deck][label] += 1
    return (buckets, per), ""


# --------------------------------------------------------------------------
# Issues index


def issue_index() -> list[tuple[str, str, str]]:
    """(id, status, one-line finding) from KNOWN_ISSUES.md's index table."""
    out = []
    path = "KNOWN_ISSUES.md"
    if not os.path.isfile(path):
        return out
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            m = re.match(r"\|\s*\[([0-9a-z]+)\]\(#[0-9a-z]+\)\s*\|"
                         r"\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", line)
            if m:
                out.append((m.group(1), m.group(2).replace("*", ""),
                            m.group(3)))
    return out


# --------------------------------------------------------------------------
# Inventory


def first_doc_line(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            src = fh.read()
    except OSError:
        return ""
    # `\s*` first: four tools open their docstring on the line AFTER the
    # quotes, and without it they listed under "What can be run" with no
    # description at all.
    m = re.search(r'"""\s*(.*?)(?:\n|""")', src, re.S)
    return m.group(1).strip() if m else ""


def inventory(d: str) -> list[tuple[str, str]]:
    """Runnable entry points in a directory, with their one-line docstring.

    LEADING-UNDERSCORE MODULES ARE EXCLUDED and here is what that hides: a
    private helper like `tools/_generated.py` is a library, not something you
    run, and listing `python -m tools._generated` under "what can be run" would
    be an instruction to do a meaningless thing. The cost is that a private
    module never appears in this inventory at all, so it is invisible here
    however large it grows -- read the directory, not this table, when you are
    looking for code rather than for a command. (§0z15: when you write an
    exemption into a checker, write down what it is now blind to.)
    """
    if not os.path.isdir(d):
        return []
    out = []
    for f in sorted(os.listdir(d)):
        if f.endswith(".py") and not f.startswith("_"):
            out.append((f[:-3], first_doc_line(os.path.join(d, f))))
    return out


# --------------------------------------------------------------------------


def render() -> str:
    L: list[str] = []
    w = L.append

    tables = {d: Table(d) for d in DECKS}
    rec = recorded_fingerprints()
    live = live_fingerprints()
    disk = caches_on_disk()
    (buckets, per), ledger_err = ledger_counts() if ledger_counts()[0] else (
        (None, None), ledger_counts()[1])
    issues = issue_index()
    knob_n = knob_count()

    w("# Status")
    w("")
    w("GENERATED by `python -m tools.status --write`. **Do not edit by hand.**")
    w("")
    w(f"Derived at `{head()}`. Every figure below is read off the artefact that")
    w("produced it — the table headers in `results/`, the fingerprints in")
    w("`tools/cache_manifest`, the ledger in `edhmc/pending`, the index in")
    w("`KNOWN_ISSUES.md`, the modules on disk. **Nothing here is remembered,**")
    w("so nothing here can be stale without the thing it describes having moved.")
    w("")
    w("**What this file cannot tell you.** Whether `validate.py` prints `+0.00`")
    w("today, whether the tests pass, whether a number is *right*. Freshness of")
    w("a check is not derivable from the filesystem, and a cheerful \"all checks")
    w("pass\" that nothing verified is the exact failure this project keeps")
    w("finding in its own documentation. Run the commands in **Before you trust")
    w("a number** below.")
    w("")

    # ---- tables
    w("## The six ablation tables")
    w("")
    w("`rows` counts the printed card rows, split by category. A MODEL-BLIND")
    w("row is **not measured**, never a cut candidate.")
    w("")
    w("| deck | table | N | horizons | noise floor | rows (eval/partial/blind) | last commit |")
    w("|---|---|---|---|---|---|---|")
    for d in DECKS:
        t = tables[d]
        if not t.exists:
            w(f"| {d} | **MISSING** | — | — | — | — | — |")
            continue
        r = t.rows
        split = "/".join(str(r.get(s, 0)) for s in SECTIONS)
        flag = " *(uncommitted edits)*" if t.dirty else ""
        w(f"| {d} | `{os.path.basename(t.path)}` | {t.n} | {t.horizons} | "
          f"±{t.floor} | {split} = {t.total} | {t.date}{flag} |")
    w("")
    tot = sum(t.total for t in tables.values() if t.exists)
    w(f"**{tot} rows across six tables.**")
    w("")

    # ---- caches
    w("## Ablation caches")
    w("")
    w("`ablation.py` keys its cache on deck, horizons, N and blank mode — **not")
    w("on the code that produced it** — so a stale cache makes a run reprint old")
    w("numbers instead of measuring. The fingerprint is the guard;")
    w("`docs/ABLATION_CACHES.md` records it.")
    w("")
    w(f"**{len(disk)} cache files on disk; {len(rec)} recorded in the manifest.**")
    w("")
    missing = [c for c in rec if c not in disk]
    extra = [c for c in disk if c not in rec]
    if missing:
        w(f"**{len(missing)} caches are recorded in the manifest but ARE NOT ON")
        w("DISK.** The manifest is a generated file that was not regenerated")
        w("after the caches were deleted, so it is describing files that no")
        w("longer exist:")
        w("")
        for c in sorted(missing):
            w(f"- `{c}`")
        w("")
    if extra:
        w("**On disk but unrecorded** — no provenance, so do not resume onto "
          "these:")
        w("")
        for c in sorted(extra):
            w(f"- `{c}`")
        w("")
    w("Per-deck state. **A moved fingerprint is SUSPECT, not condemned** —")
    w("resolve it with `tools/check_unchanged_decks.py` against a worktree at")
    w("the cache's `built_commit` (seconds), then record it with")
    w("`python -m tools.cache_manifest --verified <deck> \"<evidence>\"`.")
    w("§0z23 for why the old \"delete it\" rule was the defect.")
    w("")
    w("| deck | built at | live | state | caches |")
    w("|---|---|---|---|---|")
    try:
        from tools.cache_manifest import load_provenance, status_of
        prov = load_provenance()
    except Exception:
        prov, status_of = {}, None
    for d in DECKS:
        lf = live.get(d, "")
        mine = sorted(c for c in disk if c.startswith(f"ablation_cache_{d}_"))
        if not mine:
            w(f"| {d} | — | `{lf or '?'}` | **no cache** | 0 |")
            continue
        sts, builts = [], []
        for c in mine:
            sts.append(status_of(c, prov)[0] if status_of else "?")
            builts.append(prov.get(c, {}).get("built_at", "—"))
        w(f"| {d} | `{'/'.join(sorted(set(builts)))}` | `{lf or '?'}` | "
          f"**{'/'.join(sorted(set(sts)))}** | {len(mine)} |")
    w("")

    # ---- ledger
    w("## The ledger")
    w("")
    w("Straight out of `edhmc/pending.py`, which is the only trustworthy")
    w("statement of what is staged. Run `python -m edhmc.pending` for the")
    w("evidence behind each entry.")
    w("")
    if ledger_err:
        w(f"*Unavailable: {ledger_err}*")
        w("")
    else:
        w("| deck | committed | staged | measured | withdrawn |")
        w("|---|---|---|---|---|")
        for d in DECKS:
            c = per.get(d, {})
            w(f"| {d} | {c.get('COMMITTED', 0)} | {c.get('STAGED', 0)} | "
              f"{c.get('MEASURED', 0)} | {c.get('WITHDRAWN', 0)} |")
        w(f"| **all** | **{len(buckets['COMMITTED'])}** | "
          f"**{len(buckets['STAGED'])}** | **{len(buckets['MEASURED'])}** | "
          f"**{len(buckets['WITHDRAWN'])}** |")
        w("")
        w("### Staged and uncommitted")
        w("")
        if buckets["STAGED"]:
            w("| deck | out | in | staged |")
            w("|---|---|---|---|")
            for ch in buckets["STAGED"]:
                w(f"| {ch.deck} | {ch.remove} | {ch.add} | {ch.staged} |")
        else:
            w("Nothing staged.")
        w("")
        if buckets["WITHDRAWN"]:
            w("### Withdrawn")
            w("")
            w("Staged and then unstaged. **Not a refutation** — the entry is kept")
            w("so the same card is not re-measured from scratch.")
            w("")
            w("| deck | out | in | withdrawn |")
            w("|---|---|---|---|")
            for ch in buckets["WITHDRAWN"]:
                w(f"| {ch.deck} | {ch.remove} | {ch.add} | "
                  f"{(ch.withdrawn or '').splitlines()[0][:80]} |")
            w("")

    # ---- issues
    w("## Open findings")
    w("")
    w("From `KNOWN_ISSUES.md`'s index. **The section ids are load-bearing** —")
    w("they are cited from code — so they are never renumbered.")
    w("")
    newest, n_sections = newest_section()
    cited = code_cite_count()
    w(f"**{n_sections} sections**, newest `§{newest}`; **{cited} distinct ids")
    w("cited from code**. These figures used to be typed into CLAUDE.md and")
    w("HANDOFF.md and had rotted; they are derived here now, and `check_docs`")
    w("fails if either file quotes one by hand.")
    w("")
    if issues:
        by_status: dict[str, int] = {}
        for _id, status, _txt in issues:
            by_status[status] = by_status.get(status, 0) + 1
        w(" · ".join(f"**{k}** {v}" for k, v in sorted(by_status.items())))
        w("")
        live_ones = [i for i in issues if "OPEN" in i[1].upper()]
        if live_ones:
            w("Still live:")
            w("")
            for _id, status, txt in live_ones:
                w(f"- **§{_id}** — {txt}")
            w("")
    else:
        w("*Index unreadable.*")
        w("")

    # ---- inventory
    w("## What can be run")
    w("")
    w("Discovered from disk, so this list cannot drift from the modules that")
    w("exist — which the hand-written lists it replaces had already done, in")
    w("seven places. **Everything runs from the repo root with `-m`.**")
    w("")
    for label, d in (("tools", "tools"), ("tests", "tests"),
                     ("diagnostics", "diagnostics")):
        items = inventory(d)
        w(f"### `{d}/` — {len(items)}")
        w("")
        w("| command | what it does |")
        w("|---|---|")
        for name, doc in items:
            doc = doc.replace("|", "\\|")
            w(f"| `python -m {d}.{name}` | {doc[:110]} |")
        w("")
    shell = sorted(f for f in os.listdir("tools") if f.endswith(".sh")) \
        if os.path.isdir("tools") else []
    for f in shell:
        w(f"Also `./tools/{f}`.")
    if shell:
        w("")

    # ---- results and spreadsheets on disk
    w("## What is in results/ and spreadsheets/")
    w("")
    w("Every `results/*.txt` is the evidence for some number, and evidence is")
    w("kept -- but a file nothing names is evidence for nothing anyone can")
    w("find. `cited by` is derived by searching the code, `KNOWN_ISSUES.md`,")
    w("the live docs and `docs/HISTORY.md` for each file's name.")
    w("")
    cites = results_citations()
    tally: dict[str, int] = {}
    for _f, where in cites:
        tally[where] = tally.get(where, 0) + 1
    w(f"**{len(cites)} result files**: " + " · ".join(
        f"{v} cited by {k}" for k, v in sorted(tally.items(),
                                               key=lambda kv: -kv[1])))
    w("")
    orphans = [f for f, where in cites if where in ("HISTORY.md only", "nothing")]
    if orphans:
        w("Cited only from `docs/HISTORY.md`, or from nowhere -- the dated")
        w("narrative is the only way back to what produced them:")
        w("")
        for f in orphans:
            w(f"- `{f}`")
        w("")
    w("Spreadsheets are the system of record for a deck (azusa has none),")
    w("matched to a module by name and version:")
    w("")
    for xlsx, verdict in spreadsheet_modules():
        w(f"- `{xlsx}` — {verdict}")
    w("")

    # ---- knobs
    w("## Knobs")
    w("")
    w(f"**{knob_n} knobs** are read by the engines. The registry, with defaults,")
    w("call sites and which have never been swept, is `docs/KNOBS.md`")
    w("(generated by `python -m tools.knobs --write`).")
    w("")

    # ---- what to run
    w("## Before you trust a number")
    w("")
    w("None of these can be derived from the filesystem, so they are printed as")
    w("commands rather than as answers:")
    w("")
    w("```bash")
    w("python -m tools.validate        # must print +0.00 on all 18 metrics")
    w("python -m edhmc.pending         # staged changes, and deck legality")
    w("python -m tools.check_docs      # do the docs still match the repo?")
    w("python -m tools.audit_cards     # every card against Scryfall; expect 0 ERR")
    w("```")
    w("")
    w("`tools/validate.py` is the non-negotiable one: anything other than")
    w("`+0.00` means randomness is leaking between the branches of every A/B")
    w("test in the project, and no number here can be trusted until it is fixed.")
    w("")
    return "\n".join(L) + "\n"


def newest_section() -> tuple[str, int]:
    """(newest 0z-series id, number of 0-series sections) from the headings."""
    try:
        with open("KNOWN_ISSUES.md", "r", encoding="utf-8", errors="ignore") as fh:
            heads = re.findall(r"^## (0[a-z0-9]*)\.", fh.read(), re.M)
    except OSError:
        return "?", 0
    z = [int(h[2:]) for h in heads if re.fullmatch(r"0z\d+", h)]
    return (f"0z{max(z)}" if z else (heads[-1] if heads else "?")), len(heads)


def code_cite_count() -> int:
    """Distinct §ids cited from code -- the same scan check_docs verifies."""
    try:
        from tools.check_docs import SECTION_CITE, code_files, read
        text = "\n".join(read(p) for p in code_files())
        return len(set(SECTION_CITE.findall(text)))
    except Exception:
        return 0


def _searchable_text() -> dict[str, str]:
    """{bucket: text} over which a results/ or spreadsheets/ name is looked up."""
    out: dict[str, list[str]] = {"code": [], "KNOWN_ISSUES.md": [],
                                 "live docs": [], "HISTORY.md only": []}
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs
                   if d not in (".git", "__pycache__", "archive", "results",
                                "spreadsheets")]
        for f in files:
            p = os.path.relpath(os.path.join(root, f), ".")
            if p == OUT:
                continue        # this file lists them all; it is not a citer
            if f.endswith((".py", ".sh")):
                bucket = "code"
            elif p == "KNOWN_ISSUES.md":
                bucket = "KNOWN_ISSUES.md"
            elif p == os.path.join("docs", "HISTORY.md"):
                bucket = "HISTORY.md only"
            elif f.endswith(".md"):
                bucket = "live docs"
            else:
                continue
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                    out[bucket].append(fh.read())
            except OSError:
                pass
    return {k: "\n".join(v) for k, v in out.items()}


def results_citations() -> list[tuple[str, str]]:
    """[(file, strongest citer)] for every results/*.txt, in the order
    code > KNOWN_ISSUES.md > live docs > HISTORY.md only > nothing."""
    if not os.path.isdir(RESULTS):
        return []
    text = _searchable_text()
    out = []
    for f in sorted(os.listdir(RESULTS)):
        if not f.endswith(".txt"):
            continue
        where = "nothing"
        for bucket in ("code", "KNOWN_ISSUES.md", "live docs", "HISTORY.md only"):
            if f in text[bucket]:
                where = bucket
                break
        out.append((f, where))
    return out


def spreadsheet_modules() -> list[tuple[str, str]]:
    """[(xlsx, verdict)] -- each spreadsheet matched to the deck module whose
    NAME it starts with. The deck modules are `<name>_v<N>.py` and the
    spreadsheets `<Name>_..._v<N>.xlsx`, so the match is the leading token
    and the verdict compares versions: the system of record, a superseded
    version kept as provenance, or a deck with no module at all."""
    d = "spreadsheets"
    if not os.path.isdir(d):
        return []
    try:
        from edhmc.decks import discover_current_decks
        mods = {name: mod.__name__.rsplit(".", 1)[-1]
                for name, mod in discover_current_decks().items()}
    except Exception:
        mods = {}
    out = []
    for xlsx in sorted(os.listdir(d)):
        if not xlsx.endswith(".xlsx"):
            continue
        name = xlsx.split("_", 1)[0].lower()
        m = re.search(r"_v(\d+)\.xlsx$", xlsx)
        ver = int(m.group(1)) if m else None
        if name not in mods:
            verdict = "**no deck module** -- a deck this project has not built"
        else:
            mv = re.search(r"_v(\d+)$", mods[name])
            mver = int(mv.group(1)) if mv else None
            if ver is not None and mver is not None and ver < mver:
                verdict = f"superseded by `{mods[name]}.py`; kept as provenance"
            else:
                verdict = f"system of record for `{mods[name]}.py`"
        out.append((xlsx, verdict))
    return out


def knob_count() -> int:
    try:
        from tools.knobs import scan
        return len(scan())
    except Exception:
        return 0


def main() -> int:
    body = render()
    if "--write" in sys.argv:
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write(body)
        print(f"wrote {OUT}")
        return 0
    if "--check" in sys.argv:
        try:
            with open(OUT, "r", encoding="utf-8") as fh:
                have = fh.read()
        except OSError:
            print(f"MISSING {OUT} -- run `python -m tools.status --write`")
            return 1
        if comparable(have) != comparable(body):
            print(f"STALE {OUT} -- run `python -m tools.status --write`")
            return 1
        print(f"{OUT} is current")
        return 0
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
