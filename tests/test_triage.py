#!/usr/bin/env python3
"""Triage, tier 0: can the engine SEE a card? (queued item 23)

    python -m tests.test_triage
    python -m tests.test_triage --mutate   # 6 mutations, exact sets

`tools/triage.py` derives a card's CHANNELS -- body, land, mana, script,
effect fields, its name in its deck's engine files, a multi-type line -- and
calls a card with none BLIND and a card with only a body BODY. For a card
that exists only as oracle text it screens clause by clause against the §4
limits, and calls it BLIND only if every clause matches and it has no body.

THE ACCEPTANCE TEST IS EXACT. A card the engine cannot see plays IDENTICALLY,
seed for seed under CRN, to a blank matching its cost, types, body, priority
and threat (`triage.matched_blank`). `docs/TRIAGE.md` proposed failing on a
BLIND verdict with a significant row instead; that failed 32 times on
removal spells whose rows are §0j's priority constant, not their text.

CASES
  A  ACCEPTANCE: over every nonland in all six lists, no card called BLIND or
     BODY plays differently from its matched blank (15 seeds), and none
     called BLIND is classified SCRIPTED or PARTLY
  B  karlov's Exquisite Blood, which has no script and is dispatched by name
     (§0z25's shape): SEEN, through `named`
  C  tivit's Counterspell: BLIND
  D  karlov's Sun Titan (implemented in shilgengar, not karlov): BODY
  E  text "Counter target spell." on an Instant: BLIND, the clause named
  F  the same clause on a CREATURE: REVIEW -- a body is always visible
  G  "Return target creature card from your graveyard to the battlefield."
     on a Sorcery: REVIEW, no clause matched -- your own graveyard is seen
  H  tier 2: Sai's smoke run at N=100 reports `sai_thopters` -- a counter
     only the card's arm touches, which the first version DROPPED by
     intersecting the two arms' keys
  I  the ledger: a Proposal triaged BLIND with no clause is refused
  J  ... and one whose clause is not in its oracle text
  K  ... DEFERRED with no machinery named is refused
  L  ... BLIND quoting its own clause, and DEFERRED naming machinery, pass

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the named channel is ignored                    -> A, B
  the body channel is ignored                     -> D
  the text screen ignores a body                  -> F
  every clause with "target" is blind             -> G
  the matched blank drops the body                -> A
  the ledger's triage check does nothing           -> I, J, K

UNMUTATED (§0z15): C and E are the positive BLIND cases the mutations are
measured against; H pins a bug fixed inline in `smoke`, which has no seam.
"""
import sys

import tools.triage as T
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def card(deck, name):
    return next(c for c in build_pending(deck)[0] if c.name == name)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    r = T.backtest(seeds=range(5000, 5015), labels=False)
    check("A acceptance: no BLIND/BODY card plays unlike its matched blank",
          r["violations"], [])
    check("B Exquisite Blood: SEEN through its name",
          (T.structural_verdict(card("karlov", "Exquisite Blood"), "karlov"),
           "named" in T.structural_channels(card("karlov", "Exquisite Blood"),
                                            "karlov")), ("SEEN", True))
    check("C tivit's Counterspell: BLIND",
          T.structural_verdict(card("tivit", "Counterspell"), "tivit"), "BLIND")
    check("D karlov's Sun Titan: BODY",
          T.structural_verdict(card("karlov", "Sun Titan"), "karlov"), "BODY")
    e = T.text_screen("Counter target spell.", "Instant")
    check("E 'Counter target spell.' on an Instant: BLIND, clause named",
          (e["verdict"], e["blind_clauses"]),
          ("BLIND", ["Counter target spell."]))
    check("F the same clause on a creature: REVIEW",
          T.text_screen("When this creature enters, counter target spell.",
                        "Creature — Human Wizard")["verdict"], "REVIEW")
    g = T.text_screen("Return target creature card from your graveyard to "
                      "the battlefield.", "Sorcery")
    check("G your own graveyard: REVIEW, nothing matched",
          (g["verdict"], g["blind_clauses"]), ("REVIEW", []))
    from edhmc.pending import DECKS as CATALOG
    sai = CATALOG["tivit"][1]["Sai, Master Thopterist"]
    rows = T.smoke("tivit", sai, n=100)
    check("H Sai's smoke run reports its own counter",
          any(k == "sai_thopters" and x > 0 for k, x, _, _ in rows), True)
    import edhmc.pending as P
    base = dict(deck="tivit", card="Test Card", cost="{U}", identity="U",
                type_line="Instant", oracle="Counter target spell. Draw a card.",
                verified="2026-09-26", rationale="test", implement="test")

    def refused(**kw):
        try:
            P.check_triage(P.Proposal(**dict(base, **kw)))
        except AssertionError:
            return True
        return False
    check("I BLIND with no clause is refused", refused(triage="BLIND"), True)
    check("J BLIND quoting text the card does not have is refused",
          refused(triage="BLIND", triage_clauses=("Destroy target land.",)),
          True)
    check("K DEFERRED with no machinery is refused",
          refused(triage="DEFERRED"), True)
    check("L well-formed BLIND and DEFERRED pass",
          (refused(triage="BLIND", triage_clauses=("Counter target spell.",)),
           refused(triage="DEFERRED", triage_note="a stack")), (False, False))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Triage, tier 0\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    import edhmc.pending as P
    real = {n: getattr(T, n) for n in
            ("named_in_engine", "structural_channels", "text_screen",
             "matched_blank", "BLIND_CLAUSES")}
    real["check_triage"] = P.check_triage

    def no_body(c, deck_name):
        return [x for x in real["structural_channels"](c, deck_name)
                if x != "body"]

    def body_blind(oracle, type_line):
        return real["text_screen"](oracle, "")

    def bodiless_blank(c):
        b = real["matched_blank"](c)
        b.power = b.toughness = 0
        b.types = frozenset(t for t in b.types if t != "Creature") \
            or frozenset({"Sorcery"})
        return b

    muts = {
        "the named channel is ignored":
            ({"A", "B"}, "named_in_engine", lambda name, deck: False),
        "the body channel is ignored":
            ({"D"}, "structural_channels", no_body),
        "the text screen ignores a body":
            ({"F"}, "text_screen", body_blind),
        "every clause with target is blind":
            ({"G"}, "BLIND_CLAUSES",
             real["BLIND_CLAUSES"] + (("any target", r"\btarget\b"),)),
        "the matched blank drops the body":
            ({"A"}, "matched_blank", bodiless_blank),
        "the ledger's triage check does nothing":
            ({"I", "J", "K"}, "check_triage", lambda pr: None),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        mod = P if name == "check_triage" else T
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
