#!/usr/bin/env python3
"""
avg_labels.py – översikt per action_label

Visar:
  • actions        – antal rader med labeln
  • opportunities  – SUM(can_<label>) om kolumnen finns, annars n/a
  • pct            – actions / opportunities
  • avg_score      – medel action_score   (NULL ignoreras)
  • avg_difficulty – medel decision_difficulty (NULL ignoreras)
"""

from pathlib import Path
import argparse, sqlite3, pandas as pd, sys, textwrap

# ── 1. CLI ──────────────────────────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument("--db", help="Full sökväg till heavy_analysis.db (valfritt)")
ap.add_argument("--quiet", action="store_true", help="Dölj debug-utskrifter")
args = ap.parse_args()

def dbg(msg: str):
    if not args.quiet:
        print(msg)

# ── 2. Hitta/helt sät DB-fil ───────────────────────────────────────
def locate_db(start: Path) -> Path | None:
    cur = start
    while True:
        for cand in (
            cur / "heavy_analysis.db",
            cur / "local_data" / "database" / "heavy_analysis.db",
        ):
            if cand.is_file():
                return cand
        if cur == cur.parent:
            return None
        cur = cur.parent

db_path = (
    Path(args.db).expanduser().resolve()
    if args.db
    else locate_db(Path(__file__).resolve().parent)
)
if not db_path or not db_path.is_file():
    sys.exit("❌ Hittar ingen heavy_analysis.db – ange --db.")

dbg(f"Öppnar DB-filen: {db_path}")

con = sqlite3.connect(db_path)
cur = con.cursor()

# ── 3. Vilka kolumner finns? ───────────────────────────────────────
tbl_cols = {r[1] for r in cur.execute("PRAGMA table_info(actions)")}

# ── 4. Labels att sammanfatta ──────────────────────────────────────
LABELS = [
    # user-specificerade
    "check", "call", "fold",
    "bet", "raise",
    "open", "squeeze",
    "2bet", "3bet", "4bet", "5bet+",
    "limp_raise_fold_checkraise_call",
    "limp_raise_fold_checkraise_fold",
]

# ── 5. Samla statistik per label ───────────────────────────────────
rows = []
for lab in LABELS:
    n_act, = cur.execute(
        "SELECT COUNT(*) FROM actions WHERE action_label=?", (lab,)
    ).fetchone()

    can_col = f"can_{lab}"
    if can_col in tbl_cols:
        n_opp, = cur.execute(f"SELECT SUM({can_col}) FROM actions").fetchone()
        pct = n_act / n_opp if n_opp else None
    else:
        n_opp, pct = None, None

    avg_sc, avg_dd = cur.execute(
        """
        SELECT AVG(action_score), AVG(decision_difficulty)
        FROM actions
        WHERE action_label=?""",
        (lab,),
    ).fetchone()

    rows.append(
        dict(
            label=lab,
            actions=n_act,
            opportunities=n_opp if n_opp is not None else "n/a",
            pct=f"{pct:.2%}" if pct is not None else "n/a",
            avg_score=f"{avg_sc:.3f}" if avg_sc is not None else "n/a",
            avg_difficulty=f"{avg_dd:.3f}" if avg_dd is not None else "n/a",
        )
    )

con.close()

# ── 6. Skriv tabell till CMD ───────────────────────────────────────
df = pd.DataFrame(rows)
print(
    "\n"
    + textwrap.dedent(
        """
    ── Översikt per action_label ────────────────────────────────────
"""
    )
)
print(
    df.to_string(
        index=False,
        formatters={
            "actions": "{:,}".format,
            "opportunities": lambda x: "{:,}".format(x)
            if isinstance(x, (int, float))
            else x,
        },
    )
)
