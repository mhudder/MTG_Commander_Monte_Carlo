#!/usr/bin/env python3
"""Ablation plays only the games a blank can change (§0z145).

    python -m tests.test_ablation_skip
    python -m tests.test_ablation_skip --mutate   # 6 mutations, exact sets

The baseline records what each game read of each library card; a game that
read no field on which the card and its blank differ is the baseline's game,
and its row is copied instead of played. That is a speed change ONLY if every
skipped row is the row playing it would have produced -- so this checks
identity, not closeness.

CASES
  A  tracking is passive: the baseline played inside `tracking_reads` returns
     the rows it returns without it (rendmaw, lorehold, azusa, tivit; 30
     seeds), and `play` with a read list equals `columns_all`
  B  skipping equals playing: for the most- and the least-skipped card of
     rendmaw, lorehold, azusa and tivit, `skipping_columns` (no audit) equals
     `columns_all` of the blanked deck on every metric at T10 and T20, 60
     seeds -- and each skipped at least one game, so the case is not vacuous
  C  the hook: a field read sets its bit; a property (`mv`) sets its OWN bit
     and not the bit of the field it reads (`cost`, §0z146); `__dict__` and
     a write set UNSAFE; the hook is gone after the block, and after one
     that raised
  D  `differs_mask`: a creature's blank differs on `name` and `priority`, not
     on `cost`; every mask carries UNSAFE; and properties by VALUE (§0z146):
     an Instant's Sorcery blank differs on `types` but not on `is_creature`;
     an Artifact Creature's Creature blank differs on `types` and
     `multitype`, not on `is_creature`
  E  the audit catches a lie: reads claiming a card was never touched, with
     every skipped game audited, raise instead of returning
  F  `ablate` with the read masks returns what `ablate` without them returns
     (rendmaw, the most-read card, default audit)
  G  `engine.remove_card` is `list.remove`: over 300 shuffled lists holding
     value-EQUAL copies (two basic Forests, two equal nonlands), removing
     each card in turn leaves the same objects in the same order, and a card
     not in the list raises ValueError (§0z146)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the hook records no field reads                -> B, C, D, F
  (D because `differs_mask` reads the same bit table; C and D take their
  expected bits from `CARD_FIELDS`, which no mutation touches, so a zeroed
  table cannot agree with itself)
  `__dict__` counts as neutral                    -> C
  `differs_mask` leaves out UNSAFE                -> D
  `differs_mask` is 0: no game is played          -> B, D, F
  (§0z146, written before its run)
  properties are not tracked by value (no _PROP_BIT) -> C, D
  `remove_card` removes the first card with the same is_land and cost
                                                 -> G

UNMUTATED (§0z15): A is the neighbour -- tracking must change no game. E is
the guard the mutations would hide behind if B and F audited, which is why B
runs with `audit=0` and E alone tests the audit.
"""
import sys

import numpy as np

import edhmc.engine as EN
import tools.ablation as AB
from edhmc.experiment import repl_priority
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECKS = ("rendmaw", "lorehold", "azusa", "tivit")
LISTS = {d: build_pending(d) for d in DECKS}
N = 60


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def same_cols(a, b, run):
    return all(np.array_equal(a[t][m], b[t][m])
               for t in run.horizons for m in run.metrics)


def baseline_with_reads(run, cards, cmd, n):
    reads = []
    cols = AB.play(run, cards, cmd, range(n), reads)
    return cols, np.array(reads, dtype=np.int64)


def bit_of(name):
    """A field's bit from `CARD_FIELDS`, not from the table under test."""
    return 1 << AB.CARD_FIELDS.index(name)


def prop_bit_of(name):
    """A property's bit from `CARD_PROPS`, likewise."""
    return 1 << (len(AB.CARD_FIELDS) + AB.CARD_PROPS.index(name))


