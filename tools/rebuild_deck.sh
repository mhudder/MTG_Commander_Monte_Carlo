#!/usr/bin/env bash
# ONE deck's table, rebuilt in its own session -- one leg of a PARALLEL
# rebuild (§0z94, .claude/skills/parallel-rebuild/SKILL.md).
#
#   ./tools/rebuild_deck.sh <deck> <commit> <branch>
#
# Run from the repo root of a fresh clone. It
#   1. checks out <commit>, detached, and refuses a dirty tree -- every leg
#      measures the SAME code, which is what makes the six tables one rebuild;
#   2. rebuilds ONLY <deck> through regen_tables.sh, with PROVENANCE_SHARD=1 so
#      the run stamps its provenance into results/caches/provenance.<deck>.json
#      and never into the shared PROVENANCE.json;
#   3. refuses if anything other than that deck's own three files changed;
#   4. commits those three files and pushes them to <branch>, rebasing on
#      each attempt: the other legs push to the same branch, and no two legs
#      touch the same file, so the rebase cannot conflict.
#
# It does NOT regenerate docs, merge shards or run the gates. The coordinator
# does that once, after every leg has pushed -- six sessions regenerating
# STATUS.md would be six conflicting commits of a derived file.
set -euo pipefail

deck="${1:?usage: rebuild_deck.sh <deck> <commit> <branch>}"
commit="${2:?usage: rebuild_deck.sh <deck> <commit> <branch>}"
branch="${3:?usage: rebuild_deck.sh <deck> <commit> <branch>}"
N=$(sed -n 's/^N=//p' tools/regen_tables.sh)

git fetch origin "$branch"
git checkout --detach "$commit"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "refusing: the tree is not clean at $commit" >&2
    exit 1
fi

DECKS="$deck" PROVENANCE_SHARD=1 ./tools/regen_tables.sh

cache="results/caches/ablation_cache_${deck}_10-20_n${N}_medblank.json"
shard="results/caches/provenance.${deck}.json"
table="results/ablation_${deck}.txt"
for f in "$cache" "$shard" "$table"; do
    [ -f "$f" ] || { echo "refusing: $f was not produced" >&2; exit 1; }
done
unexpected=$(git status --porcelain | awk '{print $2}' \
             | grep -v -x -F -e "$cache" -e "$shard" -e "$table" || true)
if [ -n "$unexpected" ]; then
    echo "refusing: the rebuild changed files outside $deck's own:" >&2
    echo "$unexpected" >&2
    exit 1
fi

# The interpreter is part of what makes legs comparable: the harness is
# deterministic for one Python and numpy, and the coordinator checks that every
# leg ran the versions it runs.
versions=$(python -c 'import sys, numpy; print(f"python {sys.version.split()[0]}, numpy {numpy.__version__}")')

git add "$cache" "$shard" "$table"
git commit -q -m "Rebuild ${deck}'s table at ${commit} (parallel rebuild, §0z94)

N=${N}, horizons 10 and 20, from an empty cache. Provenance is in
${shard} until the coordinator merges it.

Interpreter: ${versions}"

for attempt in 1 2 3 4 5 6; do
    if git fetch origin "$branch" && git rebase "origin/$branch" \
            && git push origin "HEAD:$branch"; then
        echo "PUSHED $deck to $branch"
        exit 0
    fi
    git rebase --abort 2>/dev/null || true
    sleep $((2 ** attempt))
done
echo "could not push $deck after 6 attempts" >&2
exit 1
