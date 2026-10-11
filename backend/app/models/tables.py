"""Business tables generated from ingestion specs (typed columns, real PK/FK, indexes).
Column names are lower-cased CSV headers (Product_ID -> product_id)."""
from sqlalchemy import Table, Column, String, Integer, Float, Date, Boolean, ForeignKey, Index, PrimaryKeyConstraint
from app.db.session import Base
from app.ingestion.specs import FILES, LOAD_ORDER

_T = {"s": String(255), "i": Integer, "f": Float, "d": Date, "yn": Boolean}
TABLES: dict[str, Table] = {}

for fname in LOAD_ORDER:
    sp = FILES[fname]
    fk = {c: (rt, rc) for c, rt, rc in sp.fks}
    cols = []
    for c, t in sp.cols.items():
        args = [_T[t]]
        if c in fk:
            args.append(ForeignKey(f"{fk[c][0]}.{fk[c][1].lower()}", deferrable=True, initially="DEFERRED"))   # deferred: parents can be replaced inside one transaction
        cols.append(Column(c.lower(), *args, nullable=c not in sp.required and c not in sp.pk))
    tbl = Table(sp.table, Base.metadata, *cols, PrimaryKeyConstraint(*[p.lower() for p in sp.pk]))
    for ic in sp.index:
        Index(f"ix_{sp.table}_{ic.lower()}", tbl.c[ic.lower()])
    TABLES[sp.table] = tbl
