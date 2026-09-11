#!/usr/bin/env python3
"""Build Tivit_Seller_of_Secrets_Commander_Deck_v1.xlsx.

Same two-sheet format as the Karlov v2 / Lorehold v16 / Rendmaw v12 books:
a `Decklist` sheet (the system of record) and a `Dashboard` of formulas that
read it.

EVERY FACT IN COLUMNS D, E, F AND H COMES FROM SCRYFALL, not from memory --
mana value, card type, colour identity and price are fetched at build time.
That is the project's standing rule ("do not guess oracle text"), and it is why
the Karlov book needed 52 corrections when it was first audited.

Two things the other books got wrong that this one gets right from the start:

  * DASHBOARD FORMULA RANGES run to row 200, not to the last data row. The
    Karlov v2 book had 34 formulas hard-bounded to `Decklist!...87` against an
    88-row list, so every metric silently dropped the last card. openpyxl does
    not rewrite ranges on insert.
  * THE AUTOFILTER covers the real last row. Karlov v2's stops at A3:J87 on an
    88-row sheet, the same off-by-one.

    python build_tivit_xlsx.py
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

SRC = (r"C:\Users\matth\.claude\uploads"
       r"\41304e60-f0ea-4dc0-b907-5dae14490564\d6ddcfa7-Tivit_EDH.txt")
OUT = "spreadsheets/Tivit_Seller_of_Secrets_Commander_Deck_v1.xlsx"
UA = {"User-Agent": "EDHMC/1.0", "Accept": "application/json"}

ACCENT = "FF4B3F72"        # Esper purple, the analogue of Karlov's dark red
GREY = "FF555555"
FAINT = "FF777777"
FONT = "Segoe UI"
LAST = 200                 # formula ranges run here, NOT to the last data row

# --- the deck -------------------------------------------------------------
# (category, note). The note says what the card does IN THIS DECK; it is
# written from the oracle text fetched below, not from memory.
CARDS = {
 "Tivit, Seller of Secrets": ("Commander",
    "ETB and combat damage: every player votes evidence or bribery, and you "
    "vote TWICE. Clues and Treasures either way, so the vote is never bad."),

 # --- Voting & Council's Dilemma ---
 "Ballot Broker": ("Voting & Council's Dilemma",
    "An additional vote. Stacks with Tivit's own extra vote and with Brago's "
    "Representative to control most dilemmas outright."),
 "Brago's Representative": ("Voting & Council's Dilemma",
    "A second additional vote. Two of these plus Tivit is a majority in a "
    "four-player pod on every will-of-the-council card."),
 "Illusion of Choice": ("Voting & Council's Dilemma",
    "You choose how EVERY player votes this turn, and draw. Turns any "
    "symmetric dilemma into a one-sided one; the best single card here."),
 "Grudge Keeper": ("Voting & Council's Dilemma",
    "Each opponent who voted against you loses 2. With Illusion of Choice you "
    "pick their votes, so you can force the full 6."),
 "Coercive Portal": ("Voting & Council's Dilemma",
    "Upkeep vote: draw a card, or blow up every nonland permanent. You hold "
    "the extra votes, so it draws until you want the wrath."),
 "Custodi Squire": ("Voting & Council's Dilemma",
    "Flier whose ETB vote returns an artifact, creature or enchantment from "
    "your yard. Blink it to rebuy repeatedly."),
 "Lieutenants of the Guard": ("Voting & Council's Dilemma",
    "ETB dilemma: +1/+1 counters or 1/1 Soldiers. Tokens feed Mirkwood Bats "
    "and Kambal either way."),
 "Messenger Jays": ("Voting & Council's Dilemma",
    "ETB dilemma: counters or loot. A blink target that refills the hand."),
 "Master of Ceremonies": ("Voting & Council's Dilemma",
    "Every upkeep each opponent picks money, friends or secrets and you match "
    "them. Treasures, tokens and cards, mirrored to you."),
 "Plea for Power": ("Voting & Council's Dilemma",
    "Extra turn or draw three. With vote control it is always the extra turn."),
 "Expropriate": ("Voting & Council's Dilemma",
    "The deck's top end: extra turns per time vote and steal a permanent per "
    "money vote. Tivit's double vote makes it lopsided."),
 "Tempt with Bunnies": ("Voting & Council's Dilemma",
    "Tempting offer: cards and Rabbit tokens. Opponents accepting pays YOU "
    "again, and every token is a Kambal and Mirkwood Bats trigger."),
 "Tempting Contract": ("Voting & Council's Dilemma",
    "Tempting offer for Treasures each upkeep. Opponents who take one hand you "
    "one, which Academy Manufactor turns into three artifacts."),
 "Split Decision": ("Voting & Council's Dilemma",
    "Vote to counter a spell or COPY it. Copy your own Expropriate or Torment."),
 "Vault 11: Voter's Dilemma": ("Voting & Council's Dilemma",
    "Saga: Soldiers per opponent, then two secret votes that destroy the "
    "leading creature. Removal that also builds a board."),
 "Trial of a Time Lord": ("Voting & Council's Dilemma",
    "Three chapters of exile-a-creature, then a vote on whether the cards come "
    "back at all. Bottoms them if guilty wins."),
 "Bite of the Black Rose": ("Voting & Council's Dilemma",
    "Vote: -2/-2 to their creatures, or each opponent discards two. Both modes "
    "are fine, which is what makes vote control good."),
 "Capital Punishment": ("Voting & Council's Dilemma",
    "Dilemma: each opponent sacrifices a creature per death vote AND discards "
    "per taxes vote. Scales with the number of votes you control."),
 "Tyrant's Choice": ("Voting & Council's Dilemma",
    "Two mana: each opponent sacrifices a creature, or loses 4 life. Cheapest "
    "vote payoff in the deck."),

 # --- Blink & Reuse ---
 "Ephemerate": ("Blink & Reuse",
    "One mana to re-trigger Tivit, and REBOUND does it again next upkeep. Two "
    "full dilemmas for {W}."),
 "Soulherder": ("Blink & Reuse",
    "Free blink every end step and it grows. The engine that makes Tivit's "
    "ETB a repeatable draw-and-ramp."),
 "Deadeye Navigator": ("Blink & Reuse",
    "Soulbond to Tivit: {1}{U} for a dilemma, as many times as you have mana. "
    "The deck's main mana sink."),
 "Teleportation Circle": ("Blink & Reuse",
    "End-step blink for an ARTIFACT or creature -- so it also rebuys Tamiyo's "
    "Journal and Coercive Portal, not just Tivit."),
 "Conjurer's Closet": ("Blink & Reuse",
    "End-step blink on a body-free artifact. Harder to remove than the "
    "creature-based blinkers."),
 "Displacer Kitten": ("Blink & Reuse",
    "Every noncreature spell blinks a permanent you control. Points at Tivit "
    "for a dilemma per spell."),

 # --- Token & Artifact Payoffs ---
 "Academy Manufactor": ("Token & Artifact Payoffs",
    "Every Clue or Treasure becomes a Clue AND a Food AND a Treasure. Triples "
    "Tivit's output and every other token line in the deck."),
 "Kambal, Profiteering Mayor": ("Token & Artifact Payoffs",
    "Drains for every token you make, and COPIES the tokens opponents make. "
    "The single best payoff for Tivit's Treasures and Clues."),
 "Mirkwood Bats": ("Token & Artifact Payoffs",
    "Each opponent loses 1 whenever you create OR sacrifice a token. Both "
    "halves of the Clue/Treasure cycle deal damage."),
 "Nadier's Nightblade": ("Token & Artifact Payoffs",
    "Drain whenever a token LEAVES. Cracking Clues and Treasures becomes a "
    "damage engine."),
 "Disciple of the Vault": ("Token & Artifact Payoffs",
    "One mana: an opponent loses 1 for every artifact that hits your yard. "
    "Treasures and Clues are artifacts."),
 "Marionette Master": ("Token & Artifact Payoffs",
    "Fabricate 3, then each artifact leaving the battlefield drains for its "
    "power. Sacrificing a hand of Treasures is lethal."),
 "Revel in Riches": ("Token & Artifact Payoffs",
    "Treasures off opponents' dying creatures, and an alternate win at ten. "
    "Tivit plus Academy Manufactor gets there fast."),
 "Mechanized Production": ("Token & Artifact Payoffs",
    "Copies an artifact each upkeep and wins at eight with the same name. "
    "Enchant a Treasure or a Clue."),
 "Time Sieve": ("Token & Artifact Payoffs",
    "Sacrifice five artifacts for an extra turn. Tivit plus Manufactor makes "
    "five artifacts in one attack."),
 "Cyberdrive Awakener": ("Token & Artifact Payoffs",
    "Turns every noncreature artifact into a 4/4 flier for a turn. A pile of "
    "Treasures and Clues becomes lethal out of nowhere."),

 # --- Card Advantage ---
 "Rhystic Study": ("Card Advantage",
    "The strongest draw engine in the format and it taxes the same opponents "
    "the vote cards are already squeezing."),
 "Tamiyo's Journal": ("Card Advantage",
    "A Clue every upkeep -- doubled by Academy Manufactor -- and sacrifice "
    "three Clues to tutor any card."),
 "Demonic Tutor": ("Card Advantage",
    "Unconditional tutor. Usually Illusion of Choice, Expropriate, or the "
    "missing combo half."),
 "Idyllic Tutor": ("Card Advantage",
    "Finds Rhystic Study, Revel in Riches, Mechanized Production or a "
    "Prison effect."),

 # --- Ramp & Fixing ---
 "Sol Ring": ("Ramp & Fixing",
    "Turn-one Sol Ring is the single largest swing available; also an artifact "
    "for Time Sieve and Disciple of the Vault."),
 "Arcane Signet": ("Ramp & Fixing", "Any colour in the commander's identity."),
 "Azorius Signet": ("Ramp & Fixing", "{W}{U} filtering on two."),
 "Dimir Signet": ("Ramp & Fixing", "{U}{B} filtering on two."),
 "Orzhov Signet": ("Ramp & Fixing", "{W}{B} filtering on two."),
 "Model of Unity": ("Ramp & Fixing",
    "Any-colour rock that also scries 2 for you and every opponent who voted "
    "with you -- a bribe that costs you nothing."),
 "Monologue Tax": ("Ramp & Fixing",
    "A Treasure whenever an opponent casts their second spell each turn. "
    "Ramp that scales with a busy pod."),

 # --- Removal & Interaction ---
 "Swords to Plowshares": ("Removal & Interaction",
    "One mana, exile anything. The life is irrelevant next to the tempo."),
 "Path to Exile": ("Removal & Interaction", "One mana, exile. Ramps them one land."),
 "Council's Judgment": ("Removal & Interaction",
    "Votes a permanent YOU DON'T CONTROL into exile -- no targeting, so it "
    "answers hexproof and ward. With extra votes you decide."),
 "Void Rend": ("Removal & Interaction",
    "Destroys any nonland permanent and CANNOT BE COUNTERED. The clean answer."),
 "Damn": ("Removal & Interaction",
    "Two-mana spot removal, or overload {2}{W}{W} for a full wrath."),
 "Farewell": ("Removal & Interaction",
    "Modal exile of artifacts, creatures, enchantments and graveyards. Choose "
    "the modes that spare your own board."),
 "Promise of Loyalty": ("Removal & Interaction",
    "Each player keeps one creature. You keep Tivit; the vow counters stop "
    "what survives from attacking you."),
 "Sadistic Shell Game": ("Removal & Interaction",
    "Each player picks a creature you don't control and it dies. A wrath that "
    "cannot touch your board."),
 "Trap the Trespassers": ("Removal & Interaction",
    "Secret council: stun counters on the creatures they vote for. A fog and a "
    "removal spell in one, and it never hits your side."),
 "Torment of Hailfire": ("Removal & Interaction",
    "The finisher. With Treasures from Tivit and Academy Manufactor, X is "
    "large enough to end the game outright."),
 "Magister of Worth": ("Removal & Interaction",
    "Vote: mass reanimation for everyone, or a one-sided wrath that spares "
    "itself. You hold the votes, so it is a wrath."),
 "Counterspell": ("Removal & Interaction", "The baseline. {U}{U}, counter anything."),
 "Dovin's Veto": ("Removal & Interaction",
    "Counters a noncreature spell and cannot itself be countered."),
 "An Offer You Can't Refuse": ("Removal & Interaction",
    "One mana counter; the two Treasures you hand over are a real cost, but "
    "Kambal copies them for you."),
 "Muddle the Mixture": ("Removal & Interaction",
    "Counter an instant or sorcery, or TRANSMUTE for any two-drop -- Time "
    "Sieve, Dimir Signet, or a Signet you are missing."),

 # --- Protection & Taxation ---
 "Ghostly Prison": ("Protection & Taxation",
    "Taxes attackers {2} each. Tivit is a six-drop that wants to attack, so "
    "buying turns matters."),
 "Propaganda": ("Protection & Taxation", "The blue Ghostly Prison; both, so it is redundant on purpose."),
 "Lightning Greaves": ("Protection & Taxation",
    "Haste matters here: Tivit's second dilemma is on COMBAT DAMAGE, so "
    "haste is a whole extra vote the turn it lands."),
}

LAND_NOTES = {
 "Command Tower": "Untapped any-colour. Strictly the best land in the deck.",
 "Arcane Sanctum": "Tapped triome-lite; all three colours.",
 "Raffine's Tower": "Tapped tri-land with cycling {3} when it is the wrong draw.",
 "Godless Shrine": "Shockland W/B.",
 "Hallowed Fountain": "Shockland W/U.",
 "Watery Grave": "Shockland U/B.",
 "Prairie Stream": "W/U; untapped with two basics.",
 "Sunken Hollow": "U/B; untapped with two basics.",
 "Sea of Clouds": "W/U; untapped in any multiplayer game.",
 "Vault of Champions": "W/B; untapped in any multiplayer game.",
 "Exotic Orchard": "Reads the pod's lands; in a three-colour meta it is a dual.",
 "Ancient Den": "ARTIFACT land -- a free Time Sieve / Disciple of the Vault body.",
 "Seat of the Synod": "ARTIFACT land. Same reason.",
 "Vault of Whispers": "ARTIFACT land. Same reason.",
 "Archway of Innovation": "Grants improvise, which a pile of Treasures pays.",
 "Havengul Laboratory": "Investigates for {4}; transforms into a reanimator land "
                        "after three Clues are cracked in a turn.",
 "Bojuka Bog": "Tapped, but the ETB graveyard exile is real interaction.",
 "Reliquary Tower": "No maximum hand size -- the vote and Clue draw adds up.",
 "Rogue's Passage": "Makes Tivit unblockable, which is the combat-damage dilemma.",
 "Plains": "Basic.", "Island": "Basic.", "Swamp": "Basic.",
}


# ---------------------------------------------------------------------------

def parse_list():
    out = []
    for line in open(SRC, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        m = re.match(r"^(\d+)\s+(.+?)\s+\([^)]+\)\s+\S+$", line)
        if not m:
            raise SystemExit(f"unparsed line: {line!r}")
        out.append((int(m.group(1)), m.group(2)))
    return out


def scryfall(names):
    found = {}
    for i in range(0, len(names), 75):
        body = json.dumps(
            {"identifiers": [{"name": n} for n in names[i:i + 75]]}).encode()
        req = urllib.request.Request(
            "https://api.scryfall.com/cards/collection", data=body,
            headers={**UA, "Content-Type": "application/json"})
        res = json.load(urllib.request.urlopen(req, timeout=30))
        for c in res["data"]:
            found[c["name"]] = c
            # A double-faced card comes back under its COMBINED name
            # ("Havengul Laboratory // Havengul Mystery") and is NOT reported
            # in not_found, so a decklist naming one face would silently miss.
            for face in c["name"].split(" // "):
                found.setdefault(face, c)
        for miss in res.get("not_found", []):
            # a double-faced card's combined name is not a valid identifier
            url = ("https://api.scryfall.com/cards/named?fuzzy="
                   + urllib.parse.quote(miss["name"]))
            c = json.load(urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=30))
            # key it under BOTH the requested name and Scryfall's combined
            # name, so the decklist's "Havengul Laboratory" resolves even
            # though the card is "Havengul Laboratory // Havengul Mystery"
            found[miss["name"]] = c
            found.setdefault(c["name"], c)
    return found


def primary_type(card):
    """The card type the Dashboard counts, in the order the sheet lists them."""
    tl = (card.get("type_line") or "").split("//")[0]
    for t in ("Land", "Creature", "Planeswalker", "Instant", "Sorcery",
              "Artifact", "Enchantment"):
        if t in tl:
            return t
    return tl.strip()


def price(card):
    p = card.get("prices") or {}
    for k in ("usd", "usd_foil", "usd_etched"):
        if p.get(k):
            return float(p[k])
    return 0.0


def main():
    entries = parse_list()
    cards = scryfall([n for _, n in entries])

    rows = []
    for qty, name in entries:
        c = cards[name]
        ptype = primary_type(c)
        if ptype == "Land":
            cat = "Lands"
            note = LAND_NOTES.get(name, "")
        else:
            if name not in CARDS:
                raise SystemExit(f"uncategorised nonland card: {name!r}")
            cat, note = CARDS[name]
        # Scryfall returns color_identity ALPHABETICALLY (["B","U","W"]).
        # Sort into WUBRG, which is what a decklist reads and what the
        # Dashboard's "W/U/B" lookup matches -- alphabetical order made that
        # metric silently return 0.
        ci = "/".join(sorted(c.get("color_identity") or [],
                             key="WUBRG".index)) or "C"
        mv = c.get("cmc") or 0
        rows.append({
            "qty": qty, "cat": cat, "name": c["name"], "type": ptype,
            "mv": int(mv), "ci": ci, "key": "", "usd": price(c),
            "status": "Needed", "note": note,
        })

    total = sum(r["qty"] for r in rows)
    if total != 100:
        raise SystemExit(f"deck is {total} cards, expected 100")

    order = ["Commander", "Voting & Council's Dilemma", "Blink & Reuse",
             "Token & Artifact Payoffs", "Card Advantage", "Ramp & Fixing",
             "Removal & Interaction", "Protection & Taxation", "Lands"]
    unknown = {r["cat"] for r in rows} - set(order)
    if unknown:
        raise SystemExit(f"category not in the Dashboard list: {unknown}")

    KEY = {"Tivit, Seller of Secrets", "Academy Manufactor", "Ephemerate",
           "Soulherder", "Deadeye Navigator", "Displacer Kitten",
           "Illusion of Choice", "Kambal, Profiteering Mayor", "Rhystic Study",
           "Sol Ring", "Expropriate", "Torment of Hailfire",
           "Council's Judgment", "Revel in Riches", "Command Tower"}
    for r in rows:
        r["key"] = "Yes" if r["name"] in KEY else "No"

    # Sort by category, then mana value, then name. Basics last within Lands.
    rows.sort(key=lambda r: (order.index(r["cat"]),
                             r["note"] == "Basic.", r["mv"], r["name"]))

    write(rows, order)
    audit_workbook()
    print(f"wrote {OUT}: {total} cards, {len(rows)} rows")
    for cat in order:
        n = sum(r["qty"] for r in rows if r["cat"] == cat)
        print(f"    {cat:30} {n:>3}")
    print(f"    {'TOTAL':30} {total:>3}")
    print(f"    deck value  ${sum(r['qty'] * r['usd'] for r in rows):,.2f} USD")


# ---------------------------------------------------------------------------
# self-check
# ---------------------------------------------------------------------------

def audit_workbook():
    """Read the finished file back and check the things that go wrong quietly.

    A spreadsheet formula fails SILENTLY -- it returns a plausible number
    rather than an error. Every check here corresponds to a bug that actually
    shipped: Karlov v2's ranges stopping at the last data row, its autofilter
    doing the same, and this file's own `''` quoting accident, which left the
    literal text "{rng(\"A\")}" inside a formula and dropped an apostrophe.
    """
    import openpyxl
    wb = openpyxl.load_workbook(OUT)
    d, s = wb["Decklist"], wb["Dashboard"]
    problems = []

    if d.auto_filter.ref != f"A3:J{d.max_row}":
        problems.append(f"autofilter {d.auto_filter.ref} != A3:J{d.max_row}")

    cats = {r[1] for r in d.iter_rows(min_row=4, max_row=d.max_row,
                                      values_only=True) if r[0] is not None}
    for row in s.iter_rows():
        for c in row:
            v = c.value
            if not isinstance(v, str) or not v.startswith("="):
                continue
            if "{" in v or "}" in v:
                problems.append(f"{c.coordinate}: unexpanded f-string: {v}")
            for m in re.finditer(r"Decklist!([A-J])(\d+):([A-J])(\d+)", v):
                if int(m.group(4)) <= d.max_row:
                    problems.append(f"{c.coordinate}: range {m.group(0)} stops "
                                    f"at/before the last data row {d.max_row}")
            # a quoted criterion that names a category must actually match one
            for lit in re.findall(r'"([^"<>*]+)"', v):
                if lit in cats or lit in {"Commander"}:
                    continue
                looks_like_cat = any(
                    lit.replace("'", "") == c.replace("'", "") for c in cats)
                if looks_like_cat:
                    problems.append(f"{c.coordinate}: criterion {lit!r} "
                                    f"differs from the category by punctuation")

    if problems:
        raise SystemExit("WORKBOOK SELF-CHECK FAILED:\n  "
                         + "\n  ".join(problems))
    print("self-check: autofilter, formula ranges and criteria all OK")


# ---------------------------------------------------------------------------
# workbook
# ---------------------------------------------------------------------------

def write(rows, order):
    wb = Workbook()
    d = wb.active
    d.title = "Decklist"
    s = wb.create_sheet("Dashboard")

    hdr_font = Font(name=FONT, bold=True, size=11, color="FFFFFFFF")
    hdr_fill = PatternFill("solid", fgColor=ACCENT)
    body = Font(name=FONT, size=11)
    thin = Border(bottom=Side(style="thin"))

    # --- Decklist ---------------------------------------------------------
    d["A1"] = "Tivit, Seller of Secrets — Comprehensive Decklist (v1)"
    d["A1"].font = Font(name=FONT, bold=True, size=18, color=ACCENT)
    d.row_dimensions[1].height = 22.05

    headers = ["Quantity", "Category", "Card Name", "Card Type", "Mana Value",
               "Colour Identity", "Key Card?", "Est. Cost (USD)",
               "Collection Status", "Notes & Strategy"]
    for i, h in enumerate(headers, 1):
        c = d.cell(row=3, column=i, value=h)
        c.font, c.fill = hdr_font, hdr_fill
        c.alignment = Alignment(horizontal="center", wrap_text=True)
    d.row_dimensions[3].height = 27.75

    centre = {1, 5, 7}
    for n, r in enumerate(rows, start=4):
        vals = [r["qty"], r["cat"], r["name"], r["type"], r["mv"], r["ci"],
                r["key"], r["usd"], r["status"], r["note"]]
        for i, v in enumerate(vals, 1):
            c = d.cell(row=n, column=i, value=v)
            c.font, c.border = body, thin
            if i in centre:
                c.alignment = Alignment(horizontal="center")
            elif i == 8:
                c.alignment = Alignment(horizontal="right")
                c.number_format = r"\$#,##0.00"
            elif i == 10:
                c.alignment = Alignment(wrap_text=True)
        d.row_dimensions[n].height = 15.0

    last = 3 + len(rows)
    for col, w in zip("ABCDEFGHIJ",
                      [11, 26, 34, 14, 11, 15, 11, 16, 20.57, 94]):
        d.column_dimensions[col].width = w
    d.freeze_panes = "A4"
    d.auto_filter.ref = f"A3:J{last}"      # the REAL last row, not last-1

    # --- Dashboard --------------------------------------------------------
    def sect(row, text):
        c = s.cell(row=row, column=2, value=text)
        c.font = Font(name=FONT, bold=True, size=14, color=ACCENT)
        s.row_dimensions[row].height = 17.35

    def head(row, a, b):
        for col, v in ((2, a), (3, b)):
            c = s.cell(row=row, column=col, value=v)
            c.font, c.fill = hdr_font, hdr_fill
            c.alignment = Alignment(horizontal="center")

    def pair(row, label, formula, fmt=None, bold=False, inp=False):
        k = s.cell(row=row, column=2, value=label)
        k.font = Font(name=FONT, size=11, bold=True if not bold else True)
        v = s.cell(row=row, column=3, value=formula)
        v.font = Font(name=FONT, size=11, bold=bold)
        if fmt:
            v.number_format = fmt
        if inp:
            v.fill = PatternFill("solid", fgColor="FFFFFF00")
        s.row_dimensions[row].height = 15.0

    D = f"Decklist!"
    rng = lambda col: f"{D}{col}4:{col}{LAST}"     # noqa: E731

    s["B2"] = "Tivit, Seller of Secrets"
    s["B2"].font = Font(name=FONT, bold=True, size=18, color=ACCENT)
    s.row_dimensions[2].height = 22.05
    s["B3"] = ("Esper Votes, Blink & Artifact Tokens — Commander Deck "
               "Dashboard & Analytics (v1)")
    s["B3"].font = Font(name=FONT, size=12, color=GREY)

    sect(5, "Key Deck Metrics")
    head(6, "Metric", "Value")
    pair(7, "Total Cards", f"=SUM({rng('A')})")
    pair(8, "Total Deck Cost (USD)",
         f"=SUMPRODUCT({rng('A')},{rng('H')})", r"\$#,##0.00")
    pair(9, "USD → CAD Rate", 1.4203, "0.0000", inp=True)
    pair(10, "Total Deck Cost (CAD)", "=C8*$C$9", r"\$#,##0.00")
    pair(11, "Max Mana Value", f"=MAX({rng('E')})")
    pair(12, "Avg Mana Value (Spells)",
         f'=AVERAGEIF({rng("B")},"<>Lands",{rng("E")})', "0.00")
    pair(13, "Total Lands", f'=SUMIF({rng("B")},"Lands",{rng("A")})')
    pair(14, "Basic Lands",
         f'=SUMIFS({rng("A")},{rng("B")},"Lands",{rng("J")},"Basic*")')
    pair(15, "Artifact Lands",
         f'=SUMIFS({rng("A")},{rng("B")},"Lands",{rng("J")},"ARTIFACT land*")')
    # NOTE THE QUOTING. Written as f'..."Voting & Council''s Dilemma"...' this
    # silently became two adjacent literals -- the second NOT an f-string, so
    # the range stayed as the text "{rng(...)}" and the apostrophe vanished.
    # Excel is happy with an apostrophe inside a double-quoted criterion; it is
    # Python that needs the care.
    vote_cat = "Voting & Council's Dilemma"
    pair(16, "Voting Cards (incl. commander)",
         f'=SUMIF({rng("B")},"{vote_cat}",{rng("A")})'
         f'+SUMIF({rng("B")},"Commander",{rng("A")})')
    pair(17, "Three-Colour (W/U/B) Cards",
         f'=SUMIF({rng("F")},"W/U/B",{rng("A")})')

    note = s.cell(row=19, column=2, value=(
        "Tivit votes twice on its own. Ballot Broker and Brago's "
        "Representative add one each, so three of the four are a majority in a "
        "four-player pod — and Illusion of Choice simply takes every vote."))
    note.font = Font(name=FONT, size=9, color=FAINT)

    sect(22, "Mana Curve")
    head(23, "Mana Value", "Count")
    for i, mv in enumerate(range(1, 10)):
        r = 24 + i
        s.cell(row=r, column=2, value=mv).font = Font(name=FONT, size=11)
        c = s.cell(row=r, column=3, value=(
            f'=SUMIFS({rng("A")},{rng("E")},B{r},{rng("B")},"<>Lands")'))
        c.font = Font(name=FONT, size=11)
        s.row_dimensions[r].height = 15.0

    sect(35, "Category Breakdown")
    head(36, "Category", "Count")
    first = 37
    for i, cat in enumerate(order):
        r = first + i
        s.cell(row=r, column=2, value=cat).font = Font(name=FONT, size=11,
                                                       bold=True)
        c = s.cell(row=r, column=3,
                   value=f'=SUMIF({rng("B")},B{r},{rng("A")})')
        c.font = Font(name=FONT, size=11)
        s.row_dimensions[r].height = 15.0
    tot = first + len(order)
    pair(tot, "Total", f"=SUM(C{first}:C{tot - 1})", bold=True)

    types = ["Creature", "Instant", "Sorcery", "Artifact", "Enchantment",
             "Land"]
    sect(tot + 3, "Card Type Breakdown")
    head(tot + 4, "Card Type", "Count")
    tfirst = tot + 5
    for i, t in enumerate(types):
        r = tfirst + i
        s.cell(row=r, column=2, value=t).font = Font(name=FONT, size=11,
                                                     bold=True)
        c = s.cell(row=r, column=3,
                   value=f'=SUMIF({rng("D")},B{r},{rng("A")})')
        c.font = Font(name=FONT, size=11)
        s.row_dimensions[r].height = 15.0
    ttot = tfirst + len(types)
    pair(ttot, "Total", f"=SUM(C{tfirst}:C{ttot - 1})", bold=True)

    notes = [
        "• Mana value, card type, colour identity and price in the Decklist "
        "sheet are FETCHED FROM SCRYFALL by build_tivit_xlsx.py, not typed by "
        "hand. Re-run it to refresh prices.",
        "• Prices are Scryfall's USD mid, and are missing for a few printings; "
        "those fall back to foil, then to 0. Check before ordering.",
        "• Yellow cells are inputs. C9 (FX rate) is carried over from the "
        "Karlov v2 and Lorehold v16 books at 1 USD = 1.4203 CAD.",
        "• Collection Status in column I is an input — everything starts at "
        "'Needed'; set it to 'Owned' or 'Owned (Other Deck)' as you check.",
        "• Torment of Hailfire is {X}{B}{B} and is counted at MV 2, i.e. X = 0, "
        "the same convention the Karlov book uses for Debt to the Deathless.",
        "• Damn is counted at MV 2 ({B}{B}). Its wrath mode is the overload "
        "cost {2}{W}{W}, MV 4, which is neither the cast cost nor an average.",
        "• Havengul Laboratory is a double-faced land; the front face is used "
        "for type and colour identity.",
        "• Ancient Den, Seat of the Synod and Vault of Whispers are ARTIFACT "
        "lands. They count as Lands in the category breakdown and as Land in "
        "the type breakdown, but they are also live artifacts for Time Sieve, "
        "Disciple of the Vault and Marionette Master.",
        "• EVERY DASHBOARD FORMULA RANGES TO ROW 200, deliberately. The Karlov "
        "v2 book had 34 formulas bounded to the last data row and silently "
        "dropped a card when the list grew; openpyxl does not rewrite ranges.",
    ]
    sect(ttot + 3, "Notes on this sheet")
    for i, t in enumerate(notes):
        r = ttot + 4 + i
        c = s.cell(row=r, column=2, value=t)
        c.font = Font(name=FONT, size=10, color=GREY)
        s.row_dimensions[r].height = 15.0

    s.column_dimensions["A"].width = 4.0
    s.column_dimensions["B"].width = 45.0
    s.column_dimensions["C"].width = 14.0

    wb.save(OUT)


if __name__ == "__main__":
    sys.exit(main())
