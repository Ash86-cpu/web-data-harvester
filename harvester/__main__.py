"""Command-line interface.

    python -m harvester run INPUT [--by parcel|account] [--site URL] [--db URL] [--export CSV]
    python -m harvester validate (--db URL | CSV) [--json]
"""
import argparse
import json
import logging
import os
import sys

from . import store
from .fetch import Fetcher
from .lookup import LookupBot
from .validate import validate

DEFAULT_SITE = "http://127.0.0.1:5000"
DEFAULT_DB = os.environ.get("HARVESTER_DB", "sqlite:///output/records.db")


def cmd_run(args, fetcher=None):
    keys = store.read_keys(args.input)
    bot = LookupBot(fetcher or Fetcher(delay=args.delay), args.site)
    results = bot.run(keys, by=args.by)

    for r in results:
        print(str(r))
    matched = sum(r.status == "MATCHED" for r in results)
    not_found = sum(r.status == "NOT_FOUND" for r in results)
    errors = sum(r.status == "ERROR" for r in results)
    print(f"\n{len(keys)} numbers: {matched} matched, {not_found} not found, {errors} errors")

    db = store.Database(args.db)
    try:
        db.save(results)
        if args.export:
            store.export_csv(db.records(), args.export)
    finally:
        db.close()
    print(f"Saved {matched} records and {len(results)} log rows to {args.db.split('@')[-1]}")
    return 0 if errors == 0 else 2


def cmd_validate(args):
    if args.csv:
        records = store.load_csv(args.csv)
    else:
        db = store.Database(args.db)
        records = db.records()
        db.close()
    problems = validate(records)
    if args.json:
        print(json.dumps({"records": len(records), "problems": [p.__dict__ for p in problems]}, indent=2))
    else:
        print(f"{len(records)} records checked, {len(problems)} problems")
        for p in problems:
            print("  " + str(p))
    return 1 if problems else 0


def build_parser():
    ap = argparse.ArgumentParser(prog="harvester", description=(
        "Look up parcel or account numbers on a records site, keep exact matches, "
        "store them in MySQL or SQLite, and check data quality."))
    ap.add_argument("-v", "--verbose", action="store_true", help="log retries and failures")
    sub = ap.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="look up every number in an input file")
    run.add_argument("input", help="CSV with a 'number' column, or one number per line")
    run.add_argument("--by", choices=("parcel", "account"), default="parcel")
    run.add_argument("--site", default=DEFAULT_SITE, help=f"records site (default {DEFAULT_SITE})")
    run.add_argument("--db", default=DEFAULT_DB, help="mysql://user:pass@host/db or sqlite:///path")
    run.add_argument("--export", help="also write the stored records to this CSV")
    run.add_argument("--delay", type=float, default=0.2, help="seconds between requests")

    val = sub.add_parser("validate", help="check stored records")
    src = val.add_mutually_exclusive_group()
    src.add_argument("--db", default=DEFAULT_DB)
    src.add_argument("--csv", help="check a CSV export instead of the database")
    val.add_argument("--json", action="store_true")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(message)s")
    return cmd_run(args) if args.command == "run" else cmd_validate(args)


if __name__ == "__main__":
    sys.exit(main())
