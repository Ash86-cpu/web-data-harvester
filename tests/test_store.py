"""Storage. Each test runs on SQLite, and on MySQL as well in CI."""
from harvester.models import Lookup, Record
from harvester.store import Database, read_keys


def rec(parcel="P-1000", owner="Alex Archer"):
    return Record(parcel, "A-20037", owner, "1 Oak Lane, Westbury", "250000",
                  "Paid", "2026-03-01", "http://x/record/1")


def matched(r):
    return Lookup(key=r.parcel, by="parcel", status="MATCHED", pages=1, record=r)


def test_saves_matches_and_logs_every_lookup(db_url):
    db = Database(db_url)
    db.save([matched(rec()), Lookup("P-9999", "parcel", "NOT_FOUND", detail="none")])
    assert db.records() == [rec()]
    log = db.execute("SELECT lookup_key, status FROM lookup_log ORDER BY lookup_key").fetchall()
    assert [tuple(r) for r in log] == [("P-1000", "MATCHED"), ("P-9999", "NOT_FOUND")]
    db.close()


def test_rerun_updates_instead_of_duplicating(db_url):
    db = Database(db_url)
    db.save([matched(rec())])
    db.save([matched(rec(owner="Sam Bennett"))])
    rows = db.records()
    assert len(rows) == 1 and rows[0].owner == "Sam Bennett"
    db.close()


def test_failed_batch_is_rolled_back(db_url):
    db = Database(db_url)
    bad = matched(rec())
    bad.record = rec(parcel=None)  # NOT NULL primary key violation
    try:
        db.save([matched(rec("P-1001")), bad])
    except Exception:
        pass
    assert db.records() == []
    db.close()


def test_read_keys_csv_and_plain(tmp_path):
    (tmp_path / "a.csv").write_text("number\nP-1000\n\nP-1001\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("# comment\nP-1000\nP-1001\n", encoding="utf-8")
    assert read_keys(tmp_path / "a.csv") == ["P-1000", "P-1001"]
    assert read_keys(tmp_path / "b.txt") == ["P-1000", "P-1001"]


def test_rejects_unknown_database_url():
    try:
        Database("postgres://x")
    except ValueError as e:
        assert "unsupported" in str(e)
    else:
        raise AssertionError("expected ValueError")
