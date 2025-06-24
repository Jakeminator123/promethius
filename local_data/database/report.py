#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def extract_detailed_schema(db_path, output_path, sample_limit=5):
    """
    Dokumenterar schema, foreign keys, index, antal rader och exempeldata
    från en SQLite-databas.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"Databas: {os.path.basename(db_path)}\n")
        f.write("="*60 + "\n\n")

        # Hämta alla tabeller
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            f.write("Inga tabeller hittades.\n")
            return

        for tbl in tables:
            f.write(f"Tabell: {tbl}\n")
            f.write("-"*40 + "\n")

            # Kolumnmetadata
            cols = cur.execute(f"PRAGMA table_info('{tbl}');").fetchall()
            for cid, name, ctype, notnull, dflt, pk in cols:
                flags = []
                if pk:       flags.append("PK")
                if notnull:  flags.append("NOT NULL")
                f.write(f"  • {name} ({ctype}) {' '.join(flags)}\n")

            # Foreign keys
            f.write("\n  Foreign keys:\n")
            fkeys = cur.execute(f"PRAGMA foreign_key_list('{tbl}');").fetchall()
            if fkeys:
                for fk in fkeys:
                    # (id, seq, table, from, to, on_update, on_delete, match)
                    _, _, ref_table, fr, to, up, down, match = fk
                    f.write(f"    ↳ {fr} → {ref_table}({to}) "
                            f"[upd:{up} del:{down} match:{match}]\n")
            else:
                f.write("    (inga)\n")

            # Index
            f.write("\n  Index:\n")
            idxs = cur.execute(f"PRAGMA index_list('{tbl}');").fetchall()
            if idxs:
                for idx in idxs:
                    # (seq, name, unique, origin, partial)
                    _, name, unique, origin, partial = idx
                    f.write(f"    • {name} "
                            f"(unique={bool(unique)}, origin={origin}, partial={partial})\n")
            else:
                f.write("    (inga)\n")

            # Antal rader
            count = cur.execute(f"SELECT COUNT(*) FROM '{tbl}';").fetchone()[0]
            f.write(f"\n  Antal rader: {count}\n")

            # Exempeldata
            f.write("\n  Exempeldata:\n")
            rows = cur.execute(f"SELECT * FROM '{tbl}' LIMIT {sample_limit};").fetchall()
            headers = [c[1] for c in cols]
            if rows:
                f.write("    | " + " | ".join(headers) + "\n")
                f.write("    " + "-"*(4*len(headers)+len(headers)-1) + "\n")
                for row in rows:
                    f.write("    | " + " | ".join(str(v) for v in row) + "\n")
            else:
                f.write("    (ingen data)\n")

            f.write("\n\n")

    conn.close()

def main():
    """
    Går igenom alla .db-filer i aktuell mapp och skapar en
    motsvarande _detailed.txt för varje databas.
    """
    cwd = os.getcwd()
    db_files = [f for f in os.listdir(cwd) if f.lower().endswith('.db')]
    if not db_files:
        print("Inga .db-filer hittades i katalogen.")
        return

    for db in db_files:
        txt_name = os.path.splitext(db)[0] + '_detailed.txt'
        print(f"Bearbetar {db} → {txt_name}")
        extract_detailed_schema(
            os.path.join(cwd, db),
            os.path.join(cwd, txt_name)
        )

if __name__ == '__main__':
    main()