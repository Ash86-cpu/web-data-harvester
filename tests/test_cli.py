"""End to end: input file -> lookups on the fake site -> database -> validate."""
from conftest import SITE

from harvester.__main__ import build_parser, cmd_run, main
from harvester.store import Database


def test_run_then_validate(site_fetcher, db_url, tmp_path, capsys):
    keys = tmp_path / "keys.csv"
    keys.write_text("number\nP-1012\nP-1000\nP-101\n", encoding="utf-8")
    export = tmp_path / "out.csv"
    args = build_parser().parse_args(["run", str(keys), "--site", SITE, "--db", db_url,
                                      "--export", str(export)])
    assert cmd_run(args, fetcher=site_fetcher()) == 0
    out = capsys.readouterr().out
    assert "3 numbers: 2 matched, 1 not found, 0 errors" in out
    assert "NOT_FOUND  P-101" in out

    db = Database(db_url)
    assert [r.parcel for r in db.records()] == ["P-1000", "P-1012"]
    db.close()
    assert export.read_text(encoding="utf-8").count("\n") == 3  # header + 2 rows

    assert main(["validate", "--db", db_url]) == 0
    assert "2 records checked, 0 problems" in capsys.readouterr().out


def test_errors_give_exit_code_2(site_fetcher, tmp_path):
    keys = tmp_path / "k.txt"
    keys.write_text("P-1000\n", encoding="utf-8")
    db = f"sqlite:///{(tmp_path / 'r.db').as_posix()}"
    f = site_fetcher()
    url = f"{SITE}/search?by=parcel&q=P-1000"
    f.session.script[url] = [503] * 4
    args = build_parser().parse_args(["run", str(keys), "--site", SITE, "--db", db])
    assert cmd_run(args, fetcher=f) == 2


def test_validate_csv_reports_problems(tmp_path, capsys):
    csv = tmp_path / "r.csv"
    csv.write_text("parcel,account,owner,address,assessed_value,tax_status,last_updated,source_url\n"
                   "P-1000,A-20037,Alex,1 Oak Lane,N/A,Paid,2026-03-01,x\n", encoding="utf-8")
    assert main(["validate", "--csv", str(csv)]) == 1
    assert "not a number" in capsys.readouterr().out
