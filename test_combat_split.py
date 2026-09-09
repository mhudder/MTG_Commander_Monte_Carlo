#!/usr/bin/env python3
"""Pins `opponents.combat_damage`'s assignment rule — the one that splits an
attack across the pod and assigns removal insurance.

    python test_combat_split.py            # all cases MUST pass
    python test_combat_split.py --mutate    # insurance off; exactly the
                                            # DISCRIMINATING cases MUST fail

THE MUTATION CHECK IS THE POINT. A check that cannot fail reads like assurance
and is worse than none -- the same reason `diag_azusa_animation.py` carries one.

Each case DECLARES whether it distinguishes "assign lethal with insurance" from
"assign exactly lethal", and the mutated run asserts that exactly the declared
ones break. Declaring it per case rather than counting failures is deliberate:
the first version of this file asserted "2 of 6 fail" from a guess, and the
guess was wrong -- 123 bodies is enough under EITHER rule, so that case is a
boundary check and not a discriminator. Anyone adding a case now has to decide
which kind it is, and the check catches them if they decide wrong.
"""
import sys

from edhmc.engine import Card, Permanent
from edhmc import opponents as OPP

MUTATE = "--mutate" in sys.argv


class FakeGame:
    """The smallest object `combat_damage` actually reads."""

    def __init__(self, lives, blockers=0.0, split=True):
        self.cfg = {"combat_split": split}
        self.opponents = [
            OPP.Opponent(bracket=3, has_blue=False, creatures=blockers,
                         life=float(l))
            for l in lives
        ]
        self.m = {}
        self.result = None
        self.your_life = 40.0

    def has(self, name):
        return False

    def power_of(self, perm):
        return perm.card.power


def bodies(n, power):
    c = Card(name=f"{power}/{power} token", types=frozenset({"Creature"}),
             power=power, toughness=power)
    return [Permanent(card=c, sick=False, tapped=False) for _ in range(n)]


def alive(g):
    return len(OPP.living(g))


# The mutation: drop the insurance term, i.e. assign EXACTLY lethal. `k` loses
# the +1 that pays for losing the largest attacker that got through.
if MUTATE:
    import bisect

    _real = OPP.combat_damage

    def _exact(g, attackers):
        if not attackers or not g.cfg.get("combat_split", False):
            return _real(g, attackers)
        living = sorted(OPP.living(g), key=lambda o: o.life)
        if not living:
            return 0.0
        pool = sorted(attackers, key=g.power_of)
        pre = [0.0]
        for p in pool:
            pre.append(pre[-1] + g.power_of(p))
        n = len(pool)
        plan, i = [], 0
        for opp in living:
            if i >= n:
                break
            b, _ = OPP._blocker_counts(g, opp)
            j = bisect.bisect_left(pre, pre[i] + opp.life, i, n + 1)
            k = (j - i) + b          # <-- the +1 is gone
            if j > n or i + k > n:
                plan.append([opp, i, n])
                i = n
                break
            plan.append([opp, i, i + k])
            i += k
        if i < n and plan:
            plan[-1][2] = n
        total = 0.0
        for opp, lo, hi in plan:
            dealt = OPP.damage_through(g, pool[lo:hi], defender=opp)
            opp.life -= dealt
            total += dealt
        OPP._check_eliminations(g)
        return total

    OPP.combat_damage = _exact


CASES = []


def case(name, discriminates=False):
    """`discriminates` = this case's outcome depends on the insurance term, so
    it MUST fail under --mutate."""
    def deco(fn):
        CASES.append((name, fn, discriminates))
        return fn
    return deco


@case("a wide board of 1/1s kills the WHOLE pod in one attack")
def _c1():
    g = FakeGame([40, 40, 40])
    OPP.combat_damage(g, bodies(5000, 1))
    return alive(g) == 0 and g.result == "win", f"{alive(g)} alive, {g.result}"


@case("ONE huge creature still kills only one player (it attacks one player)")
def _c2():
    g = FakeGame([40, 40, 40])
    OPP.combat_damage(g, bodies(1, 5000))
    return alive(g) == 2, f"{alive(g)} alive"


@case("the OLD path is unchanged: everything at one player")
def _c3():
    g = FakeGame([40, 40, 40], split=False)
    OPP.combat_damage(g, bodies(5000, 1))
    return alive(g) == 2, f"{alive(g)} alive"


@case("insurance COSTS a kill: 120 1/1s kill 2, not the perfect-split 3",
      discriminates=True)
def _c4():
    # 40 damage each would kill all three with 120 bodies exactly. Insurance
    # needs 41 apiece, so the third player survives at 2 life.
    g = FakeGame([40, 40, 40])
    OPP.combat_damage(g, bodies(120, 1))
    return alive(g) == 1, f"{alive(g)} alive, lives {[o.life for o in g.opponents]}"


@case("and at 121 it still costs one", discriminates=True)
def _c5():
    g = FakeGame([40, 40, 40])
    OPP.combat_damage(g, bodies(121, 1))
    return alive(g) == 1, f"{alive(g)} alive, lives {[o.life for o in g.opponents]}"


@case("122 is the real boundary, and it is the LEFTOVER DUMP that gets there")
def _c5b():
    # NOT a discriminator: both rules kill all three at 122. Worth pinning
    # because the boundary is not the 123 that "41 apiece" suggests -- the
    # third player is not SECURED (41 would need 123) but the 40 leftover
    # bodies are dumped on them and 40 is exactly lethal. So the insurance
    # costs one kill over a 2-body window (120, 121), not an unbounded one.
    g = FakeGame([40, 40, 40])
    OPP.combat_damage(g, bodies(122, 1))
    return alive(g) == 0, f"{alive(g)} alive, lives {[o.life for o in g.opponents]}"


@case("blockers are paid for per defender, on top of the insurance")
def _c6():
    # 5 creatures each * 0.60 block_share = 3 blockers apiece. Killing one
    # player needs 41 connecting + 3 eaten = 44 bodies; 44 kills exactly one.
    g = FakeGame([40, 40, 40], blockers=5.0)
    OPP.combat_damage(g, bodies(44, 1))
    return alive(g) == 2, f"{alive(g)} alive, lives {[o.life for o in g.opponents]}"


def main():
    print(f"combat_damage assignment rule{'  [MUTATED: insurance off]' if MUTATE else ''}")
    print()
    npass, nfail, failed = 0, 0, set()
    for name, fn, disc in CASES:
        try:
            ok, detail = fn()
        except Exception as e:                      # noqa: BLE001
            ok, detail = False, f"{type(e).__name__}: {e}"
        tag = "  [discriminates]" if disc else ""
        print(f"  {'PASS' if ok else 'FAIL'}  {name}{tag}")
        if not ok:
            print(f"          -> {detail}")
            failed.add(name)
        npass, nfail = npass + bool(ok), nfail + (not ok)
    print()
    print(f"  {npass} passed, {nfail} failed")
    if not MUTATE:
        return 0 if nfail == 0 else 1

    want = {name for name, _, disc in CASES if disc}
    missing = want - failed          # should have broken and did not
    extra = failed - want            # broke for some other reason
    print(f"  MUTATION CHECK: the {len(want)} discriminating case(s) must fail "
          f"and nothing else.")
    for n in sorted(missing):
        print(f"    NOT CAUGHT  {n}  <- insurance term is not load-bearing here")
    for n in sorted(extra):
        print(f"    UNEXPECTED  {n}  <- broke for a reason other than insurance")
    ok = not missing and not extra
    print(f"  -> {'OK' if ok else 'THE CHECK ITSELF IS WRONG'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
