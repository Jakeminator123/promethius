#!/usr/bin/env python3
"""
build_heavy_analysis.py – v14 (board_cards + holecards)

• Läser råhänder från poker.db och uppdaterar / bygger heavy_analysis.db
  med:
      hand_info · streets · players · actions · postflop_scores
• BB-normalisering: Om NORMALIZE_CUR=Y i config, delas alla belopp med chip_value

Nytt i v14
──────────
1. actions-tabellen har kolumnerna
       board_cards TEXT   – community-kort som syns före varje action
       holecards   TEXT   – spelarens hålkort
2. ensure() lägger till dem vid behov.
3. BB-normalisering för jämförbara värden mellan olika speltyper
"""

from __future__ import annotations
import json, re, sqlite3, time, argparse
from collections import deque
from pathlib import Path
from typing import Dict, Any, List, Tuple

# ── 1. Import centraliserad path-hantering ──────────────────────────
from script_paths import ROOT, SRC_DB, DST_DB, CFG

# Kolla om vi ska normalisera valutor
NORMALIZE_CUR = CFG.get("NORMALIZE_CUR", "N").upper() == "Y"

# Hantera kommandoradsargument
ap = argparse.ArgumentParser()
ap.add_argument("--src"); ap.add_argument("--dst")
cli = ap.parse_args()
if cli.src: SRC_DB = Path(cli.src).expanduser().resolve()
if cli.dst: DST_DB = Path(cli.dst).expanduser().resolve()
DST_DB.parent.mkdir(parents=True, exist_ok=True)

# ── 2. JSON-kolumnen i hands ─────────────────────────────────────────
HANDS_TBL = "hands"
def detect_json_col(con: sqlite3.Connection) -> str:
    prefer = {"raw_json", "hand_json", "json"}
    for _, n, t, *_ in con.execute(f"PRAGMA table_info({HANDS_TBL})"):
        if t.lower() == "text" and n in prefer:
            return n
    for _, n, t, *_ in con.execute(f"PRAGMA table_info({HANDS_TBL})"):
        if t.lower() == "text" and n not in {"id", "hand_date", "seq", "chip_value_in_displayed_currency"}:
            return n
    raise RuntimeError("Ingen JSON-kolumn i hands-tabellen.")

# ── 3. position-ordning ──────────────────────────────────────────────
SEAT_ORDER = ["UTG","UTG1","UTG2","LJ","HJ","CO","BTN","SB","BB"]

# ── 4. helpers för situation_string ──────────────────────────────────
def tokenize(s: str) -> List[str]:
    out, i = [], 0
    while i < len(s):
        if s[i] in "xfc":
            out.append(s[i]); i += 1
        elif s[i] == "r":
            j = i + 1
            while j < len(s) and s[j].isdigit():
                j += 1
            out.append(s[i:j]); i = j
        else:
            raise ValueError(f"Fel tecken: {s[i]}")
    return out

def split_streets(s: str) -> List[Tuple[str, List[str], str]]:
    parts, cur, cards, name = [], "", "", "preflop"
    for part in re.split(r"(\[[^\]]+\])", s):
        if part.startswith("["):
            parts.append((name, tokenize(cur), cards))
            cur, cards = "", part.strip("[]")
            name = {"preflop":"flop","flop":"turn","turn":"river"}.get(name,"river")
        else:
            cur += part
    parts.append((name, tokenize(cur), cards))
    return [p for p in parts if p[1] or p[2]]

def rotate_postflop(active: List[str]) -> deque:
    for first in ("SB","BB"):
        if first in active:
            dq = deque(active); dq.rotate(-active.index(first)); return dq
    return deque(active)

# ── Normaliseringsfunktion ───────────────────────────────────────────
def normalize_amount(amount: float, chip_value: float) -> float:
    """Normaliserar belopp baserat på chip_value om NORMALIZE_CUR=Y."""
    if NORMALIZE_CUR and chip_value and chip_value != 0:
        return amount / chip_value
    return amount

