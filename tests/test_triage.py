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
  C  lorehold's Bolt Bend (it redirects the pod's spells, §4): BLIND. Until
     §0z140 this was tivit's Counterspell, which POD_V4 casts on the pod's
     turn -- SEEN now, case M
  D  a constructed 3/3 creature no engine names: BODY. Until 2026-10-13
     this was karlov's Sun Titan, which item 24 implemented there (§0z129),
     then rendmaw's Pygmy Kavu, which §0z132 implemented under `pod_bodies`,
     then lorehold's Hexing Squelcher, whose "can't be countered" §0z151
     implemented -- all three SEEN now, through their names. No KNOWN_BLIND
     card in any deck is a creature after §0z151, so the case is built
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
  M  the pod's channels (§0z140, POD_V4 the default): tivit's Counterspell
     SEEN through `response`, Swords to Plowshares through `answer`,
     Ghostly Prison through `tax`
  N  a constructed body in lorehold's Hexing Squelcher slot plays
     identically to its matched blank, 15 seeds (§0z151). A's population
     held one BODY card, the Squelcher; §0z151 made it SEEN, and A could no
     longer see a blank that drops the body. N is the body A lost

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the named channel is ignored                    -> A, B
  the body channel is ignored                     -> D
  the text screen ignores a body                  -> F
  every clause with "target" is blind             -> G
  the matched blank drops the body                -> N (A until §0z151,
                                                     whose population no
                                                     longer holds a BODY card)
  the ledger's triage check does nothing           -> I, J, K
  (added with M, before its run)
  the pod's channels are ignored                  -> A, M

UNMUTATED (§0z15): C and E are the positive BLIND cases the mutations are
measured against; H pins a bug fixed inline in `smoke`, which has no seam.
"""
import sys

import tools.triage as T
from edhmc.engine import Card
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
    check("C lorehold's Bolt Bend: BLIND",
          T.structural_verdict(card("lorehold", "Bolt Bend"), "lorehold"),
          "BLIND")
    body = Card(name="Triage Test Body", types=frozenset({"Creature"}),
                power=3, toughness=3, cost={"gen": 3})
    check("D a creature no engine names: BODY",
          T.structural_verdict(body, "lorehold"), "BODY")
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
    check("M the pod's channels: response, answer, tax",
          [T.structural_channels(card("tivit", n), "tivit")[-1:]
           for n in ("Counterspell", "Swords to Plowshares", "Ghostly Prison")],
          [["response"], ["answer"], ["tax"]])
    check("N a constructed body plays identically to its matched blank",
          body_plays_identically(), True)
    return set(FAIL)


def body_plays_identically() -> bool:
    """`plays_identically`'s comparison, for a BODY card no deck holds."""
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.registry import DECKS as REG
    deck, cmd = build_pending("lorehold")
    i = next(k for k, c in enumerate(deck) if c.name == "Hexing Squelcher")
    sq = deck[i]
    body = Card(name="Triage Test Body", types=sq.types, cost=dict(sq.cost),
                power=sq.power, toughness=sq.toughness, priority=sq.priority,
                threat=sq.threat)
    a, b = list(deck), list(deck)
    a[i], b[i] = body, T.matched_blank(body)
    sim = REG["lorehold"].sim
    for s in range(5000, 5015):
        ra = sim(a, cmd, dict(DEFAULT_CFG, turns=20), s)
        rb = sim(b, cmd, dict(DEFAULT_CFG, turns=20), s)
        if any(isinstance(v, (int, float)) and v != rb.get(k)
               for k, v in ra.items()):
            return False
    return True


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
             "matched_blank", "BLIND_CLAUSES", "pod_channels")}
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
            ({"N"}, "matched_blank", bodiless_blank),
        "the ledger's triage check does nothing":
            ({"I", "J", "K"}, "check_triage", lambda pr: None),
        "the pod's channels are ignored":
            ({"A", "M"}, "pod_channels", lambda c: []),
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
