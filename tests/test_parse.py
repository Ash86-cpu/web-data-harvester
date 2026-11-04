from conftest import BASE, read

from harvester.parse import parse_book, parse_list


def test_list_page_finds_20_books_and_next_link():
    books, nxt = parse_list(read("list_page_1.html"), BASE + "page-1.html")
    assert len(books) == 20
    assert books[0] == BASE + "a-light-in-the-attic_1000/index.html"
    assert nxt == BASE + "page-2.html"


def test_last_list_page_has_no_next_link():
    _, nxt = parse_list(read("list_page_50.html"), BASE + "page-50.html")
    assert nxt is None


def test_book_page_fields():
    b = parse_book(read("book.html"), "u")
    assert b.title == "A Light in the Attic"
    assert b.upc == "a897fe39b1053632"
    assert b.price == "51.77"
    assert b.stock == "22"
    assert b.rating == "3"
    assert b.category == "Poetry"


def test_missing_parts_become_empty_not_errors():
    b = parse_book("<html><body><p>nothing here</p></body></html>", "u")
    assert (b.upc, b.title, b.price, b.rating, b.category) == ("", "", "", "", "")


def test_out_of_stock_is_zero():
    html = read("book.html").replace("In stock (22 available)", "Out of stock")
    assert parse_book(html, "u").stock == "0"


def test_non_numeric_price_is_kept_for_validation():
    html = read("book.html").replace('<p class="price_color">£51.77</p>',
                                     '<p class="price_color">N/A</p>')
    assert parse_book(html, "u").price == "N/A"
