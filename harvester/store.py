"""Save and load records as CSV and SQLite."""
import csv
import sqlite3
from pathlib import Path

from .models import Book

COLUMNS = Book.field_names()


def save_csv(books, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for b in books:
            w.writerow(b.as_dict())


def save_sqlite(books, path):
    """Write all rows in one transaction. UPC is not a primary key on
    purpose: duplicates are a data problem for validate() to report, not
    something to hide by overwriting rows."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.execute("DROP TABLE IF EXISTS books")
        con.execute("CREATE TABLE books (row INTEGER PRIMARY KEY, "
                    + ", ".join(f"{c} TEXT" for c in COLUMNS) + ")")
        con.executemany(
            f"INSERT INTO books ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
            [tuple(b.as_dict()[c] for c in COLUMNS) for b in books])
    con.close()


def load(path):
    """Load records from a .db or .csv file, in their saved order."""
    path = Path(path)
    if path.suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            return [Book(**{c: row.get(c) or "" for c in COLUMNS}) for row in csv.DictReader(f)]
    con = sqlite3.connect(path)
    try:
        rows = con.execute(f"SELECT {', '.join(COLUMNS)} FROM books ORDER BY row").fetchall()
    finally:
        con.close()
    return [Book(*[v or "" for v in r]) for r in rows]