# ── 5. parse_hand → rader ───────────────────────────────────────────
def parse_hand(h: Dict[str, Any],
               extra_scores: Dict[str, Any] | None = None,
               hand_date: str | None = None,
               seq: int | None = None,
               chip_value: float | None = None):
    """
    Returnerar:
        rows_s, rows_a, rows_p, hand_info, score_rows
    """
    # Hämta chip_value om det inte skickats med
    if chip_value is None:
        chip_value = h.get("chip_value_in_displayed_currency", 1.0) or 1.0
    
    # ── 5.1 grund-setup ──────────────────────────────────────────────
    pos2info = h["positions"]
    seats = [p for p in SEAT_ORDER if p in pos2info]
    active = seats[:]

    pos2name = {p: i.get("name") or i["stub"] for p, i in pos2info.items()}
    
    # Normalisera stacks
    stack0 = {p: int(normalize_amount(int(i["stack"]), chip_value)) 
              for p, i in pos2info.items()}
    invested = {p: 0 for p in pos2info}

    # Normalisera blinds och ante
    bb = int(normalize_amount(h.get("big_blind_amount") or 0, chip_value))
    sb = int(normalize_amount(h.get("small_blind_amount") or 0, chip_value))
    ante = int(normalize_amount(h.get("ante_amount") or 0, chip_value))

    pot = sb + bb + ante * len(seats)
    if "SB" in invested: invested["SB"] += sb
    if "BB" in invested: invested["BB"] += bb
    for p in invested: invested[p] += ante
    cur_max = bb

    # ── 5.2 score-cache ─────────────────────────────────────────────
    partial = h.get("partial_scores") or extra_scores or {}
    rows_s, rows_a, rows_p = [], [], []
    score_rows = [
        (h["stub"], k,
         v if isinstance(v, float) else v.get("action_score"),
         None if isinstance(v, float) else v.get("decision_difficulty"))
        for k, v in partial.items()
    ]

    # ── 5.3 loopa genom situation_string ────────────────────────────
    order = deque(active)
    state = ""
    idx = 0
    board_seen = ""                # 🆕

    for st_idx, (street, toks, board) in enumerate(split_streets(h["situation_string"])):
        if board:
            board_seen += board     # 🆕
            rows_s.append((h["stub"], street, board))
        if street != "preflop":
            order = rotate_postflop(active)

        board_to_add = f"[{board}]" if board else ""

        for tk in toks:
            if board_to_add:
                state += board_to_add
                board_to_add = ""

            state_next = state + tk
            pos, act = order[0], tk[0]
            
            # Normalisera raise-belopp
            amt_to = None
            if act == "r":
                raw_amt = int(tk[1:])
                amt_to = int(normalize_amount(raw_amt, chip_value))

            stack_b, pot_b = stack0[pos] - invested[pos], pot
            put = 0
            if act == "r":
                put = amt_to - invested[pos]; cur_max = amt_to
            elif act == "c":
                put = cur_max - invested[pos]
            invested[pos] += put; pot += put
            stack_a = stack_b - put

            if act == "f":
                active.remove(pos); order.popleft()
            else:
                order.rotate(-1)
            players_left = len(active)

            rows_a.append((
                h["stub"], idx, street, st_idx,
                pos,
                pos2info[pos]["stub"],                 # player_id
                pos2name[pos],                         # nickname
                act, amt_to,
                stack_b, stack_a, put, pot_b, pot,
                players_left, int(stack_a == 0),
                None, None,                            # score & difficulty
                state,                                 # state_prefix
                board_seen,                            # 🆕 board_cards
                ",".join(pos2info[pos]["hole_cards"])  # 🆕 holecards
            ))
            idx += 1; state = state_next

        cur_max = 0
        for p in active: invested[p] = 0

    # ── 5.4 players- & hand_info-rader ──────────────────────────────
    # Normalisera money_won
    rows_p = [
        (h["stub"], p, pos2name[p], stack0[p],
         ",".join(pos2info[p]["hole_cards"]),
         normalize_amount(pos2info[p].get("money_won") or 0, chip_value))
        for p in pos2info
    ]
    hand_info = (
        h["stub"], hand_date, seq,
        int(h.get("is_mtt") or 0), int(h.get("is_cash") or 0),
        bb, sb, ante, len(seats), h.get("pot_type")
    )
    return rows_s, rows_a, rows_p, hand_info, score_rows

