"""End-to-end: harvest from a fake site, save, reload, validate. No network."""
import json

from conftest import BASE, FakeSession

from harvester import store
from harvester.__main__ import build_parser, cmd_run, harvest, main
from harvester.fetch import Fetcher
from harvester.models import Book


def fake_fetcher(pages, **script):
    return Fetcher(session=FakeSession(pages=pages, script=script.get("script")),
                   sleep=lambda s: None)


def test_harvest_follows_next_link_and_stops_at_limit(site):
    books, pages = harvest(fake_fetcher(site), BASE + "page-1.html", pages=2)
    assert pages == 2
    assert len(books) == 40  # 20 per page


def test_harvest_stops_when_no_next_page(site):
    _, pages = harvest(fake_fetcher(site), BASE + "page-1.html", pages=10)
    assert pages == 2  # fixture page 2 is the last page


def test_failed_book_page_is_skipped_not_fatal(site):
    first = next(u for u in site if u.endswith("index.html"))
    f = fake_fetcher(site, script={first: [503] * 4})
    books, _ = harvest(f, BASE + "page-1.html", pages=1)
    assert len(books) == 19
    assert f.failures == [first]


def test_run_saves_csv_and_db_and_validate_finds_duplicates(site, tmp_path, capsys):
    args = build_parser().parse_args(
        ["run", "--pages", "1", "--out", str(tmp_path), "--start", BASE + "page-1.html"])
    assert cmd_run(args, fetcher=fake_fetcher(site)) == 0
    assert "Fetched 1 pages, 20 records (0 retries, 0 failures)" in capsys.readouterr().out
    assert len(store.load(tmp_path / "books.csv")) == 20

    # every fake book link serves the same page, so all 20 share one UPC
    code = main(["validate", str(tmp_path / "books.db")])
    out = capsys.readouterr().out
    assert code == 1
    assert "20 records checked, 19 problems" in out
    assert "[DUPLICATE]" in out


def test_validate_json_and_clean_exit_code(tmp_path, capsys):
    db = tmp_path / "ok.db"
    store.save_sqlite([Book("u1", "T", "1.00", "1", "5", "C", "http://x")], db)
    assert main(["validate", str(db), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"records": 1, "problems": []}


def test_sqlite_and_csv_round_trip(tmp_path):
    rows = [Book("u1", "T", "N/A", "", "3", "C", "http://x")]
    store.save_sqlite(rows, tmp_path / "b.db")
    store.save_csv(rows, tmp_path / "b.csv")
    assert store.load(tmp_path / "b.db") == rows
    assert store.load(tmp_path / "b.csv") == rows
