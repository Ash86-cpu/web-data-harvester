import requests

U = "https://example.test/page"


def test_success_first_try(fetcher_for):
    f = fetcher_for(pages={U: "ok"})
    assert f.get(U) == "ok"
    assert f.retry_count == 0 and f.failures == []


def test_retries_server_error_then_succeeds(fetcher_for):
    f = fetcher_for(script={U: [503, 500, "ok"]})
    assert f.get(U) == "ok"
    assert f.retry_count == 2
    assert f.sleeps == [1.0, 2.0]  # exponential backoff


def test_retries_network_error(fetcher_for):
    f = fetcher_for(script={U: [requests.ConnectionError("reset"), "ok"]})
    assert f.get(U) == "ok"
    assert f.retry_count == 1


def test_gives_up_after_all_retries(fetcher_for):
    f = fetcher_for(script={U: [503, 503, 503, 503]})
    assert f.get(U) is None
    assert f.failures == [U]
    assert f.retry_count == 3


def test_404_is_not_retried(fetcher_for):
    f = fetcher_for()
    assert f.get(U) is None
    assert f.retry_count == 0
    assert len(f.session.calls) == 1


def test_polite_delay_between_requests(fetcher_for):
    f = fetcher_for(pages={U: "a", U + "2": "b"})
    f.get(U)
    f.get(U + "2")
    assert f.sleeps == [0.5]  # no delay before the first request


def test_sends_identifying_user_agent(fetcher_for):
    f = fetcher_for()
    assert "web-data-harvester" in f.session.headers["User-Agent"]
