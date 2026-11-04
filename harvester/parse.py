"""Read the records site's search results and detail pages."""
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import Record


def _text(node):
    return node.get_text(strip=True) if node else ""


def parse_results(html, page_url):
    """Return ([(parcel, account, detail_url), ...], next_page_url or None)."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.select("table#results tr.result"):
        link = tr.select_one("a.view[href]")
        rows.append((_text(tr.select_one(".parcel")), _text(tr.select_one(".account")),
                     urljoin(page_url, link["href"]) if link else ""))
    nxt = soup.select_one("a.next[href]")
    return rows, (urljoin(page_url, nxt["href"]) if nxt else None)


def parse_record(html, url):
    """Return a Record from a detail page. Missing cells become ""."""
    soup = BeautifulSoup(html, "html.parser")
    get = lambda cid: _text(soup.select_one(f"table#record td#{cid}"))
    value = get("assessed").lstrip("£$€").replace(",", "")
    return Record(parcel=get("parcel"), account=get("account"), owner=get("owner"),
                  address=get("address"), assessed_value=value, tax_status=get("status"),
                  last_updated=get("updated"), source_url=url)
