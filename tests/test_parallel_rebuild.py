#!/usr/bin/env python3
"""A parallel rebuild's provenance: legs stamp shards, the coordinator merges
them, and nothing is merged that was built on other code (§0z94).

    python -m tests.test_parallel_rebuild
    python -m tests.test_parallel_rebuild --mutate   # 3 mutations, exact sets

Every case runs in its own temporary cache directory, so the repository's
PROVENANCE.json is never read or written.

CASES
  A  with PROVENANCE_SHARD set, a stamp goes to provenance.<deck>.json and
     PROVENANCE.json is not written
  B  --merge-shards folds the shard into PROVENANCE.json and deletes it
  C  a shard whose built-at fingerprint is not the live one is REFUSED:
     nothing is merged and the shard stays
  D  NEIGHBOUR: without PROVENANCE_SHARD a stamp writes PROVENANCE.json, as it
     always did, and makes no shard
  E  check_docs' cache check fails while a shard is unmerged
  F  a shard carries the record it supersedes, so a rebuild's history is
     longer and not different (stamp_built's `fresh` rule)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  stamp_built ignores PROVENANCE_SHARD            -> A, F
  the merge accepts any fingerprint               -> C
  nothing can see a shard (shards() is empty)     -> B, C, E

UNMUTATED (§0z15): D is the neighbour -- the serial path is unchanged.
"""
import json
import os
import sys
import tempfile

import tools.cache_manifest as CM
import tools.check_docs as CD

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
NAME = "ablation_cache_karlov_10-20_n15000_medblank.json"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


class Sandbox:
    """A temporary CACHE_DIR with one (empty) karlov cache in it."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = (CM.CACHE_DIR, CM.PROVENANCE)
        CM.CACHE_DIR = self.tmp.name
        CM.PROVENANCE = os.path.join(self.tmp.name, "PROVENANCE.json")
        with open(os.path.join(self.tmp.name, NAME), "w") as fh:
            json.dump({}, fh)
        return self

    def __exit__(self, *exc):
        CM.CACHE_DIR, CM.PROVENANCE = self.saved
        os.environ.pop("PROVENANCE_SHARD", None)
        self.tmp.cleanup()

    @property
    def shard(self):
        return os.path.join(self.tmp.name, "provenance.karlov.json")


def run_cases():
    PASS.clear()
    FAIL.clear()
    with Sandbox() as sb:
        os.environ["PROVENANCE_SHARD"] = "1"
        CM.stamp_built(NAME, "karlov", fresh=True)
        check("A a shard, and PROVENANCE.json untouched",
              (os.path.exists(sb.shard), os.path.exists(CM.PROVENANCE)),
              (True, False))
    with Sandbox() as sb:
        os.environ["PROVENANCE_SHARD"] = "1"
        CM.stamp_built(NAME, "karlov", fresh=True)
        os.environ.pop("PROVENANCE_SHARD")
        CM.merge_shards()
        check("B merged into PROVENANCE.json, shard gone",
              (NAME in CM.load_provenance(), os.path.exists(sb.shard)),
              (True, False))
    with Sandbox() as sb:
        with open(sb.shard, "w") as fh:
            json.dump({NAME: {"deck": "karlov", "built_at": "0" * 16,
                              "built_commit": "x", "verified": []}}, fh)
        try:
            CM.merge_shards()
            refused = False
        except SystemExit:
            refused = True
        check("C a shard built on other code is refused, nothing merged",
              (refused, NAME in CM.load_provenance(),
               os.path.exists(sb.shard)), (True, False, True))
    with Sandbox() as sb:
        CM.stamp_built(NAME, "karlov", fresh=True)
        check("D without the variable: PROVENANCE.json, no shard",
              (NAME in CM.load_provenance(), os.path.exists(sb.shard)),
              (True, False))
    with Sandbox() as sb:
        CM.stamp_built(NAME, "karlov", fresh=True)        # a recorded cache
        with open(sb.shard, "w") as fh:
            json.dump({}, fh)
        r = CD.check_caches_recorded()
        check("E check_docs fails on an unmerged shard",
              (r.ok, "unmerged provenance shard" in r.detail), (False, True))
    with Sandbox() as sb:
        CM.stamp_built(NAME, "karlov", fresh=True)        # the old record
        old = CM.load_provenance()[NAME]["built_utc"]
        os.environ["PROVENANCE_SHARD"] = "1"
        CM.stamp_built(NAME, "karlov", fresh=True)
        shard = (json.load(open(sb.shard)) if os.path.exists(sb.shard)
                 else {})
        sup = shard.get(NAME, {}).get("superseded", [])
        check("F the shard supersedes the old record",
              [s.get("built_utc") for s in sup], [old])
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Parallel rebuild provenance (§0z94)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_stamp = CM.stamp_built

    def ignores_shard(*a, **k):
        v = os.environ.pop("PROVENANCE_SHARD", None)
        try:
            real_stamp(*a, **k)
        finally:
            if v is not None:
                os.environ["PROVENANCE_SHARD"] = v

    muts = {
        "stamp_built ignores PROVENANCE_SHARD":
            ({"A", "F"}, (CM, "stamp_built", ignores_shard)),
        "the merge accepts any fingerprint":
            ({"C"}, (CM, "fingerprint", lambda deck: ("0" * 16, []))),
        "nothing can see a shard":
            ({"B", "C", "E"}, (CM, "shards", lambda: [])),
    }
    bad = 0
    for label, (want, (owner, name, fn)) in muts.items():
        print(f"-- {label}")
        real = getattr(owner, name)
        setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(owner, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
