#!/bin/sh
# Regenerate the ablation tables invalidated on 2026-09-05.
#
#   lorehold  the DECK changed: -Penance +Caldera Pyremaw replaced +Galvanoth
#             in pending.py, and build_pending() applies staged changes.
#   rendmaw   the ENGINE changed: Grist is no longer a battlefield creature,
#             so its own row, and any row reading board creature-ness (March
#             of the World Ooze, The Great Henge, Overwhelming Stampede,
#             Enduring Vitality), moved.
#
#   karlov    the ENGINE changed: Suture Priest, Daxos and Elas il-Kor no
#             longer trigger off their own arrival. This was added to the list
#             on 2026-09-05 AFTER an earlier version of this script argued
#             Karlov was unaffected — which was true of the Grist change and
#             false of this one. Measured at -0.023 win rate, so not small.
#
# THE CACHE IS DELETED FIRST, and that is the whole point. ablation.py keys its
# cache on deck, horizons and N -- NOT on the version of the code that produced
# it -- so a full cache leaves `todo` empty and the run silently REPRINTS THE
# OLD NUMBERS. Pass --resume to keep a partial cache from an interrupted run.
#
#     ./tools/regen_tables.sh            # delete caches, regenerate both
#     ./tools/regen_tables.sh --resume   # continue an interrupted run
#
# BOTH FROM THE REPO ROOT. See the note above the loop.
#
# Since 2026-09-06 a deck takes minutes rather than ninety, so the 1800s budget
# below never fires and the retry loop runs exactly once. Both are kept because
# they cost nothing and still cover an interrupted run. Set ABLATE_PROCS to
# limit the worker count (default: every core).
#
# N IS 15000 AND TIVIT IS IN THE LOOP, both since 2026-09-06. The whole run is
# about 24 minutes. Do not lower N here without lowering it in the tables too:
# this script OVERWRITES ablation_<deck>.txt, so a stale N in this file silently
# replaces the committed tables with less precise ones. N is now printed in each
# table's own header, which is the check on that.
#
# Tivit was left out while it was the odd deck at N=2000 and its table was not
# comparable to the others. At a common N it is, so it regenerates with them.
#
# 2026-09-06, SECOND REGENERATION: the ablation BLANK changed. It was built at
# priority 0.5 -- below the minimum priority of every deck -- so `main_phase`,
# which is greedy on priority, cast it only when nothing else was affordable.
# That is a dead card, not a replacement-level one, and the difference in tempo
# was charged to whichever card was under test. The blank is now cast at the
# deck's median nonland priority. See KNOWN_ISSUES.md 0j.
#
# THE CACHE FILENAME CHANGED WITH IT (`_medblank`), which is deliberate: the
# pre-change files carry no such suffix, so this run cannot pick one up and
# reprint numbers measured against the old blank. Keep the name below in step
# with ablation.py's CACHE or the `rm -f` silently deletes nothing.
#
# 2026-09-06, THIRD REGENERATION -- and only TWO of the four decks needed it.
# The Erebos correction (KNOWN_ISSUES.md 0l) changed engine.py and
# decks/rendmaw_v12.py; the extra-turn correction (0m) changed edhmc/tivit.py.
# engine.py is in EVERY deck's fingerprint, so all four fingerprints moved --
# but karlov.py and lorehold.py have their own Game classes and import only the
# mana and card primitives from engine.py, none of which changed.
#
# THAT WAS CHECKED, NOT ARGUED, because this script has been wrong about exactly
# this once before: an earlier version of this header argued Karlov was
# unaffected by the 2026-09-05 work, which was true of the Grist change and
# false of the "another creature" one. The check is a git worktree at the
# previous commit running all four baselines on the same seeds at both horizons
# and diffing every metric. karlov and lorehold came back BIT-IDENTICAL;
# rendmaw and tivit did not. Only the latter two were regenerated.
#
# So: running this script whole is always SAFE but can be wasteful. If you are
# confident only some decks moved, prove it with the worktree diff first and
# regenerate those -- and if you cannot be bothered to prove it, regenerate all
# four rather than guessing.

# 2026-09-07: shilgengar and azusa joined the loop with the decks themselves.
# Both are new and untuned, so their first tables are baselines rather than
# regenerations -- but they belong here for the same reason tivit does, which
# is that a table only means something next to the others at a COMMON N.
#
# The whole run is now about 35 minutes rather than 24.

set -e
RESUME=""
[ "$1" = "--resume" ] && RESUME=1
N=15000

# Run from the REPO ROOT (`./tools/regen_tables.sh`), not from tools/. Every
# path below is root-relative, and `python -m tools.ablation` needs the root on
# sys.path to import edhmc.
for deck in lorehold rendmaw karlov tivit shilgengar azusa; do
    cache="results/caches/ablation_cache_${deck}_10-20_n${N}_medblank.json"
    [ -z "$RESUME" ] && rm -f "$cache"
    : > "results/ablation_${deck}.log"
    for _ in $(seq 1 400); do
        ABLATE_BUDGET=1800 python -m tools.ablation "$deck" "$N" 10,20 \
            > "results/ablation_${deck}.txt.new" \
            2>> "results/ablation_${deck}.log"
        # ablation.py returns early, printing nothing, while cards remain.
        if grep -q "MODEL-EVALUATED" "results/ablation_${deck}.txt.new"; then
            mv "results/ablation_${deck}.txt.new" "results/ablation_${deck}.txt"
            echo "DONE $deck"
            break
        fi
    done
    rm -f "results/ablation_${deck}.txt.new"
done
echo "ALL DONE"
