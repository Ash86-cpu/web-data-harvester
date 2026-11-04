"""Store matched records and a log of every lookup in MySQL (or SQLite).

    mysql://user:password@host:3306/dbname
    sqlite:///output/records.db

Matched records are upserted by parcel number, so re-running the same
input list updates rows instead of creating duplicates. Every lookup, matched
or not, is written to lookup_log so nothing is lost silently.
"""
import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from .models import Record

COLUMNS = Record.field_names()


class Database:
    def __init__(self, url):
        u = urlparse(url)
        self.kind = u.scheme
        if u.scheme == "sqlite":
            path = Path(u.path.lstrip("/") if u.netloc == "" else u.netloc + u.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.con = sqlite3.connect(path)
            self.ph = "?"
        elif u.scheme == "mysql":
            import pymysql  # only needed when MySQL is used
            self.con = pymysql.connect(
                host=u.hostname or "localhost", port=u.port or 3306,
                user=unquote(u.username or "root"), password=unquote(u.password or ""),
                database=u.path.lstrip("/"), charset="utf8mb4", autocommit=False)
            self.ph = "%s"
        else:
            raise ValueError(f"unsupported database URL: {url!r} (use mysql:// or sqlite:///)")
        self.create_tables()

    def execute(self, sql, params=()):
        cur = self.con.cursor()
        cur.execute(sql.replace("?", self.ph), params)
        return cur

    def create_tables(self):
        cols = ", ".join(f"{c} VARCHAR(255)" for c in COLUMNS if c != "parcel")
        self.execute(f"CREATE TABLE IF NOT EXISTS property_records ("
                     f"parcel VARCHAR(32) NOT NULL PRIMARY KEY,{cols}, fetched_at VARCHAR(32))")
        self.execute("CREATE TABLE IF NOT EXISTS lookup_log ("
                     "lookup_key VARCHAR(64), search_by VARCHAR(16), status VARCHAR(16), "
                     "detail VARCHAR(255), pages INTEGER, logged_at VARCHAR(32))")
        self.con.commit()

    def save(self, lookups):
        """Write one run's results in a single transaction."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cols = COLUMNS + ["fetched_at"]
        marks = ", ".join("?" * len(cols))
        updates = [c for c in cols if c != "parcel"]
        if self.kind == "mysql":
            upsert = (f"INSERT INTO property_records ({', '.join(cols)}) VALUES ({marks}) "
                      "ON DUPLICATE KEY UPDATE " + ", ".join(f"{c}=VALUES({c})" for c in updates))
        else:
            upsert = (f"INSERT INTO property_records ({', '.join(cols)}) VALUES ({marks}) "
                      "ON CONFLICT(parcel) DO UPDATE SET " + ", ".join(f"{c}=excluded.{c}" for c in updates))
        try:
            for lk in lookups:
                if lk.record is not None:
                    row = lk.record.as_dict()
                    self.execute(upsert, [row[c] for c in COLUMNS] + [now])
                self.execute("INSERT INTO lookup_log VALUES (?, ?, ?, ?, ?, ?)",
                             (lk.key, lk.by, lk.status, lk.detail[:255], lk.pages, now))
            self.con.commit()
        except Exception:
            self.con.rollback()
            raise

    def records(self):
        rows = self.execute(f"SELECT {', '.join(COLUMNS)} FROM property_records ORDER BY parcel").fetchall()
        return [Record(*[v or "" for v in r]) for r in rows]

    def close(self):
        self.con.close()


def read_keys(path):
    """Read the numbers to look up: a CSV with a 'number' column, or one per line."""
    text = Path(path).read_text(encoding="utf-8-sig").splitlines()
    if text and text[0].strip().lower() == "number":
        return [r["number"].strip() for r in csv.DictReader(text) if r["number"].strip()]
    return [line.strip() for line in text if line.strip() and not line.startswith("#")]


def export_csv(records, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in records:
            w.writerow(r.as_dict())


def load_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return [Record(**{c: row.get(c) or "" for c in COLUMNS}) for row in csv.DictReader(f)]
