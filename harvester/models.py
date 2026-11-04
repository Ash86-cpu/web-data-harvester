from dataclasses import asdict, dataclass, fields


@dataclass
class Book:
    """One product record. Fields are kept as parsed, so bad values from the
    page (for example a price that is not a number) survive to validation
    instead of being silently dropped."""

    upc: str
    title: str
    price: str
    stock: str
    rating: str
    category: str
    url: str

    def as_dict(self):
        return asdict(self)

    @classmethod
    def field_names(cls):
        return [f.name for f in fields(cls)]


@dataclass
class Problem:
    kind: str      # MISSING, INVALID or DUPLICATE
    record: int    # 1-based row number
    message: str

    def __str__(self):
        return f"[{self.kind}]".ljust(12) + f"record {self.record}: {self.message}"
