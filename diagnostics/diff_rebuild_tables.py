#!/usr/bin/env python3
"""Diff each deck's ablation table at OLD_REF against the working tree, by T20
win rate: the baseline, the noise floor, every row that moved beyond the wider
of its two bars (the twelve largest printed), and any sign flip between rows
significant in both tables (§0z195). Written for item 53's rebuild (§0z279).

    python -m diagnostics.diff_rebuild_tables 6c9a661 rendmaw lorehold karlov tivit shilgengar azusa

The OLD table is read with `git show OLD_REF:results/ablation_<deck>.txt`.
"""
import re
import subprocess
import sys

ROW = re.compile(r"^(\S.*?)\s{2,}([+-]\d+\.\d+)\+-(\d+\.\d+)\s+([+-]\d+\.\d+)\+-(\d+\.\d+)"
                 r"\s+([+-]\d+\.\d+)\+-(\d+\.\d+)\s+(\S+)\s*$")
BASE = re.compile(r"wins ([\d.]+) at T10, ([\d.]+) at T20")
FLOOR = re.compile(r"is \+-(\d+\.\d+)")


def parse(text):
    rows, base, floor, cat = {}, None, None, None
    for line in text.splitlines():
        if (m := BASE.search(line)) and base is None:
            base = (float(m[1]), float(m[2]))
        if line.startswith("NOISE FLOOR") and (m := FLOOR.search(line)):
            floor = float(m[1])
        if line.strip() and line.strip().split()[0] in ("MODEL-EVALUATED", "PARTLY", "MODEL-BLIND"):
            cat = line.strip().split()[0]
        m = ROW.match(line)
        if m:
            rows[m[1].strip()] = dict(win=float(m[6]), bar=float(m[7]), sig=m[8], cat=cat)
    return rows, base, floor


def main(old, decks):
    for deck in decks:
        path = f"results/ablation_{deck}.txt"
        o, ob, of = parse(subprocess.check_output(["git", "show", f"{old}:{path}"], text=True))
        n, nb, nf = parse(open(path).read())
        print(f"== {deck}: baseline T20 {ob[1]:.4f} -> {nb[1]:.4f} (T10 {ob[0]:.4f} -> {nb[0]:.4f}); "
              f"floor +-{of:.4f} -> +-{nf:.4f}; rows {len(o)} -> {len(n)}")
        moved, flips = [], []
        for card in sorted(set(o) & set(n)):
            a, b = o[card], n[card]
            d = b["win"] - a["win"]
            if abs(d) > max(a["bar"], b["bar"]):
                moved.append((d, card, a, b))
            if abs(a["win"]) > a["bar"] and abs(b["win"]) > b["bar"] and (a["win"] > 0) != (b["win"] > 0):
                flips.append(card)
        up = sum(1 for m in moved if m[0] > 0)
        print(f"   moved beyond the wider bar: {len(moved)} of {len(set(o) & set(n))} ({up} up)")
        for d, card, a, b in sorted(moved, key=lambda m: -abs(m[0]))[:12]:
            print(f"     {card:38s} {a['win']:+.4f}+-{a['bar']:.4f} -> {b['win']:+.4f}+-{b['bar']:.4f}"
                  f"  ({d:+.4f})  {a['sig']}->{b['sig']}")
        print(f"   sign flips among rows significant in both: {flips or 'none'}")
        only = (set(o) ^ set(n))
        if only:
            print(f"   rows in one table only: {sorted(only)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