# ── 6. schema ────────────────────────────────────────────────────────
SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS hand_info(
    hand_id     TEXT PRIMARY KEY,
    hand_date   TEXT,
    seq         INTEGER,
    is_mtt      INTEGER,
    is_cash     INTEGER,
    big_blind   INTEGER,
    small_blind INTEGER,
    ante        INTEGER,
    players_cnt INTEGER,
    pot_type    TEXT
);
CREATE TABLE IF NOT EXISTS streets(
    hand_id TEXT, street TEXT, board TEXT,
    PRIMARY KEY(hand_id, street)
);
CREATE TABLE IF NOT EXISTS players(
    hand_id TEXT, position TEXT, nickname TEXT,
    stack0 INTEGER, holecards TEXT, money_won REAL,
    PRIMARY KEY(hand_id, position)
);
CREATE TABLE IF NOT EXISTS actions(
    hand_id TEXT, action_order INTEGER,
    street TEXT, street_index INTEGER,
    position TEXT,
    player_id TEXT,
    nickname TEXT,
    action TEXT, amount_to INTEGER,
    stack_before INTEGER, stack_after INTEGER,
    invested_this_action INTEGER,
    pot_before INTEGER, pot_after INTEGER,
    players_left INTEGER, is_allin INTEGER,
    action_score REAL, decision_difficulty REAL,
    state_prefix TEXT,
    board_cards TEXT,             -- 🆕
    holecards   TEXT,             -- 🆕
    PRIMARY KEY(hand_id, action_order)
);
CREATE TABLE IF NOT EXISTS postflop_scores(
    hand_id TEXT, node_string TEXT,
    action_score REAL, decision_difficulty REAL,
    PRIMARY KEY(hand_id, node_string)
);
"""

def ensure(con: sqlite3.Connection) -> None:
    """Skapa schema och lägg till nya kolumner om de saknas."""
    con.executescript(SCHEMA)

    # hand_info migrations
    cur = con.execute("PRAGMA table_info(hand_info)")
    cols = {r[1] for r in cur.fetchall()}
    if "hand_date" not in cols:
        con.execute("ALTER TABLE hand_info ADD COLUMN hand_date TEXT")
    if "seq" not in cols:
        con.execute("ALTER TABLE hand_info ADD COLUMN seq INTEGER")
    if "pot_type" not in cols:
        con.execute("ALTER TABLE hand_info ADD COLUMN pot_type TEXT")

    # actions migrations
    cur = con.execute("PRAGMA table_info(actions)")
    acols = {r[1] for r in cur.fetchall()}
    if "player_id" not in acols:
        con.execute("ALTER TABLE actions ADD COLUMN player_id TEXT")
    if "board_cards" not in acols:
        con.execute("ALTER TABLE actions ADD COLUMN board_cards TEXT")
    if "holecards" not in acols:
        con.execute("ALTER TABLE actions ADD COLUMN holecards TEXT")

    con.commit()

def done_ids(c) -> set[str]:
    return {r[0] for r in c.execute("SELECT hand_id FROM hand_info")}

# ── 7. fyll saknade score-fält ───────────────────────────────────────
def fill_missing_scores(con: sqlite3.Connection, hand_id: str):
    cur = con.cursor()
    nodes = cur.execute(
        "SELECT node_string, action_score, decision_difficulty "
        "FROM postflop_scores WHERE hand_id=? ORDER BY LENGTH(node_string)",
        (hand_id,)
    ).fetchall()
    if not nodes:
        return
    upd = []
    for rowid, prefix, act in cur.execute(
        "SELECT rowid, state_prefix, action "
        "FROM actions WHERE hand_id=? AND action_score IS NULL",
        (hand_id,)
    ):
        wanted = prefix + act
        for ns, sc, dd in nodes:
            if ns.startswith(wanted):
                upd.append((sc, dd, rowid)); break
    if upd:
        cur.executemany(
            "UPDATE actions SET action_score=?, decision_difficulty=? WHERE rowid=?",
            upd
        ); con.commit()

# ── 8. import-loop ───────────────────────────────────────────────────
def main():
    while not SRC_DB.exists():
        print("⏳ väntar på poker.db …"); time.sleep(3)

    src = sqlite3.connect(SRC_DB); src.row_factory = sqlite3.Row
    json_col = detect_json_col(src)
    dst = sqlite3.connect(DST_DB); ensure(dst)

    done = done_ids(dst)

    # cache för partial_scores
    ps_cache: Dict[str, Any] = {}
    try:
        for hid, js in src.execute("SELECT id, json FROM partial_scores"):
            ps_cache[hid] = json.loads(js)
    except sqlite3.OperationalError:
        pass

    # Kolla om chip_value_in_displayed_currency finns i databasen
    has_chip_value = False
    try:
        cursor = src.execute("PRAGMA table_info(hands)")
        cols = {r[1] for r in cursor.fetchall()}
        has_chip_value = "chip_value_in_displayed_currency" in cols
    except:
        pass

    cs, cd = src.cursor(), dst.cursor(); new = 0
    
    # Bygg SQL-query beroende på om chip_value finns
    if has_chip_value:
        query = f"SELECT id, hand_date, seq, chip_value_in_displayed_currency, {json_col} FROM {HANDS_TBL}"
    else:
        query = f"SELECT id, hand_date, seq, {json_col} FROM {HANDS_TBL}"
    
    for row in cs.execute(query):
        hid, hdat, seq = row["id"], row["hand_date"], row["seq"]
        if hid in done:
            continue

        hand = json.loads(row[json_col])
        
        # Hämta chip_value om den finns
        chip_value = None
        if has_chip_value:
            chip_value = row["chip_value_in_displayed_currency"]
        
        streets, actions, players, info, score_rows = parse_hand(
            hand, ps_cache.get(hid), hdat, seq, chip_value)

        cd.execute("INSERT OR IGNORE INTO hand_info VALUES (?,?,?,?,?,?,?,?,?,?)", info)
        cd.executemany("INSERT OR IGNORE INTO streets VALUES (?,?,?)", streets)
        cd.executemany("INSERT OR IGNORE INTO players VALUES (?,?,?,?,?,?)", players)
        cd.executemany(
            """INSERT OR IGNORE INTO actions 
            (hand_id, action_order, street, street_index, position, player_id, nickname,
             action, amount_to, stack_before, stack_after, invested_this_action,
             pot_before, pot_after, players_left, is_allin, action_score, decision_difficulty,
             state_prefix, board_cards, holecards)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            actions)  # 21 kolumner med explicit kolumnnamn
        cd.executemany(
            "INSERT OR IGNORE INTO postflop_scores VALUES (?,?,?,?)", score_rows)

        fill_missing_scores(dst, hid)
        new += 1
        if new % 200 == 0:
            dst.commit(); print(f"• {new:,} HH importerade …")

    dst.commit(); src.close(); dst.close()
    
    if NORMALIZE_CUR:
        print(f"✅ klart – {new:,} händer till {DST_DB.name} (med BB-normalisering)")
    else:
        print(f"✅ klart – {new:,} händer till {DST_DB.name}")

if __name__ == "__main__":
    main()
