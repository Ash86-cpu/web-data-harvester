"""A small fake county property records site for the bot to work against.

It behaves like the lookup portals automation bots are usually pointed at:

- a search form that does a "starts with" match, so searching P-1012
  also returns P-10121 and P-10125 (the bot must pick the exact one)
- search results split across pages of 5 rows
- a detail page per record with the fields to extract
- search by parcel number or by account number

All data is generated and fictional.

Run it with:  python -m records_site            (http://127.0.0.1:5000)
"""
import random

from flask import Flask, abort, render_template_string, request

PAGE_SIZE = 5
STATUSES = ("Paid", "Due", "Delinquent")
STREETS = ("Oak Lane", "Mill Road", "Station Street", "Harbour View",
           "Church Walk", "Kings Avenue", "Bridge Close", "Elm Grove")
FIRST = ("Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Robin", "Jamie")
LAST = ("Archer", "Bennett", "Carter", "Dalton", "Ellis", "Fraser", "Grant", "Hughes")


def make_records(seed=7):
    """Deterministic fake records. Some parcel and account numbers share a
    prefix with another one, so a "starts with" search returns several rows."""
    rnd = random.Random(seed)
    records = []
    bases = list(range(1000, 1040))
    numbers = [str(b) for b in bases] + [f"{b}{d}" for b in bases[::4] for d in (1, 5)]
    for i, n in enumerate(numbers, 1):
        # ten accounts share the prefix A-2003 (A-20030..A-20039)
        acct = f"2003{i - 1}" if i <= 10 else str(30000 + i * 7)
        records.append({
            "id": i,
            "parcel": f"P-{n}",
            "account": f"A-{acct}",
            "owner": f"{rnd.choice(FIRST)} {rnd.choice(LAST)}",
            "address": f"{rnd.randint(1, 240)} {rnd.choice(STREETS)}, Westbury",
            "assessed": f"{rnd.randint(90, 650) * 1000:,}",
            "status": rnd.choice(STATUSES),
            "updated": f"2026-{rnd.randint(1, 10):02d}-{rnd.randint(1, 28):02d}",
        })
    # A-2003 itself, listed after the ten that share its prefix
    records.append({**records[3], "id": len(records) + 1, "parcel": "P-2001",
                    "account": "A-2003"})
    return records


LAYOUT = """<!doctype html><html><head><title>Westbury Property Records</title></head>
<body><h1>Westbury County Property Records</h1>{{ body|safe }}</body></html>"""

SEARCH = """
<form id="search" action="/search" method="get">
  <select name="by"><option value="parcel">Parcel number</option>
                    <option value="account">Account number</option></select>
  <input name="q" id="q"> <button type="submit">Search</button>
</form>
{% if q is not none %}
  <p class="summary">{{ total }} result(s) for "{{ q }}"</p>
  <table id="results"><tr><th>Parcel</th><th>Account</th><th>Owner</th><th></th></tr>
  {% for r in rows %}
    <tr class="result"><td class="parcel">{{ r.parcel }}</td><td class="account">{{ r.account }}</td>
        <td>{{ r.owner }}</td><td><a class="view" href="/record/{{ r.id }}">View</a></td></tr>
  {% endfor %}</table>
  {% if next_page %}<a class="next" href="/search?by={{ by }}&q={{ q }}&page={{ next_page }}">Next</a>{% endif %}
{% endif %}
"""

DETAIL = """
<table id="record">
  <tr><th>Parcel number</th><td id="parcel">{{ r.parcel }}</td></tr>
  <tr><th>Account number</th><td id="account">{{ r.account }}</td></tr>
  <tr><th>Owner</th><td id="owner">{{ r.owner }}</td></tr>
  <tr><th>Property address</th><td id="address">{{ r.address }}</td></tr>
  <tr><th>Assessed value</th><td id="assessed">&pound;{{ r.assessed }}</td></tr>
  <tr><th>Tax status</th><td id="status">{{ r.status }}</td></tr>
  <tr><th>Last updated</th><td id="updated">{{ r.updated }}</td></tr>
</table><a href="/">New search</a>
"""


def create_app(records=None):
    app = Flask(__name__)
    data = records if records is not None else make_records()
    by_id = {r["id"]: r for r in data}

    def page(body, **ctx):
        return render_template_string(LAYOUT, body=render_template_string(body, **ctx))

    @app.get("/")
    def home():
        return page(SEARCH, q=None)

    @app.get("/search")
    def search():
        by = request.args.get("by", "parcel")
        if by not in ("parcel", "account"):
            abort(400)
        q = request.args.get("q", "").strip().upper()
        pg = max(1, request.args.get("page", 1, type=int))
        hits = [r for r in data if q and r[by].upper().startswith(q)]
        rows = hits[(pg - 1) * PAGE_SIZE: pg * PAGE_SIZE]
        nxt = pg + 1 if pg * PAGE_SIZE < len(hits) else None
        return page(SEARCH, q=q, by=by, rows=rows, total=len(hits), next_page=nxt)

    @app.get("/record/<int:rid>")
    def record(rid):
        if rid not in by_id:
            abort(404)
        return page(DETAIL, r=by_id[rid])

    return app
