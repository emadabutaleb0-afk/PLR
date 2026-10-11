"""Transactional loader. Replaces the tables of the files that are present; keeps untouched tables."""
from __future__ import annotations
import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.engine import Connection
from app.models.tables import TABLES
from app.ingestion.specs import FILES, LOAD_ORDER


def _records(df: pd.DataFrame, spec) -> list[dict]:
    out = df.copy()
    out.columns = [c.lower() for c in out.columns]
    for c, t in spec.cols.items():
        lc = c.lower()
        if t == "d":
            out[lc] = out[lc].dt.date
        if t == "i":
            out[lc] = out[lc].astype("Int64")
    out = out.astype(object).where(out.notna(), None)
    return out.to_dict("records")


def dependents(table: str) -> set[str]:
    """Tables that (transitively) reference `table` through a real FK."""
    res, frontier = set(), {table}
    while frontier:
        nxt = {s.table for s in FILES.values() for _, rt, _ in s.fks if rt in frontier} - res
        res |= nxt
        frontier = nxt
    return res


def load_tables(conn: Connection, frames: dict[str, pd.DataFrame]) -> dict:
    """frames: file name -> clean typed DataFrame. Replaces the tables of the files supplied (inside one transaction; FKs are deferred).
    Rows of tables that were NOT supplied but would be orphaned by a replaced parent are removed and reported."""
    present_tables = {FILES[f].table for f in frames}
    order_tables = [FILES[f].table for f in LOAD_ORDER]
    for t in reversed(order_tables):
        if t in present_tables:
            conn.execute(delete(TABLES[t]))
    loaded = {}
    for f in LOAD_ORDER:
        if f not in frames:
            continue
        spec = FILES[f]
        recs = _records(frames[f], spec)
        for i in range(0, len(recs), 20000):
            conn.execute(TABLES[spec.table].insert(), recs[i:i + 20000])
        loaded[f] = len(recs)
    orphans = {}
    for sp in FILES.values():
        if sp.table in present_tables:
            continue
        for col, rt, rc in sp.fks:
            if rt in present_tables:
                child, parent = TABLES[sp.table], TABLES[rt]
                res = conn.execute(delete(child).where(child.c[col.lower()].notin_(select(parent.c[rc.lower()]))))
                if res.rowcount:
                    orphans[sp.table] = orphans.get(sp.table, 0) + res.rowcount
    return {"loaded": loaded, "orphans_removed": orphans}


def existing_keys(conn: Connection, table: str, col: str) -> set:
    return {r[0] for r in conn.execute(select(TABLES[table].c[col.lower()]))}
