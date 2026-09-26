# The comprehensive rules, and the parts of them this project needs

`MagicCompRules_20260807.docx` is the Magic: The Gathering Comprehensive
Rules, effective **7 August 2026**, added 2026-09-12. It is the authoritative
copy. `MagicCompRules_20260807.txt` beside it is a plain-text extraction of
the same file, added because **this project's workflow is to grep its docs**
and a `.docx` is a zip archive that `grep` cannot read.

Regenerate the `.txt` from the `.docx` rather than editing it:

```python
import zipfile, re, html
x = zipfile.ZipFile("docs/MagicCompRules_20260807.docx").read("word/document.xml").decode("utf8")
x = re.sub(r"</w:p>", "\n", x)          # paragraph boundaries first, or the
x = re.sub(r"<w:tab[^>]*/>", "\t", x)   # whole document collapses to one line
x = re.sub(r"<[^>]+>", "", x)
t = re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+\n", "\n", html.unescape(x)))
open("docs/MagicCompRules_20260807.txt", "w", encoding="utf8").write(t)
```

Rule numbers are stable within a version, so `grep -n "^305.7" ` is the way in.
Subrules skip `l` and `o`: `704.5k` is followed by `704.5m`, `704.5n`, `704.5p`.

**A rule number is evidence about the GAME, not about this engine.** Every
entry below says which of the two it settles. And the rules text does not
override `KNOWN_ISSUES.md` §4: a rule about opponents' permanents is still
unmeasurable here, because there are no opponent permanent objects to apply it
to.

---

## What the rules settle about currently-open issues

| rule | what it says | bears on |
|---|---|---|
| **104.3c** | a player required to draw more cards than are left in their library draws the remainder and **then loses the game** the next time a player would receive priority | queued **17**, CLOSED by §0z42 — `engine.drew_from_empty` records the loss at the draw, first result wins, so the 104.4a simultaneous case (deck and kill the last opponent in one resolution) scores a loss where a table scores a draw |
| **104.3j** | in Commander, a player dealt **21 or more combat damage by the same commander** over the game loses | **MODELLED for your commander since §0z65** — see below |
| **305.7** | a permanent that gains a basic land type **gains the mana ability for that type**; gaining types in addition to its own keeps its existing types and rules text | §0z / queued **15** — Ashaya |
| **302.6** | a creature's `{T}` ability can't be activated, and it can't attack, unless it has been under its controller's control since their most recent turn began | §0z / queued **15** — the constraint on the above |
| **603.6a** | enters-the-battlefield triggers fire when **an event puts a permanent onto the battlefield** | §0z / queued **15** — the trap in the above |
| **613.1d** | type-changing effects are **layer 4**; P/T-setting is layer 7 | §0z — Ashaya's two clauses interact |
| **702.12b** | an indestructible permanent isn't destroyed by lethal damage and **ignores the state-based action that checks for it** (704.5g) | §0z10, closed — confirms the fix |
| **704.5j** | the legend rule puts the extras into their **owners' graveyards** | §0z5, closed — confirms the fix |

### 104.3j — commander damage, MODELLED since §0z65

**Superseded by §0z65, kept for its prediction.** The section below was
written when the rule was absent. It is implemented now (`opponents.
commander_hit`, `Opponent.cmdr_damage`, `_check_eliminations`) and measured:
lorehold +0.0137 ±0.0036 at T20, shilgengar +0.0071, the rest inside their
bars. **Its "sharp case" was the wrong deck** -- Karlov kills 0.07 players a
game this way and wins no more; lorehold's 5/5 FLIER kills 0.49. Evasion, not
growth, is what reaches 21. And "the fix only ever adds kills" held: no deck
lost win rate.

`grep -rn "commander_damage\|21 or more"` over the package returns nothing, so
this is a win condition the project does not have. It is live rather than
academic: each engine puts the commander on the battlefield as an ordinary
`Permanent` and draws attackers from the whole board, so the commander already
attacks and already deals combat damage that `opponents.combat_damage` splits
across defenders. What is missing is a per-opponent cumulative counter keyed to
the commander.

