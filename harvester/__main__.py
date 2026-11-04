"""Command-line interface.

    python -m harvester run [--pages N] [--out DIR]
    python -m harvester validate PATH [--json]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from . import store
from .fetch import Fetcher
from .parse import parse_book, parse_list
from .validate import validate

START_URL = "https://books.toscrape.com/catalogue/page-1.html"


def harvest(fetcher, start_url=START_URL, pages=1):
    """Walk up to `pages` catalogue pages and return the parsed books."""
    books, url, done = [], start_url, 0
    while url and done < pages:
        html = fetcher.get(url)
        if html is None:
            break  # cannot find the next page without this one
        links, next_url = parse_list(html, url)
        for link in links:
            page = fetcher.get(link)
            if page is not None:
                books.append(parse_book(page, link))
        done += 1
        url = next_url
    return books, done


def cmd_run(args, fetcher=None):
    fetcher = fetcher or Fetcher(delay=args.delay)
    books, pages = harvest(fetcher, args.start, args.pages)
    out = Path(args.out)
    store.save_csv(books, out / "books.csv")
    store.save_sqlite(books, out / "books.db")
    print(f"Fetched {pages} pages, {len(books)} records "
          f"({fetcher.retry_count} retries, {len(fetcher.failures)} failures)")
    print(f"Saved: {(out / 'books.csv').as_posix()}, {(out / 'books.db').as_posix()}")
    return 0 if not fetcher.failures else 2


def cmd_validate(args):
    books = store.load(args.path)
    problems = validate(books)
    if args.json:
        print(json.dumps({"records": len(books),
                          "problems": [p.__dict__ for p in problems]}, indent=2))
    else:
        print(f"{len(books)} records checked, {len(problems)} problems")
        for p in problems:
            print("  " + str(p))
    return 1 if problems else 0


def build_parser():
    ap = argparse.ArgumentParser(prog="harvester",
                                 description="Collect book data and check its quality.")
    ap.add_argument("-v", "--verbose", action="store_true", help="log retries and failures")
    sub = ap.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="harvest catalogue pages")
    run.add_argument("--pages", type=int, default=1, help="catalogue pages to fetch (20 books each)")
    run.add_argument("--out", default="output", help="folder for books.csv and books.db")
    run.add_argument("--start", default=START_URL, help=argparse.SUPPRESS)
    run.add_argument("--delay", type=float, default=0.5, help="seconds between requests")

    val = sub.add_parser("validate", help="check a books.db or books.csv file")
    val.add_argument("path")
    val.add_argument("--json", action="store_true", help="machine-readable output")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(message)s")
    return cmd_run(args) if args.command == "run" else cmd_validate(args)


if __name__ == "__main__":
    sys.exit(main())
