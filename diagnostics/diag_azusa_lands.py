#!/usr/bin/env python3
"""Does the Azusa engine sequence its land drops the way a pilot would?

Three claims to check, none of which the engine was written to satisfy:

  1. ZONE PRIORITY. A land on top of the library (Courser / Augur / Oracle)
     or in the graveyard (Ramunap Excavator / Crucible) should be played
     BEFORE a land from hand. The hand land keeps; the top-of-library one is
     only there until something draws it, and playing it is what turns the
     top-deck enabler into card advantage.
  2. FORESIGHT. If a top-of-library enabler is going to resolve this turn,
     the land drop should wait for it, so the top card can be checked.
  3. LOTUS COBRA. Cobra should be on the battlefield BEFORE the land drops,
     so each drop makes mana that the main phase can still spend.

Reports the size of the gap, not just its existence.

    python diag_azusa_lands.py [n_games]
"""
import sys
import collections

from edhmc.experiment import DEFAULT_CFG
from edhmc.decks.azusa_v1 import build
from edhmc import azusa as AZ

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
TOP_ENABLERS = ("Courser of Kruphix", "Augur of Autumn", "Oracle of Mul Daya")
GY_ENABLERS = ("Ramunap Excavator", "Crucible of Worlds")


# ---------------------------------------------------------------------------
# 1. Zone priority -- a direct unit check on the selection rule, no simulation
# ---------------------------------------------------------------------------
def _state(gy=(), board=(), top=None):
    """A game with a hand land, and whatever else the case needs."""
    deck, cmd = build()
    cfg = dict(DEFAULT_CFG, turns=20, watch=frozenset())
    g = AZ.AzusaGame(deck, cmd, cfg, 1)
    pick = lambda n: next(c for c in g.library if c.name == n)

    g.hand = [pick("Forest")]
    g.graveyard = [pick(n) for n in gy]
    for n in board:
        g.board.append(AZ.Permanent(card=pick(n), sick=False))
    if top is not None:
        card = pick(top)
        g.library.remove(card)
        g.library.append(card)          # library[-1] is the top
    return g


def check_zone_priority():
    print("1. ZONE PRIORITY  (hand land always available; what does it pick?)")
    cases = [
        ("plain graveyard land, Crucible out",
         dict(gy=["Wasteland"], board=["Crucible of Worlds"], top="Harmonize"),
         "graveyard"),
        ("land on top, Courser out",
         dict(gy=[], board=["Courser of Kruphix"], top="Wasteland"),
         "library"),
        ("THE REROLL LINE: graveyard FETCH + top access + top is NOT a land",
         dict(gy=["Windswept Heath"], board=["Crucible of Worlds",
                                             "Courser of Kruphix"],
              top="Harmonize"),
         "graveyard"),
        ("same, but the top IS a land -- take the free land instead",
         dict(gy=["Windswept Heath"], board=["Crucible of Worlds",
                                             "Courser of Kruphix"],
              top="Wasteland"),
         "library"),
    ]
    ok = True
    for label, kw, want in cases:
        g = _state(**kw)
        choice = g.choose_land(g.playable_lands())
        got_card, got_zone = choice
        good = got_zone == want
        ok = ok and good
        print(f"   {'ok ' if good else 'FAIL'} {label}")
        print(f"        -> {got_zone:10} {got_card.name:22} "
              f"(wanted {want})")
    print(f"   VERDICT               : "
          f"{'zone-aware, reroll line understood' if ok else 'WRONG'}")
    return ok


