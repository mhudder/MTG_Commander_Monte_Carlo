#!/usr/bin/env python3
"""A SUSPENDED deck is out of every review, and only out of review.

    python -m tests.test_suspended
    python -m tests.test_suspended --mutate   # 1 mutation, exact set

The owner suspended trostani on 2026-10-08: no rebuild, no re-measure, no
evidence check for the near future. `edhmc/registry.py`'s `SUSPENDED` says so
once, and the review tools read it: `regen_tables.sh` and
`check_unchanged_decks` leave the deck out by default, and its cache reads
SUSPENDED rather than SUSPECT when the code moves under it, so `check_docs`
does not demand the rebuild.

CASES
  A  trostani is SUSPENDED, and ACTIVE is every other deck in registry order
  B  a trostani cache whose fingerprint moved reads SUSPENDED
  C  NEIGHBOUR: a karlov cache whose fingerprint moved still reads SUSPECT
  D  check_docs' cache check passes with trostani's fingerprint moved --
     asked about TROSTANI'S CACHE ALONE, so another deck's state cannot
     decide it (it did, until 2026-10-09: §0z123)
  E  check_unchanged_decks measures the ACTIVE decks only, by default
  F  `python -m edhmc.registry --active` -- regen_tables.sh's default list --
     leaves trostani out

MUTATION, WRITTEN BEFORE THE RUN, exact set:
  cache_manifest forgets the suspension (its SUSPENDED is empty)  -> B, D

UNMUTATED (§0z15): A, E and F read the registry itself, which the mutation
does not touch; C is the neighbour and must hold either way.
"""
import subprocess
import sys

import edhmc.registry as R
import tools.cache_manifest as CM
import tools.check_docs as CD
import tools.check_unchanged_decks as CU

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CACHE = "ablation_cache_{}_10-20_n15000_medblank.json"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def moved(prov, *decks):
    """A copy of the provenance with these decks' caches built elsewhere."""
    out = {k: dict(v) for k, v in prov.items()}
    for d in decks:
        out[CACHE.format(d)]["built_at"] = "0" * 16
        out[CACHE.format(d)]["verified"] = []
    return out


def run_cases():
    PASS.clear()
    FAIL.clear()
    real = CM.load_provenance()

    check("A trostani is suspended and the other six are active",
          ("trostani" in R.SUSPENDED, list(R.ACTIVE)),
          (True, [d for d in R.DECKS if d != "trostani"]))

    prov = moved(real, "trostani", "karlov")
    check("B a moved trostani cache reads SUSPENDED",
          CM.status_of(CACHE.format("trostani"), prov)[0], "SUSPENDED")
    check("C NEIGHBOUR: a moved karlov cache reads SUSPECT",
          CM.status_of(CACHE.format("karlov"), prov)[0], "SUSPECT")

    # ONLY TROSTANI'S CACHE IS ASKED ABOUT. This case ran the whole check
    # until 2026-10-09, so its answer was also the state of every OTHER
    # deck's cache: a SUSPECT lorehold (a staged swap, rebuild deferred,
    # §0z123) failed it although nothing about the suspension had moved.
    # `caches` and `shards` are narrowed to trostani's, so the case answers
    # one question -- does the suspension exempt a moved trostani cache?
    saved = CM.load_provenance, CM.caches, CM.shards
    CM.load_provenance = lambda: moved(real, "trostani")
    CM.caches = lambda: [c for c in saved[1]() if c[0] == CACHE.format("trostani")]
    CM.shards = lambda: [p for p in saved[2]() if "trostani" in p]
    try:
        res = CD.check_caches_recorded()
    finally:
        CM.load_provenance, CM.caches, CM.shards = saved
    check("D check_docs passes a moved trostani cache", res.ok, True)

    check("E check_unchanged_decks covers the active decks only",
          tuple(CU.DECKS), R.ACTIVE)

    out = subprocess.run([sys.executable, "-m", "edhmc.registry", "--active"],
                         capture_output=True, text=True, check=True).stdout
    check("F regen_tables' default list leaves trostani out",
          out.split(), list(R.ACTIVE))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("A SUSPENDED deck is out of review (2026-10-08)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact set\n")
    want = {"B", "D"}
    saved = CM.SUSPENDED
    CM.SUSPENDED = {}
    try:
        broke = run_cases()
    finally:
        CM.SUSPENDED = saved
    ok = broke == want
    print(f"   broke {sorted(broke) or 'nothing'}  expected {sorted(want)}  "
          f"{'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{int(ok)} passed, {int(not ok)} failed (1 mutation, exact set)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
