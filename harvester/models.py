from dataclasses import asdict, dataclass, fields


@dataclass
class Record:
    """One property record, as shown on the detail page. Values are kept as
    text exactly as the page shows them, so bad values reach validation
    instead of being silently fixed or dropped."""

    parcel: str
    account: str
    owner: str
    address: str
    assessed_value: str
    tax_status: str
    last_updated: str
    source_url: str

    def as_dict(self):
        return asdict(self)

    @classmethod
    def field_names(cls):
        return [f.name for f in fields(cls)]


@dataclass
class Lookup:
    """The outcome of searching for one number from the input list."""

    key: str            # the parcel or account number we searched for
    by: str             # "parcel" or "account"
    status: str         # MATCHED, NOT_FOUND or ERROR
    pages: int = 0      # result pages walked
    candidates: int = 0 # rows the site returned before exact matching
    record: Record = None
    detail: str = ""

    def __str__(self):
        if self.status == "MATCHED":
            r = self.record
            return (f"MATCHED    {self.key:<9} {r.account if self.by == 'parcel' else r.parcel:<9} "
                    f"{r.owner:<15} {r.tax_status:<10} ({self.candidates} "
                    f"result{'s' if self.candidates != 1 else ''}, "
                    f"{self.pages} page{'s' if self.pages != 1 else ''})")
        return f"{self.status:<10} {self.key:<9} {self.detail}"


@dataclass
class Problem:
    kind: str      # MISSING, INVALID or DUPLICATE
    record: int    # 1-based row number
    message: str

    def __str__(self):
        return f"[{self.kind}]".ljust(12) + f"record {self.record}: {self.message}"
