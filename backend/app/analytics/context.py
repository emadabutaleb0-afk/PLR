"""Loads the business tables into pandas once per refresh. All engines read from this context, never from CSV."""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.tables import TABLES

SALES_COLS = ["row_id", "invoice_id", "order_date", "month_key", "location_id", "channel", "customer_id", "customer_type",
              "product_id", "product_family", "size", "quantity", "list_price_egp", "discount_pct", "gross_sales_egp",
              "net_sales_egp", "estimated_cogs_egp", "gross_profit_egp", "returned", "return_date", "return_reason",
              "refund_value_egp", "quality_related_return"]


def _read(db: Session, name: str, cols=None) -> pd.DataFrame:
    t = TABLES[name]
    q = select(*[t.c[c] for c in cols]) if cols else select(t)
    df = pd.read_sql(q, db.connection())
    for c in df.columns:
        if t.c[c].type.python_type.__name__ == "date":
            df[c] = pd.to_datetime(df[c])
    return df


@dataclass
class Ctx:
    product: pd.DataFrame
    loc: pd.DataFrame
    sales: pd.DataFrame
    inv: pd.DataFrame
    mkt: pd.DataFrame
    qual: pd.DataFrame
    prod: pd.DataFrame
    prt: pd.DataFrame
    po: pd.DataFrame
    sup: pd.DataFrame
    mat: pd.DataFrame
    bom: pd.DataFrame
    cs: pd.DataFrame
    dt: pd.DataFrame
    web: pd.DataFrame
    ops: pd.DataFrame
    customers: pd.DataFrame
    as_of: pd.Timestamp          # last sales date
    inv_month: pd.Timestamp      # latest inventory snapshot month

    @property
    def available(self) -> dict:
        return {k: (len(getattr(self, k)) > 0) for k in
                ["product", "loc", "sales", "inv", "mkt", "qual", "prod", "prt", "po", "sup", "mat", "bom", "cs", "dt"]}


def load_ctx(db: Session) -> Ctx:
    sales = _read(db, "sales_transactions", SALES_COLS)
    sales["month"] = sales["order_date"].dt.to_period("M").dt.to_timestamp()
    inv = _read(db, "inventory_history")
    as_of = sales["order_date"].max() if len(sales) else pd.Timestamp.today().normalize()
    inv_month = inv["snapshot_month"].max() if len(inv) else as_of.to_period("M").to_timestamp()
    return Ctx(
        product=_read(db, "product_master"), loc=_read(db, "locations"), sales=sales, inv=inv,
        mkt=_read(db, "marketing"), qual=_read(db, "quality"), prod=_read(db, "production_orders"),
        prt=_read(db, "printing_batches"), po=_read(db, "purchase_orders"), sup=_read(db, "suppliers"),
        mat=_read(db, "materials"), bom=_read(db, "product_bom"), cs=_read(db, "customer_service"),
        dt=_read(db, "machine_downtime"), web=_read(db, "web_traffic_daily"), ops=_read(db, "group_operations"),
        customers=_read(db, "customers", ["customer_id", "customer_type", "governorate", "acquisition_channel", "join_date"]),
        as_of=as_of, inv_month=inv_month)
