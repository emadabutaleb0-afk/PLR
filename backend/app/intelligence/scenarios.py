"""17. WHAT-IF SCENARIOS - three questions an owner actually asks, answered from the company's own numbers:
  discount       "What if I change the discount on this product in this channel?"
  extra_stock    "What if I produce / order N more units of this product?"
  material_price "What if a material gets X% more expensive?"
Every result lists its assumptions. Nothing here is a forecast of the future beyond the demand pace the forecasting engine already produced."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.features import window
from app.intelligence.common import num, clean

HORIZON_DAYS = 90
KINDS = ("discount", "extra_stock", "material_price")


def scenario_base(c, f: dict, pl: pd.DataFrame, cfg) -> dict:
    end = c.as_of
    s = window(c.sales, "order_date", end, 180)
    lv = s.assign(lv=s.list_price_egp * s.quantity).groupby(["product_id", "channel"]).agg(lv=("lv", "sum"), u=("quantity", "sum"), net=("net_sales_egp", "sum")).reset_index()
    lv["list_unit"] = lv.lv / lv.u.replace(0, np.nan)
    lv["avg_discount"] = 1 - lv.net / lv.lv.replace(0, np.nan)
    x = pl.merge(lv[["product_id", "channel", "list_unit", "avg_discount"]], on=["product_id", "channel"], how="left")
    daily = np.where(x.forecast_daily.fillna(0) > 0, x.forecast_daily, x.vel.fillna(0))
    x = x.assign(daily=daily)
    products = {}
    for pid, g in x.groupby("product_id"):
        products[pid] = dict(product_id=pid, product_name=g.product_name.iloc[0], channels=[dict(
            channel=r.channel, daily=float(r.daily), stock=float(r.closing_stock or 0), safety=float(r.safety_stock_units or 0), lead=float(r.supplier_lead_time_days if pd.notna(r.supplier_lead_time_days) else 7),
            net_unit=float(r.net_unit) if pd.notna(r.net_unit) else None, cogs_unit=float(r.cogs_unit) if pd.notna(r.cogs_unit) else None, gp_unit=float(r.gp_unit) if pd.notna(r.gp_unit) else 0.0,
            list_unit=float(r.list_unit) if pd.notna(r.list_unit) else None, avg_discount=float(r.avg_discount) if pd.notna(r.avg_discount) else None) for r in g.itertuples()])
    po = c.po.copy()
    po["sp"] = po.ordered_qty * po.unit_cost_egp
    mcost = (po.groupby("material_id").sp.sum() / po.groupby("material_id").ordered_qty.sum().replace(0, np.nan)).fillna(0)
    mats = c.mat.set_index("material_id")
    materials = [dict(material_id=m, material_name=mats.material_name.get(m, m), unit=mats.unit.get(m, ""), unit_cost=float(v)) for m, v in mcost.items() if m in mats.index]
    bom: dict = {}
    for r in c.bom.itertuples():
        bom.setdefault(r.product_id, []).append(dict(material_id=r.material_id, req=float(r.required_per_unit), cost_unit=float(r.required_per_unit * mcost.get(r.material_id, 0))))
    return clean(dict(products=products, materials=materials, bom=bom, params=dict(target_cover_days=cfg.target_cover_days, capital_cost_annual_pct=cfg.capital_cost_annual_pct, margin_floor_pct=cfg.margin_floor_pct, horizon_days=HORIZON_DAYS)))


def options(base: dict) -> dict:
    prods = [dict(product_id=p["product_id"], product_name=p["product_name"], channels=[dict(channel=ch["channel"], avg_discount=ch["avg_discount"], gp_unit=ch["gp_unit"]) for ch in p["channels"]])
             for p in sorted(base["products"].values(), key=lambda p: p["product_name"])]
    return dict(products=prods, materials=sorted(base["materials"], key=lambda m: m["material_name"]), horizon_days=base["params"]["horizon_days"])


def _prod(base, pid):
    p = base["products"].get(pid)
    if not p:
        raise ValueError("Unknown product.")
    return p


def _discount(base, product_id, channel, new_discount, lift_per_5pp=0.0, **_):
    p = _prod(base, product_id)
    ch = next((x for x in p["channels"] if x["channel"] == channel), None)
    if ch is None or ch["list_unit"] is None or ch["cogs_unit"] is None or ch["avg_discount"] is None:
        raise ValueError("This product has no recent sales in that channel, so the discount cannot be simulated.")
    if new_discount is None or not 0 <= new_discount <= 0.6:
        raise ValueError("Discount must be between 0% and 60%.")
    d0, d1 = ch["avg_discount"], float(new_discount)
    units0 = ch["daily"] * base["params"]["horizon_days"]
    net0, net1 = ch["list_unit"] * (1 - d0), ch["list_unit"] * (1 - d1)
    gp0, gp1 = net0 - ch["cogs_unit"], net1 - ch["cogs_unit"]
    units1 = units0 * max(0.0, 1 + lift_per_5pp * (d1 - d0) / 0.05)
    b = dict(discount=d0, units=units0, revenue=units0 * net0, gross_profit=units0 * gp0, margin=gp0 / net0 if net0 else None)
    a = dict(discount=d1, units=units1, revenue=units1 * net1, gross_profit=units1 * gp1, margin=gp1 / net1 if net1 else None)
    be = (gp0 / gp1 - 1) if gp1 > 0 else None
    warn = []
    if a["margin"] is not None and a["margin"] < base["params"]["margin_floor_pct"]:
        warn.append("margin_below_floor")
    return dict(kind="discount", title=f"{p['product_name']} / {channel}", before=b, after=a, delta=dict(units=a["units"] - b["units"], revenue=a["revenue"] - b["revenue"], gross_profit=a["gross_profit"] - b["gross_profit"]),
                breakeven_volume_change=be, warnings=warn,
                assumptions=["Demand follows the forecast pace for the next 90 days.", f"Volume change assumed: {lift_per_5pp:+.0%} per 5 points of discount (the data shows no measurable lift, so 0% is the supported default).", "Unit cost stays the same."])


def _extra_stock(base, product_id, extra_units, **_):
    p = _prod(base, product_id)
    if extra_units is None or extra_units <= 0:
        raise ValueError("Enter a number of units above zero.")
    H = max(base["params"]["target_cover_days"], max(ch["lead"] for ch in p["channels"]) + 14)
    rows = []
    for ch in p["channels"]:
        deficit = max(ch["daily"] * H + ch["safety"] - ch["stock"], 0.0)
        rows.append(dict(channel=ch["channel"], deficit=deficit, gp_unit=ch["gp_unit"], cogs_unit=ch["cogs_unit"] or 0.0))
    left, placed = float(extra_units), 0.0
    gain = 0.0
    for r in sorted(rows, key=lambda r: -r["gp_unit"]):
        take = min(left, r["deficit"]); r["units_used"] = take; gain += take * r["gp_unit"]; placed += take; left -= take
    unused = float(extra_units) - placed
    cogs = float(np.mean([r["cogs_unit"] for r in rows if r["cogs_unit"]] or [0.0]))
    tied = unused * cogs
    hold = tied * base["params"]["capital_cost_annual_pct"] * H / 365
    return dict(kind="extra_stock", title=p["product_name"], horizon_days=H, extra_units=float(extra_units), units_needed=placed, units_unused=unused, profit_gain=gain, cash_tied_up=tied, holding_cost=hold, net_profit=gain - hold,
                total_deficit=float(sum(r["deficit"] for r in rows)), channels=[dict(channel=r["channel"], deficit=r["deficit"], units_used=r.get("units_used", 0.0), gp_unit=r["gp_unit"]) for r in rows],
                assumptions=[f"Planning horizon is {H:.0f} days (target cover or lead time + 14 days, whichever is longer).", "Only the demand that current stock cannot cover is counted as sold; extra units beyond that stay in stock.", "Holding cost uses the configured annual capital cost on unit cost."])


def _material_price(base, material_id, pct, pass_through=0.0, **_):
    m = next((x for x in base["materials"] if x["material_id"] == material_id), None)
    if m is None:
        raise ValueError("Unknown material.")
    if pct is None or not -0.5 <= pct <= 2:
        raise ValueError("Price change must be between -50% and +200%.")
    rows, base_profit = [], 0.0
    for pid, p in base["products"].items():
        units = sum(ch["daily"] for ch in p["channels"]) * base["params"]["horizon_days"]
        base_profit += sum(ch["daily"] * base["params"]["horizon_days"] * ch["gp_unit"] for ch in p["channels"])
        use = next((b for b in base["bom"].get(pid, []) if b["material_id"] == material_id), None)
        if not use or units <= 0:
            continue
        d_cogs = use["cost_unit"] * pct
        rows.append(dict(product_id=pid, product_name=p["product_name"], units=units, cost_per_unit_change=d_cogs, profit_impact=-units * d_cogs * (1 - pass_through)))
    rows.sort(key=lambda r: r["profit_impact"])
    total = float(sum(r["profit_impact"] for r in rows))
    return dict(kind="material_price", title=m["material_name"], pct=pct, pass_through=pass_through, products_affected=len(rows), profit_impact=total, baseline_profit=base_profit,
                impact_share=(total / base_profit) if base_profit else None, top_products=rows[:8],
                assumptions=["Cost per unit = quantity in the bill of materials x average purchase price of the material.", f"{pass_through:.0%} of the increase is recovered through selling prices.", "Demand follows the forecast pace for the next 90 days."])


def run_scenario(base: dict, kind: str, **p) -> dict:
    if kind not in KINDS:
        raise ValueError("Unknown scenario.")
    return clean({"discount": _discount, "extra_stock": _extra_stock, "material_price": _material_price}[kind](base, **p))
