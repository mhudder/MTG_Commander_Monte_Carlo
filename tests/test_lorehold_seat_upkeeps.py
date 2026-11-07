#!/usr/bin/env python3
"""§0z179: lorehold's opponent-upkeep windows open AT each opponent's upkeep.

    python -m tests.test_lorehold_seat_upkeeps
    python -m tests.test_lorehold_seat_upkeeps --mutate   # 2 mutations, exact sets

Lorehold, the Historian: "At the beginning of each opponent's upkeep, you
may discard a card. If you do, draw a card." -- and the first card drawn on a
turn is a miracle. The three windows a round ran AFTER the pod's whole round,
so a wrath miracled on an opponent's upkeep could not stop that opponent's
kill, and an upkeep went missing whenever Lorehold or the opponent did not
survive the round. Under the seat order (§0z179) they run inside it, through
`LoreholdGame.pod_upkeep`, before that opponent's pieces, kill and removal;
with Lorehold not out, a draw land's draw does (`draw_land_window`).

Each case drives `lorehold.take_turn` at pod turn 5 with `your_turn` stubbed
out (the round and what follows it are the subject), and records each window
with the seat whose turn it opened in (`g.pod_seat`, None outside the round).

CASES
  A  each seat's window opens before that seat's pieces: 0, 1, 2 in order
  B  exactly one window per seat, all inside the round, none after it
  C  NEIGHBOUR: `lorehold_seat_upkeeps=False` opens the three after the
     round, as it was
  D  Lorehold not out, two draw lands ready: their windows open at seats 0
     and 1, inside the round, and both lands are used
  E  NEIGHBOUR: `pod_seat_turns=False` (the old round) opens them after it

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  lorehold_seat_upkeeps=False everywhere   -> A, B, D
  LoreholdGame.pod_upkeep is a no-op       -> A, B, D

UNMUTATED (§0z15): C and E are the neighbours. The two mutations break the
same cases for different reasons -- the first moves the windows after the
round, the second loses them (take_turn no longer runs them after it either)
-- and B's count is what tells them apart in the output.
"""
import sys

import edhmc.lorehold as L
import edhmc.opponents as OPP
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}

DECK, CMD = build_pending("lorehold")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(commander=True, **cfg):
    g = L.LoreholdGame(list(DECK), CMD,
                       dict(DEFAULT_CFG, watch=frozenset(),
                            **{**EXTRA_CFG, **cfg}), 3)
    g.opening_hand()
    g.turn = 5
    g.commander_cast = commander
    for o in g.opponents:
        o.kill_turn, o.life = 99, float(10 ** 9)
    return g


def play(g):
    """`take_turn` with `your_turn` stubbed; returns the log of windows (as
    "window <seat>" / "land <seat>") and of each seat's pieces step."""
    log = []
    real = (L.your_turn, L.rummage_window, L.draw_land_window,
            OPP.respond_to_pieces)

    def rw(gg, cross_turn):
        log.append(f"window {getattr(gg, 'pod_seat', None)}")
        return real[1](gg, cross_turn)

    def dl(gg, ready):
        opened = real[2](gg, ready)
        if opened:
            log.append(f"land {getattr(gg, 'pod_seat', None)}")
        return opened

    def pieces(gg, seat=None):
        log.append(f"pieces {seat}")
        return real[3](gg, seat=seat)

    L.your_turn = lambda gg, extra=False: 0
    L.rummage_window, L.draw_land_window = rw, dl
    OPP.respond_to_pieces = pieces
    try:
        L.take_turn(g)
    finally:
        L.your_turn, L.rummage_window, L.draw_land_window, \
            OPP.respond_to_pieces = real
    return log


def run_cases():
    PASS.clear()
    FAIL.clear()

    log = play(game())
    order = [x for x in log if x.split()[0] in ("window", "pieces")]
    check("A each seat's window before that seat's pieces",
          order, ["window 0", "pieces 0", "window 1", "pieces 1",
                  "window 2", "pieces 2"])

    log = play(game())
    wins = [x for x in log if x.startswith("window")]
    check("B one window per seat, all inside the round",
          wins, ["window 0", "window 1", "window 2"])

    log = play(game(lorehold_seat_upkeeps=False))
    check("C lorehold_seat_upkeeps=False: three windows, after the round",
          [x for x in log if x.startswith("window")], ["window None"] * 3)

    g = game(commander=False)
    lands = [Permanent(card=Card(name=n, types=frozenset({"Land"}),
                                 is_land=True, produces=frozenset({"C"})),
                       sick=False)
             for n in ("Mikokoro, Center of the Sea", "Geier Reach Sanitarium")]
    g.board.extend(lands)
    g.draw_lands_ready = list(lands)
    g.float_mana = 6
    log = play(g)
    check("D draw lands open their windows at seats 0 and 1, both used",
          ([x for x in log if x.startswith("land")], g.draw_lands_ready),
          (["land 0", "land 1"], []))

    log = play(game(pod_seat_turns=False))
    check("E pod_seat_turns=False: the windows open after the round",
          [x for x in log if x.startswith("window")], ["window None"] * 3)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z179: lorehold's windows at each opponent's upkeep\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "lorehold_seat_upkeeps=False everywhere":
            ({"A", "B", "D"}, None, {"lorehold_seat_upkeeps": False}),
        "LoreholdGame.pod_upkeep is a no-op":
            ({"A", "B", "D"}, (L.LoreholdGame, "pod_upkeep",
                               lambda self, i: None), {}),
    }
    bad = 0
    for label, (want, patch, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        if patch:
            owner, name, fn = patch
            real = getattr(owner, name)
            setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            if patch:
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
