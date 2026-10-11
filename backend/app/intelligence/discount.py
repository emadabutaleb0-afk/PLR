"""15. DISCOUNT INTELLIGENCE - what has discounting actually done to volume and profit?

Discount depth in this company is set mostly by channel (Retail 0-20%, Online 0-25%, Wholesale 28-38%), so a pooled "more discount -> more units" chart is confounded
by bulk wholesale orders. We therefore analyse each channel on its own and test the response WITHIN product and month (product + month fixed effects).
Findings are predictive/associational, never claimed as causal elasticity. Where no volume lift is detectable the engine says so instead of assuming one."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.features import window, safe_div
from app.intelligence.common import num, records, clean

BANDS = [(-0.001, 0.0, "0%"), (0.0, 0.05, "1-5%"), (0.05, 0.10, "6-10%"), (0.10, 0.15, "11-15%"), (0.15, 0.20, "16-20%"), (0.20, 0.25, "21-25%"), (0.25, 0.40, "26-38%")]
CAVEATS = ["Discount depth differs mostly by channel, so every channel is analysed separately.",
           "The volume test compares months of the SAME product (with month effects removed). It is an association, not a proven price elasticity.",
           "Seasonal offers, campaigns and stock availability can move volume and discount together and are not fully separable in this data."]


def _band(s: pd.Series) -> pd.Series:
    labs = [b[2] for b in BANDS]
    edges = [BANDS[0][0]] + [b[1] for b in BANDS]
    return pd.cut(s, edges, labels=labs)


def _fe_test(sales: pd.DataFrame) -> dict:
    """log(1+units) ~ discount with product and month fixed effects (two-way demeaning)."""
    p = sales.assign(w=sales.discount_pct * sales.quantity).groupby(["product_id", "month"]).agg(units=("quantity", "sum"), w=("w", "sum")).reset_index()
    p["disc"] = p.w / p.units
    p["y"] = np.log1p(p.units)
    if len(p) < 60 or p.disc.std() < 1e-6:
        return dict(n=len(p), coef=None, se=None, verdict="Not enough variation in discount depth to test.")
    y, x = p.y.copy(), p.disc.copy()
    for _ in range(3):                                           # alternating projections = two-way within transform
        for k in ("product_id", "month"):
            y = y - y.groupby(p[k]).transform("mean"); x = x - x.groupby(p[k]).transform("mean")
    sxx = float((x * x).sum())
    if sxx <= 0:
        return dict(n=len(p), coef=None, se=None, verdict="Not enough variation in discount depth to test.")
    b = float((x * y).sum() / sxx)
    e = y - b * x
    dof = max(len(p) - p.product_id.nunique() - p.month.nunique() - 1, 1)
    se = float(np.sqrt((e * e).sum() / dof / sxx))
    lo, hi = b - 1.96 * se, b + 1.96 * se
    # coefficient is log-units per 1.00 of discount -> % unit change per +5pp
    f = lambda v: float(np.expm1(v * 0.05))
    if lo <= 0 <= hi:
        verdict = "No measurable volume lift from deeper discounts (the effect cannot be told apart from zero)."
    elif b > 0:
        verdict = "Deeper discounts are associated with more units."
    else:
        verdict = "Deeper discounts are associated with fewer units."
    return dict(n=len(p), coef=b, se=se, per5pp=f(b), per5pp_low=f(lo), per5pp_high=f(hi), verdict=verdict)


def discount_intelligence(c, f: dict, cfg) -> dict:
    end = c.as_of
    s = window(c.sales, "order_date", end, 365).copy()
    s["disc_val"] = s.list_price_egp * s.quantity - s.net_sales_egp
    s["band"] = _band(s.discount_pct.fillna(0))
    channels = []
    for ch in ["Retail", "Online", "Wholesale"]:
        d = s[s.channel == ch]
        if d.empty:
            continue
        g = d.groupby("band", observed=True).agg(lines=("quantity", "size"), units=("quantity", "sum"), net=("net_sales_egp", "sum"), gp=("gross_profit_egp", "sum"), disc_val=("disc_val", "sum")).reset_index()
        g["units_per_line"] = safe_div(g.units, g.lines)
        g["gp_unit"] = safe_div(g.gp, g.units)
        g["margin"] = safe_div(g.gp, g.net)
        g["share_units"] = safe_div(g.units, g.units.sum())
        ref = g.gp_unit.iloc[0]
        g["breakeven_lift"] = np.where(g.gp_unit > 0, ref / g.gp_unit.replace(0, np.nan) - 1, np.nan)   # extra units needed to earn the same gross profit as the shallowest band
        channels.append(dict(channel=ch, bands=records(g), test=_fe_test(d) if ch != "Wholesale" else dict(n=0, coef=None, se=None, verdict="Wholesale discounts are a structural price tier (28-38%) and are not tested as a promotion."),
                             avg_discount=num(float((d.discount_pct * d.quantity).sum() / max(d.quantity.sum(), 1)), 4), disc_val=num(d.disc_val.sum()), gp=num(d.gross_profit_egp.sum()), units=int(d.quantity.sum())))
    # per product (Retail + Online): where is margin being given away, and what cap protects it
    ro = s[s.channel.isin(["Retail", "Online"])]
    r = ro.groupby("product_id").agg(units=("quantity", "sum"), list_value=("list_price_egp", lambda x: 0.0), net=("net_sales_egp", "sum"), cogs=("estimated_cogs_egp", "sum"), gp=("gross_profit_egp", "sum"),
                                      disc_val=("disc_val", "sum")).reset_index()
    ro = ro.assign(list_val=ro.list_price_egp * ro.quantity, excess=(ro.discount_pct.fillna(0) - cfg.discount_comfort_pct).clip(lower=0) * ro.list_price_egp * ro.quantity,
                 deep_units=np.where(ro.discount_pct.fillna(0) > cfg.discount_comfort_pct, ro.quantity, 0))
    lv = ro.groupby("product_id").agg(list_val=("list_val", "sum"), excess=("excess", "sum"), deep_units=("deep_units", "sum")).reset_index()
    r = r.drop(columns="list_value").merge(lv, on="product_id")
    r["avg_discount"] = safe_div(r.disc_val, r.list_val)
    r["margin"] = safe_div(r.gp, r.net)
    r["list_unit"] = safe_div(r.list_val, r.units)
    r["cogs_unit"] = safe_div(r.cogs, r.units)
    # largest discount that still keeps the margin floor; the recommended cap is the lower of that and the comfort band
    feas = 1 - r.cogs_unit / (r.list_unit * (1 - cfg.margin_floor_pct)).replace(0, np.nan)
    r["max_feasible"] = feas.clip(lower=0, upper=1)
    r["recommended_cap"] = np.minimum(r.max_feasible.fillna(0), cfg.discount_comfort_pct)
    r["deep_share"] = safe_div(r.deep_units, r.units)
    r["above_cap"] = r.deep_share >= 0.25
    r["product_name"] = r.product_id.map(c.product.set_index("product_id").product_name)
    r = r.sort_values("excess", ascending=False)
    cols = ["product_id", "product_name", "units", "avg_discount", "deep_share", "margin", "gp", "disc_val", "excess", "max_feasible", "recommended_cap", "above_cap"]
    tot_ex = float(r.excess.sum())
    tests = [x["test"] for x in channels if x["test"].get("coef") is not None]
    no_lift = bool(tests) and not any(t["verdict"].startswith("Deeper discounts are associated with more") for t in tests)
    headline = ("In Retail and Online, deeper discounts did not produce more units, but every extra discount step cost gross profit. "
                "Keep discounts at or below the comfort band unless a campaign proves its lift.") if no_lift else \
               "Deeper discounts are associated with more units in at least one channel: compare the break-even lift with the measured lift before deepening any discount."
    return clean(dict(channels=channels, products=records(r[cols].head(40)), comfort=cfg.discount_comfort_pct, floor=cfg.margin_floor_pct, excess_total=tot_ex, headline=headline,
                      products_above_cap=int(r.above_cap.sum()), caveats=CAVEATS, window_label=f"{(end - pd.Timedelta(days=364)):%b %Y} - {end:%b %Y} (12 months)"))
