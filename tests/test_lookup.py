"""The search loop: pagination, exact matching, and every way a lookup can end."""
from conftest import SITE

from harvester.lookup import LookupBot, normalise
from records_site.app import make_records


def bot(site_fetcher, **kw):
    return LookupBot(site_fetcher(**kw), SITE)


def test_exact_match_among_prefix_results(site_fetcher):
    # "P-1012" also returns P-10121 and P-10125; only P-1012 must be kept
    r = bot(site_fetcher).lookup("P-1012")
    assert r.status == "MATCHED"
    assert r.record.parcel == "P-1012"
    assert r.candidates == 3


def test_walks_every_results_page(site_fetcher):
    # 11 accounts start with A-2003, 5 per page: the exact one is on page 3
    r = bot(site_fetcher).lookup("A-2003", by="account")
    assert r.status == "MATCHED"
    assert r.record.account == "A-2003"
    assert r.pages == 3
    assert r.candidates == 11


def test_not_found_when_only_partial_matches(site_fetcher):
    r = bot(site_fetcher).lookup("P-101")  # P-1010..P-1019 exist, P-101 does not
    assert r.status == "NOT_FOUND"
    assert "no exact match in" in r.detail


def test_not_found_when_no_results(site_fetcher):
    r = bot(site_fetcher).lookup("P-9999")
    assert (r.status, r.candidates) == ("NOT_FOUND", 0)


def test_match_ignores_case_and_spaces(site_fetcher):
    r = bot(site_fetcher).lookup(" p-1012 ")
    assert r.status == "MATCHED" and r.record.parcel == "P-1012"


def test_two_records_with_same_number_is_an_error(site_fetcher):
    recs = make_records()
    recs.append({**recs[0], "id": 999})
    r = bot(site_fetcher, records=recs).lookup(recs[0]["parcel"])
    assert r.status == "ERROR" and "share this parcel" in r.detail


def test_detail_page_that_does_not_match_is_an_error(site_fetcher):
    f = site_fetcher()
    LookupBot(f, SITE).lookup("P-1012")  # warm up to find the detail URL
    detail = next(u for u in f.session.calls if "/record/" in u)
    wrong = f.session.client.get("/record/1").get_data(as_text=True)
    f2 = site_fetcher(script={detail: [wrong]})
    r = LookupBot(f2, SITE).lookup("P-1012")
    assert r.status == "ERROR" and "detail page shows" in r.detail


def test_search_page_failure_is_an_error_not_a_crash(site_fetcher):
    b = bot(site_fetcher)
    url = b.search_url("P-1012", "parcel")
    b.fetcher.session.script[url] = [503] * 4
    r = b.lookup("P-1012")
    assert r.status == "ERROR" and "search page failed" in r.detail


def test_run_keeps_going_after_a_failure(site_fetcher):
    results = bot(site_fetcher).run(["P-1000", "P-9999", "P-1001"])
    assert [r.status for r in results] == ["MATCHED", "NOT_FOUND", "MATCHED"]


def test_extracts_all_fields(site_fetcher):
    rec = bot(site_fetcher).lookup("P-1000").record
    src = make_records()[0]
    assert rec.account == src["account"]
    assert rec.owner == src["owner"]
    assert rec.address == src["address"]
    assert rec.assessed_value == src["assessed"].replace(",", "")
    assert rec.tax_status == src["status"]
    assert rec.last_updated == src["updated"]


def test_normalise():
    assert normalise(" p - 10 12 ") == "P-1012"
