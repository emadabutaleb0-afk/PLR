"""12. PRODUCT STRATEGY ENGINE - eight explainable 0-100 scores per product and one final decision with the rule that fired."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.context import Ctx
from app.analytics.features import safe_div
from app.intelligence.common import egp


def _pct(s, inv=False):
    r = s.rank(pct=True) * 100
    return (100 - r) if inv else r


def supplier_score_by_product(c: Ctx, sup: dict) -> pd.Series:
    """Aggregated BOM -> material -> supplier link: spend-weighted supplier on-time and acceptance, per product."""
    t = sup["table"].set_index("supplier_id")
    s = (100 * (0.5 * t.on_time_rate + 0.5 * t.acceptance_rate)).rename("sc")
    pl_ = sup["product_link"].copy()
    pl_["sc"] = pl_.supplier_id.map(s)
    w = pl_.groupby("product_id").apply(lambda d: np.average(d.sc.fillna(d.sc.mean()), weights=d.spend.clip(lower=1)) if len(d) else np.nan, include_groups=False)
    return w


def strategy(c: Ctx, f: dict, pl: pd.DataFrame, mg: dict, sup: dict, mk: dict, ql: dict, actions: pd.DataFrame, cfg) -> pd.DataFrame:
    p = c.product[["product_id", "sku", "product_name", "product_family", "catalog_season"]].set_index("product_id")
    agg = pl.groupby("product_id").apply(lambda d: pd.Series(dict(
        v90=d.v90.sum(), v90_ly=d.v90_ly.sum(), yoy=(d.v90.sum() / d.v90_ly.sum()) if d.v90_ly.sum() > 0 else np.nan,
        net=d.net_12m.sum(), gp=d.gp_12m.sum(), stock=d.closing_stock.sum(), stock_value=d.stock_value.sum(), vel=d.vel.sum(),
        doc=min(d.closing_stock.sum() / max(d.vel.sum(), 1e-9), 999), so3=d.stockout_days_3m.sum(), return_rate=d.ret_units_12m.sum() / max(d.units_12m.sum(), 1),
        q_return_rate=d.q_units_12m.sum() / max(d.units_12m.sum(), 1), dead_hi=(d.dead_risk == "HIGH").sum(), stock_hi=(d.stockout_risk == "HIGH").sum())), include_groups=False)
    d = p.join(agg)
    d["margin"] = safe_div(d.gp, d.net)
    # --- scores (all percentile-/rule-based, 100 = good)
    d["demand_score"] = (0.5 * _pct(d.v90) + 0.5 * _pct(d.yoy.fillna(1))).round(1)
    mt = mg["table"].set_index("product_id")
    d["margin_score"] = (0.6 * _pct(d.margin) + 0.4 * mt.margin_health_score.reindex(d.index).fillna(50)).round(1)
    cover_pen = np.where(d.doc > 120, np.clip((d.doc - 120) / 240, 0, 1), np.where(d.doc < 10, np.clip((10 - d.doc) / 10, 0, 1), 0))
    d["inventory_score"] = (100 * (1 - cover_pen) - np.clip(d.so3, 0, 15) * 1.5).clip(0, 100).round(1)
    qp = f["qual_prod"].set_index("product_id")
    d["quality_score"] = (0.7 * _pct(qp.q_reject_rate.reindex(d.index).fillna(qp.q_reject_rate.median()), inv=True) + 0.3 * _pct(d.q_return_rate, inv=True)).round(1)
    pp = f["prod_prod"].set_index("product_id")
    d["production_score"] = (0.4 * _pct(pp.pr_eff.reindex(d.index).fillna(pp.pr_eff.median())) + 0.3 * _pct(pp.pr_delay.reindex(d.index).fillna(0), inv=True) +
                             0.3 * _pct(pp.pr_reject_rate.reindex(d.index).fillna(0), inv=True)).round(1)
    ss = supplier_score_by_product(c, sup).reindex(d.index)
    d["supplier_score"] = _pct(ss.fillna(ss.median())).round(1)
    mp = mk["by_product"].set_index("product_id")
    d["marketing_score"] = (0.6 * _pct(mp.profit_roas.reindex(d.index).fillna(mp.profit_roas.median())) + 0.4 * (100 - np.clip(abs(np.log(mp.support_ratio.reindex(d.index).fillna(1).clip(0.05, 20))) * 40, 0, 100))).round(1)
    d["customer_score"] = (0.6 * _pct(d.return_rate, inv=True) + 0.4 * _pct(d.q_return_rate, inv=True)).round(1)
    sc = ["demand_score", "margin_score", "inventory_score", "quality_score", "production_score", "supplier_score", "marketing_score", "customer_score"]
    names = dict(zip(sc, ["Demand", "Margin", "Inventory", "Quality", "Production", "Supplier", "Marketing", "Customer"]))
    dec, expl = [], []
    for pid, r in d.iterrows():
        weak = [names[k] for k in sc if r[k] < 35]; strong = [names[k] for k in sc if r[k] >= 70]
        if r.demand_score < 25 and r.inventory_score < 45 and r.margin_score < 50 and r.dead_hi >= 1:
            x, why = "PHASE_OUT", "Weak demand, trapped stock and below-average margin"
        elif r.dead_hi >= 2 and r.doc > cfg.dead_cover_days * 0.67:
            x, why = "STOP_REPLENISHMENT", "Stock is far above what demand needs in most locations"
        elif r.dead_hi >= 1 and r.demand_score < 50:
            x, why = "DISCOUNT", "Excess stock with only moderate demand"
        elif r.stock_hi >= 1 and r.quality_score >= 40 and r.production_score >= 40:
            x, why = "SCALE" if r.margin_score >= 60 and r.demand_score >= 60 else "MAINTAIN", "Demand outruns stock; supply side is healthy enough to respond"
            if x == "MAINTAIN":
                x, why = "RELOCATE", "Stock is short in some locations while elsewhere it is not"
        elif r.quality_score < 30 or r.production_score < 25 or r.supplier_score < 20:
            x, why = "FIX", "A quality, production or supplier weakness limits this product"
        elif r.demand_score >= 70 and r.margin_score >= 60 and r.inventory_score >= 50:
            x, why = "SCALE", "Strong demand and margin with healthy inventory"
        elif r.demand_score >= 55 and r.stock_hi >= 1:
            x, why = "RELOCATE", "Demand is healthy but stock is in the wrong places"
        else:
            x, why = "MAINTAIN", "No dimension is far enough from normal to justify a change"
        dec.append(x)
        expl.append(dict(rule=why, strongest=strong[:3], weakest=weak[:3]))
    d["decision"] = dec
    d["explanation"] = expl
    d["overall_score"] = d[sc].mean(axis=1).round(1)
    return d.reset_index()
