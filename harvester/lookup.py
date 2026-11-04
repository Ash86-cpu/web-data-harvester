"""The bot's main loop: for each number in the input list, search the site,
walk every results page, keep only the row whose number matches exactly,
open it and extract the record."""
from urllib.parse import urlencode

from .models import Lookup
from .parse import parse_record, parse_results


def normalise(value):
    """Compare numbers the way a person would: ignore case and spaces."""
    return "".join(value.split()).upper()


class LookupBot:
    def __init__(self, fetcher, base_url, max_pages=20):
        self.fetcher = fetcher
        self.base_url = base_url.rstrip("/")
        self.max_pages = max_pages

    def search_url(self, key, by):
        return f"{self.base_url}/search?{urlencode({'by': by, 'q': key})}"

    def lookup(self, key, by="parcel"):
        """Search for one number and return a Lookup with its outcome."""
        result = Lookup(key=key, by=by, status="NOT_FOUND")
        column = 0 if by == "parcel" else 1
        wanted = normalise(key)
        url = self.search_url(key, by)

        matches = []
        while url and result.pages < self.max_pages:
            html = self.fetcher.get(url)
            if html is None:
                result.status, result.detail = "ERROR", "search page failed after retries"
                return result
            rows, url = parse_results(html, url)
            result.pages += 1
            result.candidates += len(rows)
            # the site does a "starts with" search, so filter to the exact number
            matches += [row for row in rows if normalise(row[column]) == wanted]

        if not matches:
            result.detail = f"no exact match in {result.candidates} results"
            return result
        if len(matches) > 1:
            result.status = "ERROR"
            result.detail = f"{len(matches)} records share this {by} number"
            return result

        detail_url = matches[0][2]
        page = self.fetcher.get(detail_url)
        if page is None:
            result.status, result.detail = "ERROR", "record page failed after retries"
            return result
        record = parse_record(page, detail_url)
        # check the detail page really is the record we asked for
        if normalise(getattr(record, by)) != wanted:
            result.status = "ERROR"
            result.detail = f"detail page shows {getattr(record, by)!r}, not {key!r}"
            return result
        result.status, result.record = "MATCHED", record
        return result

    def run(self, keys, by="parcel"):
        """Look up every number, one at a time, and return all outcomes."""
        return [self.lookup(k, by) for k in keys]
