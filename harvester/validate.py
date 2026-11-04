"""Data quality checks on stored records. One function per rule."""
import re
from datetime import date

from .models import Problem

REQUIRED = ("parcel", "account", "owner", "address", "assessed_value", "tax_status")
STATUSES = {"Paid", "Due", "Delinquent"}
PARCEL = re.compile(r"^P-\d{4,6}$")
ACCOUNT = re.compile(r"^A-\d{4,6}$")


def check_missing(records):
    return [Problem("MISSING", i, f"no {f.replace('_', ' ')}")
            for i, r in enumerate(records, 1) for f in REQUIRED
            if not getattr(r, f).strip()]


def check_formats(records):
    out = []
    for i, r in enumerate(records, 1):
        if r.parcel and not PARCEL.match(r.parcel):
            out.append(Problem("INVALID", i, f"parcel '{r.parcel}' is not in P-nnnn format"))
        if r.account and not ACCOUNT.match(r.account):
            out.append(Problem("INVALID", i, f"account '{r.account}' is not in A-nnnn format"))
    return out


def check_value(records):
    out = []
    for i, r in enumerate(records, 1):
        if not r.assessed_value:
            continue  # reported as missing
        try:
            if float(r.assessed_value) <= 0:
                out.append(Problem("INVALID", i, f"assessed value {r.assessed_value} is not positive"))
        except ValueError:
            out.append(Problem("INVALID", i, f"assessed value '{r.assessed_value}' is not a number"))
    return out


def check_status(records):
    return [Problem("INVALID", i, f"tax status '{r.tax_status}' is not one of Paid, Due, Delinquent")
            for i, r in enumerate(records, 1) if r.tax_status and r.tax_status not in STATUSES]


def check_date(records):
    out = []
    for i, r in enumerate(records, 1):
        try:
            if date.fromisoformat(r.last_updated) > date.today():
                out.append(Problem("INVALID", i, f"last updated {r.last_updated} is in the future"))
        except ValueError:
            out.append(Problem("INVALID", i, f"last updated '{r.last_updated}' is not a YYYY-MM-DD date"))
    return out


def check_duplicates(records):
    out, seen = [], {}
    for i, r in enumerate(records, 1):
        for field in ("parcel", "account"):
            v = getattr(r, field)
            if v and (field, v) in seen:
                out.append(Problem("DUPLICATE", i, f"same {field} {v} as record {seen[(field, v)]}"))
            elif v:
                seen[(field, v)] = i
    return out


CHECKS = (check_missing, check_formats, check_value, check_status, check_date, check_duplicates)


def validate(records):
    problems = [p for check in CHECKS for p in check(records)]
    return sorted(problems, key=lambda p: (p.record, p.kind))
