from harvester.models import Book
from harvester.validate import validate


def book(**kw):
    base = dict(upc="u1", title="T", price="10.00", stock="3", rating="4",
                category="C", url="http://x")
    base.update(kw)
    return Book(**base)


def kinds(problems):
    return [(p.kind, p.record) for p in problems]


def test_clean_records_have_no_problems():
    assert validate([book(upc="a"), book(upc="b")]) == []


def test_missing_required_field():
    problems = validate([book(upc="")])
    assert kinds(problems) == [("MISSING", 1)]
    assert "no upc" in problems[0].message


def test_price_not_a_number():
    problems = validate([book(price="N/A")])
    assert kinds(problems) == [("INVALID", 1)]
    assert "not a number" in problems[0].message


def test_negative_price():
    assert "negative" in validate([book(price="-1")])[0].message


def test_empty_price_reported_once_as_missing():
    assert kinds(validate([book(price="")])) == [("MISSING", 1)]


def test_rating_out_of_range():
    for bad in ("0", "6", "", "three"):
        assert kinds(validate([book(rating=bad)])) == [("INVALID", 1)]


def test_stock_must_be_whole_and_not_negative():
    for bad in ("-2", "1.5", "", "lots"):
        assert kinds(validate([book(stock=bad)])) == [("INVALID", 1)]


def test_duplicate_upc_points_to_first_record():
    problems = validate([book(upc="a"), book(upc="b"), book(upc="a")])
    assert kinds(problems) == [("DUPLICATE", 3)]
    assert "record 1" in problems[0].message


def test_problems_sorted_by_record():
    problems = validate([book(upc="a"), book(price="x"), book(upc="a", rating="9")])
    assert [p.record for p in problems] == sorted(p.record for p in problems)
