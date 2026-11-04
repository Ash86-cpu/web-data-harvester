import os
from urllib.parse import urlsplit

import pytest
import requests

from harvester.fetch import Fetcher
from records_site.app import create_app

SITE = "http://records.test"


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
    """`script` maps a URL to results returned in order (status int,
    exception, or page text); anything else falls through to `app`."""

    def __init__(self, pages=None, script=None, app=None):
        self.pages = pages or {}
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.client = app.test_client() if app else None
        self.headers = {}
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append(url)
        if self.script.get(url):
            item = self.script[url].pop(0)
            if isinstance(item, Exception):
                raise item
            return FakeResponse(item) if isinstance(item, int) else FakeResponse(200, item)
        if url in self.pages:
            return FakeResponse(200, self.pages[url])
        if self.client:
            parts = urlsplit(url)
            r = self.client.get(parts.path + ("?" + parts.query if parts.query else ""))
            return FakeResponse(r.status_code, r.get_data(as_text=True))
        return FakeResponse(404)


@pytest.fixture
def fetcher_for():
    def make(**kw):
        sleeps = []
        f = Fetcher(session=FakeSession(**kw), sleep=sleeps.append)
        f.sleeps = sleeps
        return f
    return make


@pytest.fixture
def site_fetcher():
    """A Fetcher wired to the fake records site, running in-process."""
    def make(records=None, script=None):
        return Fetcher(session=FakeSession(app=create_app(records), script=script),
                       sleep=lambda s: None)
    return make


DB_URLS = ["sqlite"]
if os.environ.get("MYSQL_URL"):
    DB_URLS.append("mysql")


@pytest.fixture(params=DB_URLS)
def db_url(request, tmp_path):
    """Every storage test runs on SQLite, and on MySQL too when MYSQL_URL is set (CI)."""
    if request.param == "sqlite":
        return f"sqlite:///{(tmp_path / 'r.db').as_posix()}"
    import pymysql
    url = os.environ["MYSQL_URL"]
    from harvester.store import Database
    db = Database(url)
    db.execute("DROP TABLE IF EXISTS property_records")
    db.execute("DROP TABLE IF EXISTS lookup_log")
    db.con.commit()
    db.close()
    return url
