"""Build a local SQLite dictionary from ECDICT's ecdict.csv.

Run:  .venv\\Scripts\\python.exe build_dict.py
"""
import csv
import sqlite3
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
CSV_PATH = BASE / "data" / "ecdict.csv"
DB_PATH = BASE / "data" / "ecdict.db"

csv.field_size_limit(10 * 1024 * 1024)


def main() -> None:
    if not CSV_PATH.exists():
        print(f"missing {CSV_PATH}")
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=OFF")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS ecdict (
            word TEXT PRIMARY KEY COLLATE NOCASE,
            phonetic TEXT,
            definition TEXT,
            translation TEXT,
            pos TEXT,
            collins TEXT,
            oxford TEXT,
            tag TEXT,
            bnc TEXT,
            frq TEXT,
            exchange TEXT
        )
        """
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS forms (form TEXT COLLATE NOCASE, lemma TEXT COLLATE NOCASE)"
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_forms_form ON forms(form COLLATE NOCASE)")

    existing = con.execute("SELECT COUNT(*) FROM ecdict").fetchone()[0]
    if existing > 700000:
        print(f"already built: {existing} entries")
        con.close()
        return

    started = time.time()
    rows = 0
    forms = 0
    batch = []
    form_batch = []

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            word = (row.get("word") or "").strip()
            if not word:
                continue
            batch.append(
                (
                    word,
                    row.get("phonetic") or "",
                    row.get("definition") or "",
                    row.get("translation") or "",
                    row.get("pos") or "",
                    row.get("collins") or "",
                    row.get("oxford") or "",
                    row.get("tag") or "",
                    row.get("bnc") or "",
                    row.get("frq") or "",
                    row.get("exchange") or "",
                )
            )
            rows += 1

            exchange = row.get("exchange") or ""
            for part in exchange.split("/"):
                if ":" not in part:
                    continue
                code, value = part.split(":", 1)
                value = value.strip().lower()
                if not value:
                    continue
                # p/d/i/3/r/t/s are inflections of this headword.
                if code in ("p", "d", "i", "3", "r", "t", "s"):
                    form_batch.append((value, word.lower()))
                    forms += 1
                # 1:lemma means this headword is an inflected form of lemma.
                elif code == "1":
                    form_batch.append((word.lower(), value))
                    forms += 1

            if len(batch) >= 5000:
                con.executemany(
                    "INSERT OR IGNORE INTO ecdict VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch
                )
                batch.clear()
            if len(form_batch) >= 20000:
                con.executemany("INSERT OR IGNORE INTO forms VALUES (?,?)", form_batch)
                form_batch.clear()
            if rows % 100000 == 0:
                print(f"  {rows:,} entries...", flush=True)

    if batch:
        con.executemany("INSERT OR IGNORE INTO ecdict VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch)
    if form_batch:
        con.executemany("INSERT OR IGNORE INTO forms VALUES (?,?)", form_batch)

    con.commit()
    con.execute("CREATE INDEX IF NOT EXISTS idx_ecdict_tag ON ecdict(tag)")
    con.commit()
    con.close()
    print(f"done: {rows:,} entries, {forms:,} forms, {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
