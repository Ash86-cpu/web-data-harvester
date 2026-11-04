"""Turn HTML pages from books.toscrape.com into Book records."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import Book

RATINGS = {"One": "1", "Two": "2", "Three": "3", "Four": "4", "Five": "5"}


def parse_list(html, page_url):
    """Return (book_urls, next_page_url or None) for a catalogue page."""
    soup = BeautifulSoup(html, "html.parser")
    books = [urljoin(page_url, a["href"])
             for a in soup.select("article.product_pod h3 a[href]")]
    nxt = soup.select_one("li.next a[href]")
    return books, (urljoin(page_url, nxt["href"]) if nxt else None)


def _text(node):
    return node.get_text(strip=True) if node else ""


def parse_book(html, url):
    """Return a Book. Missing parts become empty strings for validation."""
    soup = BeautifulSoup(html, "html.parser")
    table = {_text(r.th): _text(r.td) for r in soup.select("table.table-striped tr")}

    price = _text(soup.select_one("div.product_main p.price_color"))
    price = re.sub(r"^[^\d\-]*", "", price) if re.search(r"\d", price) else price

    avail = table.get("Availability", "")
    m = re.search(r"\((\d+) available\)", avail)
    stock = m.group(1) if m else ("0" if "out of stock" in avail.lower() else "")

    rating = ""
    star = soup.select_one("div.product_main p.star-rating")
    if star:
        rating = next((RATINGS[c] for c in star.get("class", []) if c in RATINGS), "")

    crumbs = [_text(a) for a in soup.select("ul.breadcrumb li a")]
    category = crumbs[2] if len(crumbs) > 2 else ""

    return Book(
        upc=table.get("UPC", ""),
        title=_text(soup.select_one("div.product_main h1")),
        price=price,
        stock=stock,
        rating=rating,
        category=category,
        url=url,
    )
