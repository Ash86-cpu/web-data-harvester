from pathlib import Path

import pytest
import requests

from harvester.fetch import Fetcher

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://books.toscrape.com/catalogue/"


def read(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, status=200, text=""):
        self.status_code = status
        self.text = text
        self.encoding = "utf-8"

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError(f"HTTP {self.status_code}")
            err.response = self
            raise err


class FakeSession:
    """Serves saved pages by URL. `script` maps a URL to a list of results
    returned in order (an int status, an exception, or page text)."""

    def __init__(self, pages=None, script=None):
        self.pages = pages or {}
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.headers = {}
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append(url)
        if self.script.get(url):
            item = self.script[url].pop(0)
            if isinstance(item, Exception):
                raise item
            if isinstance(item, int):
                return FakeResponse(item)
            return FakeResponse(200, item)
        if url in self.pages:
            return FakeResponse(200, self.pages[url])
        return FakeResponse(404)


@pytest.fixture
def site():
    """A two-page fake catalogue where every book link serves the saved book page."""
    from harvester.parse import parse_list

    p1, p2 = read("list_page_1.html"), read("list_page_50.html")
    url1, url2 = BASE + "page-1.html", BASE + "page-2.html"
    pages = {url1: p1, url2: p2}
    book = read("book.html")
    for html, url in ((p1, url1), (p2, url2)):
        for link in parse_list(html, url)[0]:
            pages[link] = book
    return pages


@pytest.fixture
def fetcher_for():
    def make(**kw):
        sleeps = []
        f = Fetcher(session=FakeSession(**kw), sleep=sleeps.append)
        f.sleeps = sleeps
        return f
    return make
