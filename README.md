# web-data-harvester

[![tests](https://github.com/Ash86-cpu/web-data-harvester/actions/workflows/tests.yml/badge.svg)](https://github.com/Ash86-cpu/web-data-harvester/actions/workflows/tests.yml)

![Example run](docs/demo.gif)

A Python data-harvesting bot that takes a list of parcel or account numbers,
looks each one up on a records website, loops through the search results to
find the exact match, extracts the record and stores it in **MySQL**.

At work I build this kind of robot in **Kofax Design Studio**: a loop over
input numbers, a search form, a loop over result rows and pages, a match
condition, data extraction and a database write. This repository rebuilds
the same workflow in open-source Python, so it can be read, run and tested
by anyone without a Kofax licence.

| Kofax robot step | Here |
|---|---|
| Loop over input rows (Excel/CSV variable list) | `store.read_keys()` and `LookupBot.run()` |
| Enter number in search field, click Search | `LookupBot.search_url()` and `Fetcher.get()` |
| Loop over result rows, click Next until no more pages | the `while url` loop in `LookupBot.lookup()` |
| Test tag: does this row's number equal the input? | exact match with `normalise()` |
| Click the matching row, extract fields | `parse_record()` |
| Store in database (MySQL action) | `Database.save()` |
| Try-catch / error branch, log and continue | `Lookup.status` and the `lookup_log` table |

## The records site

The repo includes a small fake **county property records site**
(`records_site/`, a Flask app with generated, fictional data) so there is
something realistic to automate:

- search by parcel number or account number
- the search is "starts with", so `P-1012` also returns `P-10121` and
  `P-10125`, and the bot has to pick the exact one
- results come 5 per page with a **Next** link
- each record has a detail page with owner, address, assessed value, tax
  status and last-updated date

## Quick start

Requires Python 3.10+.

```
git clone https://github.com/Ash86-cpu/web-data-harvester.git
cd web-data-harvester
pip install -r requirements.txt

python -m records_site                 # terminal 1: site on http://127.0.0.1:5000

python -m harvester run samples/parcels.csv                        # terminal 2
python -m harvester run samples/accounts.txt --by account
python -m harvester validate
```

By default records go to SQLite (`output/records.db`) so it runs with no
setup. To use MySQL:

```
python -m harvester run samples/parcels.csv --db mysql://user:password@localhost:3306/records
```

or set `HARVESTER_DB` to the same URL.

## Example output

```
$ python -m harvester run samples/parcels.csv
MATCHED    P-1012    A-30091   Jamie Ellis     Paid       (3 results, 1 page)
MATCHED    P-1000    A-20030   Casey Carter    Delinquent (3 results, 1 page)
MATCHED    P-1027    A-30196   Morgan Fraser   Paid       (1 result, 1 page)
NOT_FOUND  P-101     no exact match in 14 results
MATCHED    P-1036    A-30259   Jordan Archer   Delinquent (3 results, 1 page)
NOT_FOUND  P-9999    no exact match in 0 results

6 numbers: 4 matched, 2 not found, 0 errors
Saved 4 records and 6 log rows to sqlite:///output/records.db

$ python -m harvester run samples/accounts.txt --by account
MATCHED    A-2003    P-2001    Robin Archer    Due        (11 results, 3 pages)
MATCHED    A-20035   P-1005    Taylor Fraser   Delinquent (1 result, 1 page)

2 numbers: 2 matched, 0 not found, 0 errors
Saved 2 records and 2 log rows to sqlite:///output/records.db

$ python -m harvester validate
6 records checked, 0 problems
```

`P-101` shows why exact matching matters: 14 parcels start with `P-101`, but
none of them is `P-101`. `A-2003` is on the third page of 11 results.

## Database

Two tables, created on first run (same SQL on MySQL and SQLite):

| Table | Contents |
|---|---|
| `property_records` | One row per matched record, keyed by parcel number. Re-running updates the row (MySQL `ON DUPLICATE KEY UPDATE`) instead of creating a duplicate. |
| `lookup_log` | One row per input number with its outcome (MATCHED, NOT_FOUND, ERROR), the reason, pages walked and time, so nothing fails silently. |

Each run is saved in one transaction: if any write fails, the whole batch is
rolled back.

## Options

| Command | Option | Meaning |
|---|---|---|
| `run` | `INPUT` | CSV with a `number` column, or one number per line |
| | `--by parcel\|account` | Which number the input contains (default parcel) |
| | `--site URL` | Records site (default http://127.0.0.1:5000) |
| | `--db URL` | `mysql://user:pass@host:3306/db` or `sqlite:///path` |
| | `--export CSV` | Also write the stored records to a CSV |
| | `--delay S` | Seconds between requests (default 0.2) |
| `validate` | `--db URL` or `--csv PATH` | Check stored records or a CSV export |
| | `--json` | Machine-readable output |

Exit codes: `run` returns 2 if any lookup ended in ERROR. `validate`
returns 1 if it found problems.

## How it works

| File | Responsibility |
|---|---|
| `harvester/lookup.py` | The bot loop: search, walk result pages, exact match, open record, confirm it |
| `harvester/fetch.py` | HTTP with timeouts, retries with exponential backoff, polite delay |
| `harvester/parse.py` | Read result rows, the Next link and detail pages with BeautifulSoup |
| `harvester/store.py` | MySQL / SQLite storage, upsert, lookup log, CSV input and export |
| `harvester/validate.py` | Data quality checks, one function per rule |
| `records_site/app.py` | The fake records site |

Design decisions:

- **Never trust a partial match.** The site's search is "starts with", so
  every result row is compared to the input exactly (ignoring case and
  spaces). If two rows share the number, that is reported as an error
  rather than guessing.
- **Check the record you landed on.** After opening the detail page, the bot
  confirms its parcel or account number is the one it searched for.
- **One bad lookup does not stop the run.** Every number gets an outcome in
  `lookup_log`; failures are retried (1 s, 2 s, 4 s) and then logged.
- **Re-runs are safe.** Upserting by parcel number means running the same
  list twice updates rows instead of duplicating them.
- **Validate before anyone relies on the data.** Missing fields, bad number
  formats, non-numeric values, unknown tax statuses, bad or future dates and
  duplicate numbers are reported, with a non-zero exit code.

## Tests

```
pip install -r requirements-dev.txt
python -m pytest -v
```

33 tests cover the lookup loop (prefix results, pagination to page 3, not
found, duplicates on the site, a detail page that does not match, failed
pages), retries and backoff, every validation rule, storage (upsert, lookup
log, rollback) and an end-to-end run from input file to database. Tests run
the records site in-process, so no server or network is needed.

On GitHub Actions the storage and end-to-end tests run against both SQLite
and a **real MySQL 8 server**, followed by a live run of the bot against
the records site writing to MySQL.

## Limitations

- `parse.py` is written for this records site's HTML; a different site
  needs its own selectors.
- Lookups run one at a time. That is deliberate (polite, easy to follow),
  but a large list would want a bounded worker pool.
- It uses plain HTTP requests, so it does not run JavaScript. Sites that
  build pages in the browser need a browser automation tool, which is where
  a Kofax robot's built-in browser is used at work.

## License

MIT
