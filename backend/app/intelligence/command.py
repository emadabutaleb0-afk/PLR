"""16. COMMAND CENTER - the executive hook: six headline numbers and the five actions to take today (one per business question)."""
from __future__ import annotations
import pandas as pd
from app.intelligence.common import num, clean, egp

SLOTS = [("protect_revenue", "Protect Revenue", {"REPLENISH", "REPLENISH_SIZE"}, "/inventory"),
         ("protect_margin", "Protect Margin", {"FIX_MARGIN"}, "/merchandising"),
         ("reduce_dead_stock", "Reduce Dead Stock", {"DISCOUNT", "RELOCATE", "STOP_REPLENISHMENT", "PHASE_OUT", "OVERSTOCK_UNDERSUPPORTED"}, "/inventory"),
         ("prevent_supply_failure", "Prevent Supply Failure", set(), "/supply"),
         ("fix_profit_leakage", "Fix Profit Leakage", {"FIX_QUALITY"}, "/leakage")]


def _from_rec(slot, label, r, page):
    return dict(slot=slot, label=label, title=r["title"], detail=r["action"], why=(r.get("why") or [None])[0], value_egp=num(r["estimated_value_egp"]), value_kind="Expected impact (estimate)",
                urgency=r["urgency"], confidence=r["confidence"], rec_key=r["rec_key"], page=page)


def command_center(pl: pd.DataFrame, ranked: list[dict], ex: dict, leak: dict, supply: dict, disc: dict) -> dict:
    kp = {k["key"]: k["value"] for k in ex.get("kpis", [])}
    items = {i["key"]: i["value"] or 0 for i in leak["items"]}
    so_high = pl[pl.stockout_risk == "HIGH"].product_id.nunique()
    so_any = pl[pl.stockout_risk.isin(["HIGH", "MEDIUM"])].product_id.nunique()
    dead_high = pl[pl.dead_risk == "HIGH"].product_id.nunique()
    dead_any = pl[pl.dead_risk.isin(["HIGH", "MEDIUM"])].product_id.nunique()
    mats = supply["materials"]
    risky = [m for m in mats if m["risk"] in ("HIGH", "MEDIUM")]
    tiles = [dict(key="profit_at_risk", label="Profit at Risk", value=num(leak["profit_at_risk"]["total"]), unit="egp", tone="rose", note=leak["profit_at_risk"]["label"]),
             dict(key="recoverable_profit", label="Recoverable Profit", value=num(kp.get("recoverable_profit")), unit="egp", tone="emerald", note="Sum of estimated values of open recommendations (estimates)"),
             dict(key="stockout_risk", label="Stockout Risks", value=int(so_any), unit="products", tone="amber", note=f"{so_high} products at high risk of running out"),
             dict(key="overstock_risk", label="Overstock Risks", value=int(dead_any), unit="products", tone="violet", note=f"{dead_high} products at high dead-stock risk"),
             dict(key="quality_leakage", label="Quality & Waste Leakage", value=num(items.get("quality", 0) + items.get("production", 0)), unit="egp", tone="slate", note="Last 12 months: QC losses + production and print waste"),
             dict(key="supply_risks", label="Supply Risks", value=len(risky), unit="materials", tone="sky", note=f"{sum(1 for m in mats if m['risk'] == 'HIGH')} materials with high supplier risk")]
    by_cat: dict = {}
    for r in ranked:                                   # ranked is already sorted by priority
        by_cat.setdefault(r["category"], r)
    actions = []
    for slot, label, cats, page in SLOTS:
        pick = next((by_cat[c] for c in by_cat if c in cats), None) if cats else None
        if slot == "prevent_supply_failure":
            if risky:
                m = risky[0]
                actions.append(dict(slot=slot, label=label, title=f"Advance purchase of {m['material_name']}", detail=m["action"], why=f"Main supplier {m.get('main_supplier') or 'n/a'}; average delay when late {m['avg_delay_when_late']:.1f} days; {m['products']} products depend on it",
                                    value_egp=num(m["profit_dependent"]), value_kind="Profit that depends on this material (not a saving)", urgency="HIGH" if m["risk"] == "HIGH" else "MEDIUM", confidence=None, rec_key=None, page=page))
            continue
        if slot == "fix_profit_leakage" and leak.get("items") and (leak["total"] or 0) > 0:
            top = leak["items"][0]
            tp = leak["top_products"][0] if leak.get("top_products") else None
            detail = pick["action"] if (pick is not None and top["key"] in ("quality", "production")) else (f"Start with {tp['product_name']}, where {tp['main_driver']} is the main driver" if tp else top["definition"])
            actions.append(dict(slot=slot, label=label, title=f"{top['label']} is the biggest leak ({top['share']:.0%} of leakage)", detail=detail, why=pick["title"] if pick is not None else top["definition"],
                                value_egp=num(top["value"]), value_kind="Leaked in the last 12 months (not a saving)", urgency="HIGH", confidence=pick["confidence"] if pick is not None else None, rec_key=pick["rec_key"] if pick is not None else None, page=page))
            continue
        if pick is not None:
            actions.append(_from_rec(slot, label, pick, page))
        elif slot == "protect_margin" and disc.get("products"):
            p = disc["products"][0]
            actions.append(dict(slot=slot, label=label, title=f"Cap discounts on {p['product_name']}", detail=f"Keep Retail and Online discounts at or below {p['recommended_cap']:.0%}; average is {p['avg_discount']:.0%} today",
                                why=f"{egp(p['excess'])} of discount was granted above the {disc['comfort']:.0%} comfort band in 12 months, with no measurable volume lift", value_egp=num(p["excess"]), value_kind="Discount given away above the comfort band",
                                urgency="MEDIUM", confidence=None, rec_key=None, page="/discounts"))
        elif slot == "fix_profit_leakage" and leak.get("top_products"):
            p = leak["top_products"][0]
            actions.append(dict(slot=slot, label=label, title=f"Investigate leakage on {p['product_name']}", detail=f"Largest leakage driver: {p['main_driver']}", why=f"{egp(p['total'])} of leakage in 12 months",
                                value_egp=num(p["total"]), value_kind="Leakage in the last 12 months", urgency="MEDIUM", confidence=None, rec_key=None, page="/leakage"))
    return clean(dict(tiles=tiles, actions=actions))