def run_cases():
    PASS.clear()
    FAIL.clear()

    passive, play_eq, results = True, True, {}
    for d in DECKS:
        cards, cmd = LISTS[d]
        run = AB.Run(d, N, (10, 20), skip=True, audit=0)
        plain = AB.columns_all(run, cards, cmd, 0, 30)
        tracked, _ = baseline_with_reads(run, cards, cmd, 30)
        passive &= same_cols(plain, tracked, run)
        base, reads = baseline_with_reads(run, cards, cmd, N)
        play_eq &= same_cols(base, AB.columns_all(run, cards, cmd, 0, N), run)
        results[d] = (run, base, reads)
    check("A tracking changes no game; play with reads is columns_all",
          (passive, play_eq), (True, True))

    identical, skipped_some = True, True
    for d in DECKS:
        cards, cmd = LISTS[d]
        run, base, reads = results[d]
        skips = {}
        for c in cards:
            if c.is_land:
                continue
            slot = next(i for i, x in enumerate(cards) if x.name == c.name)
            blank = AB.blanked(run, cards, c.name)[slot]
            skips[c.name] = int(((reads[:, slot]
                                  & AB.differs_mask(c, blank)) == 0).sum())
        live = {k: v for k, v in skips.items() if v > 0}
        picks = ({max(skips, key=skips.get), min(live, key=live.get)}
                 if live else set())
        skipped_some &= bool(picks)
        for name in picks:
            deck_b = AB.blanked(run, cards, name)
            try:
                got = AB.skipping_columns(run, cards, deck_b, cmd, name, base,
                                          reads)
                identical &= same_cols(got, AB.columns_all(
                    run, deck_b, cmd, 0, N), run)
            except RuntimeError:
                identical = False
    check("B skipping equals playing, and skips something",
          (identical, skipped_some), (True, True))

    probe = EN.Card(name="Probe", types=frozenset({"Creature"}),
                    cost={"G": 1}, power=2)
    with AB.tracking_reads() as seen:
        probe.power
        field_bit = seen.pop(id(probe), 0)
        probe.mv
        prop_bits = seen.pop(id(probe), 0)
        probe.__dict__
        dict_bits = seen.pop(id(probe), 0)
        probe.tapped = False
        write_bits = seen.pop(id(probe), 0)
    gone = "__getattribute__" not in vars(EN.Card)
    try:
        with AB.tracking_reads():
            raise KeyError("inside")
    except KeyError:
        pass
    gone_after_raise = ("__getattribute__" not in vars(EN.Card)
                        and "__setattr__" not in vars(EN.Card))
    check("C the hook: fields, properties, __dict__, writes, removal",
          (field_bit == bit_of("power"), prop_bits == prop_bit_of("mv"),
           bool(dict_bits & AB.UNSAFE), bool(write_bits & AB.UNSAFE),
           gone, gone_after_raise),
          (True, True, True, True, True, True))

    cards, _ = LISTS["rendmaw"]
    creature = next(c for c in cards if c.is_creature and not c.is_land)
    mask = AB.differs_mask(creature, AB.blank_like(creature,
                                                    repl_priority(cards)))
    instant = EN.Card(name="Probe Instant", types=frozenset({"Instant"}),
                      cost={"R": 1})
    artcre = EN.Card(name="Probe Golem",
                     types=frozenset({"Artifact", "Creature"}),
                     cost={"gen": 2}, power=1, toughness=1)
    mi = AB.differs_mask(instant, AB.blank_like(instant, 3.0))
    ma = AB.differs_mask(artcre, AB.blank_like(artcre, 3.0))
    check("D differs_mask: fields, UNSAFE always, properties by value",
          (bool(mask & bit_of("name")), bool(mask & bit_of("priority")),
           bool(mask & bit_of("cost")), bool(mask & AB.UNSAFE),
           bool(mi & bit_of("types")), bool(mi & prop_bit_of("is_creature")),
           bool(ma & bit_of("types")), bool(ma & prop_bit_of("multitype")),
           bool(ma & prop_bit_of("is_creature"))),
          (True, creature.priority != repl_priority(cards), False, True,
           True, False, True, True, False))

    run, base, reads = results["rendmaw"]
    slot = int(np.argmax((reads != 0).sum(axis=0)))
    name = cards[slot].name
    liar = AB.Run("rendmaw", N, (10, 20), skip=True, audit=1)
    try:
        AB.skipping_columns(liar, cards, AB.blanked(liar, cards, name),
                            LISTS["rendmaw"][1], name, base,
                            np.zeros_like(reads))
        raised = False
    except RuntimeError:
        raised = True
    check("E the audit catches reads that lie", raised, True)

    full = AB.Run("rendmaw", N, (10, 20), skip=True)
    cmd = LISTS["rendmaw"][1]
    try:
        with_reads = AB.ablate(full, cards, cmd, name, base, reads)
    except RuntimeError:
        with_reads = "raised"
    check("F ablate with reads equals ablate without",
          with_reads == AB.ablate(full, cards, cmd, name, base), True)
    import random as _random
    rng = _random.Random(146)

    def protos():
        f = dict(name="Forest", types=frozenset({"Land"}), is_land=True,
                 produces=frozenset("G"))
        b = dict(name="Bear", types=frozenset({"Creature"}), cost={"G": 2},
                 power=2, toughness=2)
        return [EN.Card(**f), EN.Card(**f), EN.Card(**b), EN.Card(**b),
                EN.Card(name="Elk", types=frozenset({"Creature"}),
                        cost={"G": 2}, power=3, toughness=3),
                EN.Card(name="Rite", types=frozenset({"Sorcery"}),
                        cost={"G": 2}),
                EN.Card(name="Plains", types=frozenset({"Land"}),
                        is_land=True, produces=frozenset("W"))]

    same = True
    for _ in range(300):
        cards = protos()
        rng.shuffle(cards)
        for target in list(cards):
            a, b = list(cards), list(cards)
            a.remove(target)
            EN.remove_card(b, target)
            same &= [id(c) for c in a] == [id(c) for c in b]
    try:
        EN.remove_card(protos()[:2], protos()[4])
        raised = False
    except ValueError:
        raised = True
    check("G remove_card is list.remove, duplicates included", (same, raised),
          (True, True))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Ablation skips the games a blank cannot change (§0z145)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_neutral = AB._NEUTRAL
    real_bits = AB._FIELD_BIT
    real_mask = AB.differs_mask

    def first_same_cost(cards, card):
        for i, c in enumerate(cards):
            if c is card or (c.is_land == card.is_land
                             and c.cost == card.cost):
                del cards[i]
                return
        raise ValueError("not in list")

    def no_unsafe(card, blank):
        return real_mask(card, blank) & ~AB.UNSAFE

    muts = {
        "the hook records no field reads":
            ({"B", "C", "D", "F"}, "_FIELD_BIT",
             {k: 0 for k in real_bits}),
        "`__dict__` counts as neutral":
            ({"C"}, "_NEUTRAL", real_neutral | {"__dict__"}),
        "`differs_mask` leaves out UNSAFE":
            ({"D"}, "differs_mask", no_unsafe),
        "`differs_mask` is 0: no game is played":
            ({"B", "D", "F"}, "differs_mask", lambda card, blank: 0),
        "properties are not tracked by value":
            ({"C", "D"}, "_PROP_BIT", {}),
        "`remove_card` removes the first card with the same is_land and cost":
            ({"G"}, EN, "remove_card", first_same_cost),
    }
    bad = 0
    for label, spec in muts.items():
        want, owner, name, value = (spec if len(spec) == 4
                                    else (spec[0], AB) + tuple(spec[1:]))
        print(f"-- {label}")
        orig = getattr(owner, name)
        setattr(owner, name, value)
        try:
            broke = run_cases()
        finally:
            setattr(owner, name, orig)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
