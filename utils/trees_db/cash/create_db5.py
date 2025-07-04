#!/usr/bin/env python3
"""
build_simple_poker_db.py  v2.0
────────────────────────────────────────────────────────────────────
Bygger en *platt* SQLite-databas (ranges_flat) från ett katalogträd
med solver-ranger.  NYTT i v2.0: kolumnen action_sequence lagras
UTAN prefixet “PF:”.

Mappkonvention
──────────────
  ffr25_btn  →  F-F-R2.5   /  BTN
  _utg       →  ''         /  UTG   (tom sekvens = första att agera)

Filtyper
────────
  • exakt EN .json      – range.json
  • eller en/flera .txt – f.txt, c.txt, r25.txt …  (filnamnet = action)

Körning
───────
  GUI:  python build_simple_poker_db.py
        → välj rotmapp  → välj var .db ska sparas
  CLI:  python build_simple_poker_db.py --tree <dir> --out <fil.db>
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

# ─────────────── Position-alias (inkl. BU/BUT/BN) ───────────────
POSITION_ALIASES = {
    "UTG": ["UTG", "EP1", "P1", "LJ", "LOWJACK", "LOW_JACK"],
    "HJ":  ["HJ", "HIGHJACK", "P2", "P3"],
    "CO":  ["CO", "CUTOFF"],
    "BTN": ["BTN", "BUTTON", "BU", "BUT", "BN"],
    "SB":  ["SB", "SMALLBLIND", "SMALL_BLIND"],
    "BB":  ["BB", "BIGBLIND", "BIG_BLIND"],
}
_SAN = lambda s: s.upper().replace(" ", "").replace("_", "")
ALIAS_TO_CANON = {_SAN(a): canon for canon, lst in POSITION_ALIASES.items() for a in lst}

# ─────────────── Mappnamn → (action_seq, position) ──────────────
_RX_RAISE = re.compile(r"r(\d+)", re.I)


def _decode_folder(folder: str) -> tuple[str, str]:
    """
    'ffr25_btn'  →  ('F-F-R2.5', 'BTN')
    '_utg'       →  ('',          'UTG')
    """
    if "_" not in folder:
        raise ValueError("Undermappens namn måste innehålla '_'")
    seq_part, raw_pos = folder.rsplit("_", 1)

    actions, i = [], 0
    while i < len(seq_part):
        ch = seq_part[i].lower()
        if ch in "fcx":                       # fold / call / check
            actions.append(ch.upper())
            i += 1
        elif ch == "r":                       # raise + storlek
            m = _RX_RAISE.match(seq_part[i:])
            if m:
                d = m.group(1)                # "25" → "2.5"
                amt = d if len(d) == 1 else f"{d[:-1]}.{d[-1]}"
                actions.append(f"R{amt}")
                i += 1 + len(d)
            else:
                actions.append("R")
                i += 1
        else:                                 # okänt tecken → hoppa
            i += 1

    seq = "-".join(actions)                   # 〈ingen〉 prefix »PF:« längre!
    pos = ALIAS_TO_CANON.get(_SAN(raw_pos), raw_pos.upper())
    return seq, pos


# ─────────────── SQLite-init (en tabell) ────────────────────────
DDL = """
PRAGMA foreign_keys = OFF;
CREATE TABLE ranges_flat(
    id              INTEGER PRIMARY KEY,
    action_sequence TEXT NOT NULL,  -- utan 'PF:'
    position        TEXT NOT NULL,
    action          TEXT NOT NULL,
    combo           TEXT NOT NULL,
    frequency       REAL NOT NULL
);
"""


def _init_db(path: Path) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.executescript(DDL)
    conn.commit()
    return conn


# ─────────────── txt-parser ─────────────────────────────────────
def _read_txt(path: Path) -> dict[str, float]:
    """Läser 'Combo:freq' par, separerade med radbryt eller komma."""
    content = path.read_text(encoding="utf-8")
    tokens = content.replace("\n", ",").split(",")
    combos: dict[str, float] = {}
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if ":" in tok:
            c, f = tok.split(":", 1)
            combos[c.strip()] = float(f)
        else:  # ingen frekvens angiven ⇒ anta 1.0
            combos[tok] = 1.0
    return combos


# ─────────────── Träds-import ───────────────────────────────────
def _import_tree(base: Path, conn: sqlite3.Connection) -> None:
    cur, rows = conn.cursor(), 0
    for dp, _, files in os.walk(base):
        folder = Path(dp).name
        try:
            seq, pos = _decode_folder(folder)
        except ValueError:
            continue

        json_files = [f for f in files if f.lower().endswith(".json")]
        txt_files = [f for f in files if f.lower().endswith(".txt")]

        # JSON prioriteras om den finns
        if len(json_files) == 1:
            data = json.loads(Path(dp, json_files[0]).read_text(encoding="utf-8"))
        elif txt_files:
            data: dict[str, dict[str, float]] = {}
            for fname in txt_files:
                act = Path(fname).stem.lower()  # "f.txt" → "f"
                data[act] = _read_txt(Path(dp, fname))
        else:
            continue  # ingen datafil hittad → hoppa

        for act, combos in data.items():
            for combo, freq in combos.items():
                cur.execute(
                    "INSERT INTO ranges_flat(action_sequence,position,action,combo,frequency)"
                    "VALUES(?,?,?,?,?)",
                    (seq, pos, act.lower(), combo, float(freq)),
                )
                rows += 1

    conn.commit()
    print(f"✓ Import klar – {rows} rader insatta.")


# ─────────────── GUI-assistans (valfritt) ───────────────────────
try:
    import tkinter as _tk
    from tkinter import filedialog as _fd

    _HAS_TK = True
except ImportError:
    _HAS_TK = False


def _choose_dir(title: str) -> Path:
    if not _HAS_TK:
        sys.exit("Tkinter saknas – ange --tree manuellt.")
    root = _tk.Tk(); root.withdraw()
    d = _fd.askdirectory(title=title)
    root.destroy()
    if not d:
        sys.exit("Avbrutet.")
    return Path(d)


def _choose_save(title: str, default: str) -> Path:
    """Returnerar alltid en filväg. Pekar användaren på en mapp → lägg till default."""
    if not _HAS_TK:
        sys.exit("Tkinter saknas – ange --out manuellt.")
    root = _tk.Tk(); root.withdraw()
    p = _fd.asksaveasfilename(
        title=title,
        defaultextension=".db",
        initialfile=default,
    )
    root.destroy()
    if not p:
        sys.exit("Avbrutet.")
    p = Path(p)
    if p.is_dir():  # användaren valde bara en mapp
        p = p / default
    return p


# ─────────────── main / CLI ─────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Bygg platt poker-range-DB (en tabell)")
    ap.add_argument("--tree", help="Rotmapp med solver-ranger (.json / .txt)")
    ap.add_argument("--out", help="Utfil (.db)")
    args = ap.parse_args()

    if args.tree and args.out:  # rent CLI-läge
        base, db = Path(args.tree).expanduser(), Path(args.out).expanduser()
    else:  # GUI-läge
        base = _choose_dir("Välj rotmapp med mappar som _utg, ffr25_btn …")
        db = _choose_save("Spara SQLite-databas som …", "poker_ranges.db")

    if not base.is_dir():
        sys.exit(f"❌ Hittar ingen mapp: {base}")
    db.parent.mkdir(parents=True, exist_ok=True)

    conn = _init_db(db)
    _import_tree(base, conn)
    conn.close()
    print(f"DB sparad → {db}")


if __name__ == "__main__":
    main()
