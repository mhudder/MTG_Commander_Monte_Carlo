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
# KARLOV IS DELIBERATELY NOT REGENERATED. karlov.py imports only Card,
# Permanent, can_pay, available_mana, spend and play_land from engine.py;
# is_creature_now() is reached only inside the `if g.has("Enduring Vitality")`
# branch, which no Karlov list can enter; and no Karlov card is in
# STACK_ONLY_CREATURES. Its table is untouched.
#
# THE CACHE IS DELETED FIRST, and that is the whole point. ablation.py keys its
# cache on deck, horizons and N -- NOT on the version of the code that produced
# it -- so a full cache leaves `todo` empty and the run silently REPRINTS THE
# OLD NUMBERS. Pass --resume to keep a partial cache from an interrupted run.
#
#     ./regen_tables.sh            # delete caches, regenerate both
#     ./regen_tables.sh --resume   # continue an interrupted run

set -e
RESUME=""
[ "$1" = "--resume" ] && RESUME=1

for deck in lorehold rendmaw; do
    cache="ablation_cache_${deck}_10-20_n6000.json"
    [ -z "$RESUME" ] && rm -f "$cache"
    : > "ablation_${deck}.log"
    for _ in $(seq 1 400); do
        ABLATE_BUDGET=1800 python ablation.py "$deck" 6000 10,20 \
            > "ablation_${deck}.txt.new" 2>> "ablation_${deck}.log"
        # ablation.py returns early, printing nothing, while cards remain.
        if grep -q "MODEL-EVALUATED" "ablation_${deck}.txt.new"; then
            mv "ablation_${deck}.txt.new" "ablation_${deck}.txt"
            echo "DONE $deck"
            break
        fi
    done
    rm -f "ablation_${deck}.txt.new"
done
echo "ALL DONE"