# ---------------------------------------------------------------------------
# 2 & 3. Foresight and Cobra sequencing, measured over real games
# ---------------------------------------------------------------------------
class Instrumented(AZ.AzusaGame):
    """Records the state at the moment a key permanent RESOLVES. Adds no
    behaviour -- it calls through to the real resolve()."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.obs = []

    def resolve(self, card):
        if card.name in TOP_ENABLERS + GY_ENABLERS + ("Lotus Cobra",):
            self.obs.append({
                "name": card.name,
                "turn": self.turn,
                "drops_left": self.land_drops - self.land_drops_used,
                "lands_in_hand": sum(1 for c in self.hand if c.is_land),
                "top_is_land": bool(self.library) and self.library[-1].is_land,
            })
        return super().resolve(card)


def check_sequencing():
    deck, cmd = build()
    cfg = dict(DEFAULT_CFG, turns=20, watch=frozenset())
    tally = collections.Counter()
    per_card = collections.defaultdict(collections.Counter)

    for s in range(N):
        g = Instrumented(deck, cmd, cfg, 5000 + s)
        g.opening_hand()
        for _ in range(cfg["turns"]):
            AZ.take_turn(g)
            if g.result is not None:
                break
        for o in g.obs:
            key = "cobra" if o["name"] == "Lotus Cobra" else (
                "top" if o["name"] in TOP_ENABLERS else "gy")
            tally[f"{key}_resolved"] += 1
            if o["drops_left"] <= 0:
                tally[f"{key}_after_drops_spent"] += 1
                if key == "top" and o["top_is_land"]:
                    tally["top_wasted_land_on_top"] += 1
                if key == "cobra" and o["lands_in_hand"] > 0:
                    tally["cobra_wasted_land_in_hand"] += 1
            per_card[o["name"]]["n"] += 1
            per_card[o["name"]]["late"] += (o["drops_left"] <= 0)

    print("\n2. FORESIGHT  (was the land drop already spent when the "
          "enabler resolved?)")
    for label, key in (("top-of-library enablers", "top"),
                       ("graveyard enablers", "gy")):
        n = tally[f"{key}_resolved"]
        late = tally[f"{key}_after_drops_spent"]
        pct = f"{late / n:.1%}" if n else "n/a"
        print(f"   {label:24} resolved {n:5}  after drops spent: {late:5} ({pct})")
    n = tally["top_resolved"]
    print(f"   ...and of those late ones, the top card WAS a land "
          f"{tally['top_wasted_land_on_top']} times "
          f"({tally['top_wasted_land_on_top'] / n:.1%} of all resolutions)"
          if n else "")
    print("   per card:")
    for name in TOP_ENABLERS + GY_ENABLERS:
        c = per_card[name]
        if c["n"]:
            print(f"     {name:26} {c['late']:5}/{c['n']:5} late "
                  f"({c['late'] / c['n']:.1%})")

    print("\n3. LOTUS COBRA  (was it on the battlefield in time to see a "
          "land drop?)")
    n = tally["cobra_resolved"]
    late = tally["cobra_after_drops_spent"]
    if n:
        print(f"   resolved {n}, of which {late} ({late / n:.1%}) after this "
              f"turn's land drops were already spent")
        print(f"   of those, {tally['cobra_wasted_land_in_hand']} still had a "
              f"land in hand it could have triggered off")
    print("\n   'late' = the card resolved when this turn's drops were already "
          "spent, so it\n   contributed nothing on the turn it arrived. Some "
          "residue is unavoidable:\n   a card drawn or afforded only after "
          "combat is genuinely late.")


def check_wasted_drops():
    """The summary number: land drops left unused at end of turn while a
    land was sitting somewhere the deck could legally have played it from.

    Also checks the commander's own case, which is the worst instance of the
    ordering problem: `land_drops_for_turn()` reads `commander_cast`, and
    land_step runs BEFORE main_phase, so on the turn Azusa resolves she
    grants nothing at all."""
    deck, cmd = build()
    cfg = dict(DEFAULT_CFG, turns=20, watch=frozenset())
    t = collections.Counter()

    for s in range(N):
        g = AZ.AzusaGame(deck, cmd, cfg, 5000 + s)
        g.opening_hand()
        cmd_turn = None
        for _ in range(cfg["turns"]):
            before_cast = g.commander_cast
            AZ.take_turn(g)
            if not before_cast and g.commander_cast and cmd_turn is None:
                cmd_turn = g.turn
                # drops actually taken on the turn she resolved
                t["azusa_turn_drops"] += g.land_drops
                t["azusa_landed"] += 1
            # end of turn: were drops left on the table with a land available?
            unused = g.land_drops - g.land_drops_used
            if unused > 0 and g.playable_lands():
                t["turns_with_wasted_drop"] += 1
                t["wasted_drops"] += min(unused, len(g.playable_lands()))
            t["turns"] += 1
            if g.result is not None:
                break

    print("\n4. WASTED LAND DROPS  (drop unused at end of turn, with a land "
          "legally playable)")
    print(f"   turns simulated                 {t['turns']}")
    print(f"   turns ending with a wasted drop {t['turns_with_wasted_drop']}"
          f"  ({t['turns_with_wasted_drop'] / t['turns']:.1%})")
    print(f"   total drops wasted              {t['wasted_drops']}"
          f"  ({t['wasted_drops'] / N:.2f} per game)")
    print("\n   AZUSA HERSELF, the worst case of the ordering problem:")
    print(f"   games where she resolved        {t['azusa_landed']}")
    print(f"   mean land drops on that turn    "
          f"{t['azusa_turn_drops'] / max(1, t['azusa_landed']):.2f}"
          "   <- should be 3 the turn she lands, is 1")


if __name__ == "__main__":
    check_zone_priority()
    check_sequencing()
    check_wasted_drops()
