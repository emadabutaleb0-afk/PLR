"""14. CHANNEL ALLOCATION OPTIMISER - Retail vs Online vs Wholesale.

The data has three selling locations (one per channel), so we do NOT invent a branch-transfer network: the question answered is
"given the units we hold of a product, how should they be split across channels?"
Greedy fill by gross profit per unit is exactly optimal for this linear problem:
  1. cover lead-time demand + safety stock in every channel (highest profit channel first if stock is short)
  2. fill the remaining demand over the planning horizon, highest profit per unit first
  3. park any excess in proportion to demand (flagged as excess)"""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.intelligence.common import num, records, clean

CHANNEL_ORDER = ["Retail", "Online", "Wholesale"]
NOTE = ("Wholesale is contract-driven: confirm commitments before moving stock out of the Wholesale Desk. "
        "The planning horizon is the target cover (45 days by default) or lead time + 14 days, whichever is longer. Demand is the forecast pace per channel; profit per unit is each channel's actual gross profit per unit (last 180 days).")


def allocate(pool: float, base: np.ndarray, demand: np.ndarray, safety: np.ndarray, gp: np.ndarray, vel: np.ndarray) -> np.ndarray:
    """Return units per channel (same order as inputs). All inputs are 1-D arrays; pool is the units to place."""
    n = len(gp)
    out = np.zeros(n)
    order = np.argsort(-gp)
    rem = float(pool)
    for i in order:                              # tier 1: lead-time demand + safety stock
        t = min(rem, base[i]); out[i] += t; rem -= t
    for i in order:                              # tier 2: remaining horizon demand (+ safety)
        t = min(rem, max(demand[i] + safety[i] - out[i], 0)); out[i] += t; rem -= t
    if rem > 1e-9:                               # tier 3: excess, parked by demand weight
        w = vel / vel.sum() if vel.sum() > 0 else np.ones(n) / n
        out += rem * w
    return out


def channel_allocation(pl: pd.DataFrame, cfg, min_units: int = 10) -> dict:
    rows, params = [], {}
    for pid, g in pl.groupby("product_id"):
        g = g.set_index("channel")
        if len(g) < 2:
            continue
        ch = [x for x in CHANNEL_ORDER if x in g.index] + [x for x in g.index if x not in CHANNEL_ORDER]
        g = g.loc[ch]
        lead = g.supplier_lead_time_days.fillna(7)
        H = float(max(cfg.target_cover_days, lead.max() + 14))
        vel = g.vel.fillna(0).clip(lower=0).values.astype(float)
        safety = g.safety_stock_units.fillna(0).values.astype(float)
        stock = g.closing_stock.fillna(0).clip(lower=0).values.astype(float)
        gp = g.gp_unit.fillna(0).values.astype(float)
        demand = vel * H
        base = np.minimum(vel * lead.values + safety, demand + safety)
        rec = allocate(stock.sum(), base, demand, safety, gp, vel)
        rec = np.round(rec)
        rec[np.argmax(rec)] += stock.sum() - rec.sum()          # keep the total exact after rounding
        cur_gp = float((gp * np.minimum(stock, demand)).sum())
        rec_gp = float((gp * np.minimum(rec, demand)).sum())
        shift = rec - stock
        moved = float(shift[shift > 0].sum())
        params[pid] = dict(channels=ch, vel=vel.tolist(), safety=safety.tolist(), gp=gp.tolist(), lead=lead.values.tolist(), horizon=H, stock=stock.tolist(), base=base.tolist())
        if stock.sum() <= 0:
            continue
        short = [c for c, s, d in zip(ch, stock, demand) if s < d * 0.5 and d > 0]
        rows.append(dict(product_id=pid, product_name=g.product_name.iloc[0], sku=g.sku.iloc[0], horizon_days=H, pool_units=int(stock.sum()), moved_units=int(moved),
                         profit_uplift=max(rec_gp - cur_gp, 0.0), short_channels=short, worth_acting=bool(moved >= min_units and rec_gp - cur_gp > 0),
                         channels=[dict(channel=c, current=int(s), recommended=int(r), shift=int(r - s), demand=num(d, 0), gp_unit=num(p, 1), cover_days=num(s / v, 0) if v > 0 else None)
                                   for c, s, r, d, p, v in zip(ch, stock, rec, demand, gp, vel)]))
    df = pd.DataFrame(rows)
    if df.empty:
        return clean(dict(rows=[], summary={}, params=params, note=NOTE))
    df = df.sort_values("profit_uplift", ascending=False)
    ch_cur, ch_rec = {}, {}
    for r in rows:
        for x in r["channels"]:
            ch_cur[x["channel"]] = ch_cur.get(x["channel"], 0) + x["current"]
            ch_rec[x["channel"]] = ch_rec.get(x["channel"], 0) + x["recommended"]
    act = df[df.worth_acting]
    summary = dict(products=len(df), products_to_rebalance=len(act), units_to_move=int(act.moved_units.sum()), profit_uplift=num(act.profit_uplift.sum()),
                   by_channel=[dict(channel=k, current=ch_cur[k], recommended=ch_rec.get(k, 0)) for k in ch_cur],
                   label="ESTIMATE: extra gross profit over the planning horizon if stock sits where profit per unit is highest, assuming demand follows the forecast pace.")
    return clean(dict(rows=df.to_dict("records"), summary=summary, params=params, note=NOTE))


def split_units(params: dict, units: float) -> list[dict]:
    """Split an arbitrary quantity (e.g. a new production batch) across channels for one product."""
    p = params
    vel, safety, gp = np.array(p["vel"]), np.array(p["safety"]), np.array(p["gp"])
    demand = vel * p["horizon"]
    base = np.array(p["base"])
    rec = np.round(allocate(units, base, demand, safety, gp, vel))
    if rec.sum() != units and len(rec):
        rec[np.argmax(rec)] += units - rec.sum()
    return [dict(channel=c, units=int(u), share=num(u / units, 4) if units else 0, demand=num(d, 0), gp_unit=num(g, 1)) for c, u, d, g in zip(p["channels"], rec, demand, gp)]
