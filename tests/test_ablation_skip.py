#!/usr/bin/env python3
"""Ablation plays only the games a blank can change (§0z145).

    python -m tests.test_ablation_skip
    python -m tests.test_ablation_skip --mutate   # 8 mutations, exact sets

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
  H  `engine.want_max` is `max(cards, key=want_key)`, the same OBJECT, on
     2,000 random pools of lands and spells with tied tiers, bands,
     priorities and mana values, lands short and not (§0z148)
  I  `want_max` reads no `priority` outside the best band: with lands short
     a land is taken and no spell's priority is read; with two castable
     spells and an uncastable one, the castable two are read and the
     uncastable one is not (§0z148)

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
  (§0z148, both written before their run)
  `want_max` keeps the LAST of the tied cards     -> H
  `want_max` reads every card's tail (the plain max over `want_key`)
                                                 -> I

  The first run of these broke two sets more than written. "No field reads"
  broke I as well, rightly: I sees `priority` through the same hook, and
  its set was not updated when I was added -- a transcript, not a
  prediction (§0z14). And the first stand-in for "the last of the tied"
  ranked every card by the full `want_key`, so it ALSO read every tail and
  broke I: it was not the defect it named. Replaced by one that reads tails
  inside the band only, and H written before its run.

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

    class Pilot:
        """The three hooks `want_key` asks, nothing else."""
        board, hand, cfg = [], [], {}

        def __init__(self, tiers=None, ranks=None, short=None):
            self.tiers, self.ranks, self.short = tiers or {}, ranks or {}, short

        def want_tier(self, c):
            return self.tiers.get(id(c), 0)

        def lands_wanted(self, n):
            return self.short

        def land_rank(self, c):
            return self.ranks.get(id(c), 0.0)

    def spell(name, mv, priority):
        return EN.Card(name=name, types=frozenset({"Sorcery"}),
                       cost={"gen": mv}, priority=priority)

    def land(name):
        return EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                       produces=frozenset("G"))

    rng = _random.Random(148)
    same = True
    for _ in range(2000):
        pool = [land(f"L{k}") if rng.random() < 0.3
                else spell(f"S{k}", rng.randrange(0, 5),
                           rng.choice((1.0, 2.0, 2.0, 3.0)))
                for k in range(rng.randrange(1, 11))]
        g = Pilot({id(c): 1 for c in pool if rng.random() < 0.15},
                  {id(c): rng.choice((0.0, 0.5, 1.0)) for c in pool},
                  rng.random() < 0.5)
        lands, mana = rng.randrange(0, 3), rng.randrange(0, 5)
        want = max(pool, key=lambda c: EN.want_key(g, c, lands, mana))
        same &= EN.want_max(g, pool, lands, mana) is want
    check("H want_max is max over want_key, the same card", same, True)

    prio = bit_of("priority")
    forest, bear, elk, big = (land("Forest"), spell("Bear", 2, 3.0),
                              spell("Elk", 2, 2.0), spell("Big", 7, 9.0))
    with AB.tracking_reads() as seen:
        took_land = EN.want_max(Pilot(short=True), [bear, forest, big],
                                0, 3) is forest
        short_reads = [seen.get(id(c), 0) & prio for c in (bear, big)]
        seen.clear()
        took_bear = EN.want_max(Pilot(short=False), [big, elk, forest, bear],
                                1, 3) is bear
        band_reads = [bool(seen.get(id(c), 0) & prio)
                      for c in (bear, elk, big)]
    check("I want_max reads priority only inside the best band",
          (took_land, short_reads, took_bear, band_reads),
          (True, [0, 0], True, [True, True, False]))
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

    def last_tied(g, cards, lands, mana):
        bands = [EN.want_band(g, c, lands, mana) for c in cards]
        tied = [c for c, b in zip(cards, bands) if b == max(bands)]
        best = max(EN.want_within(g, c) for c in tied)
        return [c for c in tied if EN.want_within(g, c) == best][-1]

    def plain_max(g, cards, lands, mana):
        return max(cards, key=lambda c: EN.want_key(g, c, lands, mana))

    def no_unsafe(card, blank):
        return real_mask(card, blank) & ~AB.UNSAFE

    muts = {
        "the hook records no field reads":
            ({"B", "C", "D", "F", "I"}, "_FIELD_BIT",
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
        "`want_max` keeps the last of the tied cards":
            ({"H"}, EN, "want_max", last_tied),
        "`want_max` reads every card's tail":
            ({"I"}, EN, "want_max", plain_max),
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
