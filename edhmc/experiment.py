"""
edhmc.experiment — paired A/B testing of single-card swaps.

The whole difficulty of this problem is signal-to-noise. One card is 1% of a
Commander deck, and game-to-game variance is enormous. Two techniques do the
heavy lifting:

1. COMMON RANDOM NUMBERS. Deck A and deck B are built as the *same list* with
   one slot differing, then shuffled with the *same* RNG seed. The 98 shared
   cards therefore land in identical library positions in both games, and the
   swapped card occupies the same slot. Almost all shuffle variance cancels in
   the difference. This typically cuts the standard error by 5-15x versus
   independent sampling — worth roughly 25-200x the number of trials.

2. PAIRED INFERENCE. We analyse D_i = metric(B_i) - metric(A_i), never the two
   means separately, and report a bootstrap CI on mean(D).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import numpy as np

from edhmc.engine import simulate

DEFAULT_CFG = {
    "turns": 10,
    "pod_life": 120,            # three opponents at 40
    "opponents": True,          # False -> old pure-goldfish mode
    "pod_brackets": (2, 3, 4),  # mixed pod
    "derived_blocking": True,   # False -> fall back to flat block_rate
    "block_rate": 0.30,         # only used when derived_blocking is False
    "block_share": 0.60,
    "first_wipe_turn": 5,

    # --- pod model v3, made the default 2026-09-04 ------------------------
    # Combat now kills. Before this, 100% of losses in all three decks were an
    # opponent's clock and your life total was inert, which made lifegain,
    # lifelink and any life cost unevaluable. See CANDIDATES_2026-09-04.md.
    # `POD_V1` below restores the previous pod exactly.
    "combat_targeting": "open",   # creatures hit whoever cannot block
    "incidental_rate": 1.0,       # was 0.45
    "clock_shift": 2,             # the deus ex machina arrives later
    "archetypes": True,           # aggro / midrange / control / combo pods

    "hold_up_rate": 0.60,       # P(you held up Heroic Intervention)
    "counter_threshold": 4.0,
    "set_top_gate": 4.0,       # min mana saved before paying to set the top
    "starting_life": 40,
    "clock_rearm": 4,          # turns before a fired opponent clock re-arms

    "opp_instant_rate": 0.8,
    "on_the_draw": True,
}

# ---------------------------------------------------------------------------
# Pod v2 — combat that actually kills (2026-09-04)
# ---------------------------------------------------------------------------
# Opt-in: dict(DEFAULT_CFG, **POD_V2). DEFAULT_CFG is untouched, so every
# number in the project reproduces exactly until a run asks for this.
#
#   combat_targeting="open"  creatures swing at the player who cannot block,
#                            not at the scariest board (see opponents.combat_share)
#   incidental_rate=1.0      up from 0.45
#   clock_shift=2            the deus ex machina arrives two turns later, paying
#                            back the lethality that combat now supplies
#
# Chosen to PRESERVE the existing calibration, not to hit a life-share target.
# Fitted over a 25-point grid by `fit_pod.py`; that script's mechanical best is
# (1.2, 4), which reaches a 0.65 life-share but costs Rendmaw and Lorehold
# ~25% of their win rate. The 0.65 target was invented — no published data on
# EDH elimination causes was found — so it is not worth re-baselining the whole
# project against. Game length IS anchored: the Command Zone's 100+ game sample
# puts the average game at turn 10.29 with 70% between 8 and 12.
#
#   metric              baseline (v1)          POD_V2
#   win r/l/k           0.295/0.220/0.428      0.290/0.188/0.454
#   turns r/l/k         12.1/13.5/11.7         12.9/13.3/12.6
#   life-share of losses  0.00/0.00/0.00       0.31/0.51/0.21
#
# Note the life-share now VARIES BY DECK, which is the whole point: Lorehold
# runs 11 creatures and gets attacked, Karlov is creature-dense and gains life
# and does not. The old model could not express that difference at all.
POD_V2 = {
    "combat_targeting": "open",
    "incidental_rate": 1.0,
    "clock_shift": 2,
}

# POD_V3 = POD_V2 plus per-opponent archetypes. The archetype multipliers are
# normalised to a weighted mean of 1, so this adds VARIANCE between pods, not
# average difficulty — see opponents.ARCHETYPES.
POD_V3 = dict(POD_V2, archetypes=True)

# The pod as it stood before 2026-09-04, kept so any earlier number in the
# project can be reproduced exactly.
POD_V1 = {
    "combat_targeting": "threat",
    "incidental_rate": 0.45,
    "clock_shift": 0,
    "archetypes": False,
}

METRICS = ("won", "damage", "cards_drawn", "rendmaw_triggers", "tokens_made",
           "opponents_killed", "turns_played", "final_board_power",
           "removal_eaten", "wipes_suffered", "countered")


@dataclass
class ABResult:
    metric: str
    mean_a: float
    mean_b: float
    mean_diff: float
    ci_low: float
    ci_high: float
    p_value: float
    n: int

    @property
    def significant(self) -> bool:
        return self.ci_low > 0 or self.ci_high < 0

    def line(self, name_a, name_b) -> str:
        star = "  *" if self.significant else "   "
        pct = (self.mean_diff / self.mean_a * 100) if self.mean_a else 0.0
        return (f"{self.metric:<20} {self.mean_a:>9.2f} {self.mean_b:>9.2f} "
                f"{self.mean_diff:>+9.2f} {pct:>+7.1f}%  "
                f"[{self.ci_low:>+7.2f}, {self.ci_high:>+7.2f}] "
                f"p={self.p_value:<7.4g}{star}")


def _swap(deck, out_card_name, in_card):
    return _swap_many(deck, [out_card_name], [in_card])


def _swap_many(deck, out_names, in_cards):
    """Replace n cards with n others, preserving list positions.

    Position matters: keeping the swapped slots in place is what lets common
    random numbers cancel the shuffle variance of the other 97 cards.
    """
    assert len(out_names) == len(in_cards), "swap must be n-for-n"
    new = list(deck)
    for out_name, in_card in zip(out_names, in_cards):
        for i, c in enumerate(new):
            if c.name == out_name:
                new[i] = in_card
                break
        else:
            raise KeyError(f"{out_name} not in deck")
    return new


def run_ab(deck, commander, out_card, in_card, n=20000, cfg=None,
           base_seed=1234, turns=None, sim=None):
    """Simulate n paired games. Deck A keeps `out_card`; deck B plays `in_card`.

    `out_card` / `in_card` may each be a single value or a matched list, for
    multi-card swaps. `sim` selects the engine (defaults to the Rendmaw one).
    """
    sim = sim or simulate
    cfg = dict(DEFAULT_CFG, **(cfg or {}))
    if turns:
        cfg["turns"] = turns
    outs = [out_card] if isinstance(out_card, str) else list(out_card)
    ins = [in_card] if not isinstance(in_card, (list, tuple)) else list(in_card)
    cfg["watch"] = frozenset(outs) | {c.name for c in ins}
    deck_a = list(deck)
    deck_b = _swap_many(deck, outs, ins)

    rows_a, rows_b = [], []
    for i in range(n):
        seed = base_seed + i                      # <- common random numbers
        rows_a.append(sim(deck_a, commander, cfg, seed))
        rows_b.append(sim(deck_b, commander, cfg, seed))
    return rows_a, rows_b, cfg


def analyse(rows_a, rows_b, metrics=METRICS, boots=4000, rng_seed=7):
    rng = np.random.default_rng(rng_seed)
    out = []
    n = len(rows_a)
    for m in metrics:
        a = np.array([r[m] for r in rows_a], dtype=float)
        b = np.array([r[m] for r in rows_b], dtype=float)
        d = b - a
        idx = rng.integers(0, n, size=(boots, n))
        boot_means = d[idx].mean(axis=1)
        lo, hi = np.percentile(boot_means, [2.5, 97.5])
        se = d.std(ddof=1) / np.sqrt(n)
        t = d.mean() / se if se > 0 else 0.0
        from scipy import stats as st
        p = 2 * st.t.sf(abs(t), df=n - 1)
        out.append(ABResult(m, a.mean(), b.mean(), d.mean(), lo, hi, p, n))
    return out


def lethal_curve(rows, cfg):
    """P(cumulative damage >= pod life) by turn.

    Since the opponent clock landed, games end at different turns, so
    `damage_by_turn` is ragged. Pad to the longest run before stacking.
    """
    turns = max((len(r["damage_by_turn"]) for r in rows), default=0)
    if turns == 0:
        return []
    padded = np.array([r["damage_by_turn"] + [0.0] * (turns - len(r["damage_by_turn"]))
                       for r in rows], dtype=float)
    cum = np.cumsum(padded, axis=1)
    return [(t + 1, float((cum[:, t] >= cfg["pod_life"]).mean())) for t in range(turns)]


def report(rows_a, rows_b, name_a, name_b, cfg, results):
    w = 100
    print("=" * w)
    print(f"A = {name_a}   vs   B = {name_b}")
    print(f"n = {len(rows_a):,} paired games (common random numbers) | "
          f"{cfg['turns']} turns | block_rate={cfg['block_rate']}")
    print("=" * w)
    print(f"{'metric':<20} {'A':>9} {'B':>9} {'B-A':>9} {'rel':>8}  "
          f"{'95% CI of diff':>19} {'':<10}")
    print("-" * w)
    for r in results:
        print(r.line(name_a, name_b))
    print("-" * w)
    print("* = 95% CI excludes zero")


def analyse_conditional(rows_a, rows_b, metrics=METRICS, **kw):
    """Restrict to the paired games where at least one side drew the test card.

    A single card is drawn in only ~17% of ten-turn games. The unconditional
    mean is the number that matters for deckbuilding EV, but it hides how big
    the effect is *when the card shows up*. Both are worth reading.
    """
    keep = [i for i in range(len(rows_a))
            if rows_a[i]["cast_test_card"] or rows_b[i]["cast_test_card"]]
    return keep, analyse([rows_a[i] for i in keep], [rows_b[i] for i in keep],
                         metrics=metrics, **kw)
