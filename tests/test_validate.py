from harvester.models import Record
from harvester.validate import validate


def rec(**kw):
    base = dict(parcel="P-1000", account="A-20037", owner="Alex Archer",
                address="1 Oak Lane", assessed_value="250000", tax_status="Paid",
                last_updated="2026-03-01", source_url="http://x")
    base.update(kw)
    return Record(**base)


def kinds(problems):
    return [(p.kind, p.record) for p in problems]


def test_clean_records():
    assert validate([rec(), rec(parcel="P-1001", account="A-20074")]) == []


def test_missing_field():
    p = validate([rec(owner="")])
    assert kinds(p) == [("MISSING", 1)] and "no owner" in p[0].message


def test_bad_number_formats():
    p = validate([rec(parcel="1000", account="ACC-1")])
    assert len(p) == 2 and all(x.kind == "INVALID" for x in p)


def test_assessed_value_must_be_positive_number():
    assert "not a number" in validate([rec(assessed_value="N/A")])[0].message
    assert "not positive" in validate([rec(assessed_value="0")])[0].message


def test_unknown_tax_status():
    assert "tax status" in validate([rec(tax_status="Overdue")])[0].message


def test_dates():
    assert "not a YYYY-MM-DD" in validate([rec(last_updated="03/01/2026")])[0].message
    assert "in the future" in validate([rec(last_updated="2999-01-01")])[0].message


def test_duplicates_point_to_first_record():
    p = validate([rec(), rec(account="A-20074"), rec(parcel="P-1001")])
    assert kinds(p) == [("DUPLICATE", 2), ("DUPLICATE", 3)]
    assert "record 1" in p[0].message
