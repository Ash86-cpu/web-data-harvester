"""Data quality checks. Each check looks at one rule and returns Problems."""
from .models import Problem

REQUIRED = ("upc", "title", "price", "url")


def check_missing(books):
    return [Problem("MISSING", i, f"no {field}")
            for i, b in enumerate(books, 1)
            for field in REQUIRED if not getattr(b, field).strip()]


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def check_price(books):
    out = []
    for i, b in enumerate(books, 1):
        if not b.price.strip():
            continue  # reported by check_missing
        p = _number(b.price)
        if p is None:
            out.append(Problem("INVALID", i, f"price '{b.price}' is not a number"))
        elif p < 0:
            out.append(Problem("INVALID", i, f"price {b.price} is negative"))
    return out


def check_rating(books):
    return [Problem("INVALID", i, f"rating '{b.rating}' is not 1 to 5")
            for i, b in enumerate(books, 1)
            if b.rating not in {"1", "2", "3", "4", "5"}]


def check_stock(books):
    out = []
    for i, b in enumerate(books, 1):
        s = _number(b.stock)
        if s is None or s < 0 or s != int(s):
            out.append(Problem("INVALID", i, f"stock '{b.stock}' is not a whole number of 0 or more"))
    return out


def check_duplicates(books):
    seen, out = {}, []
    for i, b in enumerate(books, 1):
        key = b.upc.strip()
        if not key:
            continue
        if key in seen:
            out.append(Problem("DUPLICATE", i, f"same UPC {key} as record {seen[key]}"))
        else:
            seen[key] = i
    return out


CHECKS = (check_missing, check_price, check_rating, check_stock, check_duplicates)


def validate(books):
    """Run every check and return the problems sorted by record."""
    problems = [p for check in CHECKS for p in check(books)]
    return sorted(problems, key=lambda p: (p.record, p.kind))