The direction that matters is **yours killing an opponent**, not the reverse —
the pod's own commanders are folded into `resolve_clocks`, and giving them a
separate 21-damage track would be inventing detail the pod model does not have.
**Karlov of the Ghost Council is the sharp case**, because it grows on +1/+1
counters and `g.power_of` already reads them, so a Karlov that connects twice
can plausibly reach 21 while the defender is nowhere near dead on life. Against
that: the fix only ever *adds* kills, so every affected deck's win rate is a
floor, and the split-damage rule (§0v) spreads the swing rather than
concentrating it on one player, which is the assignment that would rack up
commander damage fastest. Worth measuring before believing either way.

### 305.7 + 302.6 + 603.6a — the Ashaya clause, and how to build it

Ashaya reads, verified against Scryfall 2026-09-12:

> Ashaya's power and toughness are each equal to the number of lands you
> control. Nontoken creatures you control are Forest lands in addition to their
> other types. **(They're still affected by summoning sickness.)**

The three rules together say what implementing the second sentence means:

* **305.7** — the creatures gain the Forest type *in addition to* their own, so
  they keep their abilities and gain Forest's intrinsic `{T}: Add {G}`. This is
  the half that combos with Quirion Ranger (`Return a Forest you control to its
  owner's hand: Untap target creature`) — under Ashaya every nontoken creature
  is a returnable Forest.
* **302.6** — and they cannot tap for it the turn they arrive. The card's own
  reminder text says so, and `Permanent.sick` already carries exactly this.
* **603.6a** — **half of this entry was wrong, and it was corrected on
  2026-09-13 when the clause was actually implemented (§0z18). Read the
  correction before the original.**

  ORIGINAL, and true only of one direction: "it must not fire landfall. A
  creature already on the battlefield gaining the land type is not an event
  putting a permanent onto the battlefield. In a landfall deck a naive
  implementation would trigger every payoff off every creature and the error
  would be enormous."

  THAT IS RIGHT ABOUT CREATURES ALREADY ON THE BATTLEFIELD WHEN ASHAYA
  RESOLVES — they gain the type with no ETB event and trigger nothing — AND
  WRONG ABOUT EVERY CREATURE THAT ENTERS AFTERWARDS. The official ruling
  (2020-09-25) settles it:

  > "You can't play creature cards as lands; you'll still have to cast them as
  > spells, and **they'll enter the battlefield as lands** (in addition to
  > their other types)."

  A nontoken creature cast under Ashaya **enters as a land and fires
  landfall.** In this 28-creature list that is the LARGER half of the card:
  6.65 triggers per resolution, and the whole +0.0140 win rate rests mostly on
  it. Written as a blanket prohibition, this entry would have shipped Ashaya
  understated — and its closing sentence reads as a warning against the
  correct behaviour.

  **The lesson, which is why the wrong version is kept above:** a rule number
  is evidence about the GAME, and the rulings are evidence about the CARD. This
  entry reasoned from 603.6a alone and never checked Ashaya's own rulings,
  which are one API call away and say the opposite.

**`edhmc/azusa.py`'s own note on the gap is now incomplete.** It lists the
blast radius as `available_mana, land_drops_for_turn, playable_lands,
land_entered, land_died` and Titania. It does not list **`forests()`**
(`azusa.py:1139`), which counts board permanents by name against the generated
`FOREST` set and therefore counts no animated creature. Three things read it,
and two are in the live §0z4 candidate batch:

| reads `forests()` | consequence if Ashaya's clause lands |
|---|---|
| Sapling Nursery's Affinity for Forests (`azusa.py:1132`) | costs `{1}` less per Forest; its **+0.0170 is a floor** |
| Nissa, Who Shakes the World's "whenever you tap a Forest for mana" (`azusa.py:653`) | every creature tapped is a Forest tapped; its **+0.0215 is a floor** |
| Castle Garenbrig's enters-untapped condition (`azusa.py:1098`) | already met nearly always in a 21-Forest list; immaterial |

That note predates the 2026-09-10 candidate batch, which is the §0z13 shape
pointed at a code comment instead of an issue: **the enumeration was complete
when it was written and two new consumers appeared underneath it.** Both
affected cards sit in the set of four the project is currently choosing between,
and both move the same way, so the ranking within that set may be undisturbed —
but they are floors, and the write-ups do not say so yet.
