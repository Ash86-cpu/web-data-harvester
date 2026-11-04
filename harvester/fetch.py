"""Polite HTTP fetching with timeouts, retries and backoff."""
import logging
import time

import requests

log = logging.getLogger(__name__)

USER_AGENT = "web-data-harvester/1.0 (portfolio project; +https://github.com/Ash86-cpu)"


class Fetcher:
    """Fetches pages one at a time.

    - every request has a timeout, so one slow page cannot hang the run
    - network errors and 5xx/429 responses are retried with exponential
      backoff (1 s, 2 s, 4 s by default)
    - a fixed delay between requests keeps the load on the site low
    - a page that still fails is counted and skipped, not fatal
    """

    RETRY_STATUS = {429, 500, 502, 503, 504}

    def __init__(self, session=None, retries=3, backoff=1.0, delay=0.5,
                 timeout=10, sleep=time.sleep):
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)
        self.retries = retries
        self.backoff = backoff
        self.delay = delay
        self.timeout = timeout
        self.sleep = sleep
        self.retry_count = 0
        self.failures = []
        self._last = None

    def get(self, url):
        """Return the page text, or None if it failed after all retries."""
        if self._last is not None and self.delay:
            self.sleep(self.delay)
        self._last = url
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code in self.RETRY_STATUS:
                    raise requests.HTTPError(f"HTTP {resp.status_code}")
                resp.raise_for_status()
                resp.encoding = resp.encoding or "utf-8"
                if resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = "utf-8"  # the site is UTF-8 but omits charset
                return resp.text
            except requests.RequestException as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status is not None and status not in self.RETRY_STATUS:
                    log.warning("giving up on %s: HTTP %s", url, status)
                    break  # 404 and similar will not fix themselves
                if attempt == self.retries:
                    log.warning("giving up on %s after %d attempts: %s",
                                url, attempt + 1, exc)
                    break
                wait = self.backoff * (2 ** attempt)
                log.info("retrying %s in %.0fs (%s)", url, wait, exc)
                self.retry_count += 1
                self.sleep(wait)
        self.failures.append(url)
        return None
