"""Markdown optimisation: choose the discount that maximises expected profit over the clearance window while
protecting gross margin. Uses scipy.optimize (bounded scalar optimisation) then snaps to 5-point steps.
Price response is NOT measurable in this dataset (checked: product x location x month fixed-effects regression gives an
insignificant discount coefficient), so the lift per 10pp is a configurable ASSUMPTION and results are labelled as scenarios."""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize_scalar


def max_discount(price: float, cost: float, floor: float, cap: float = 0.5) -> float:
    if price <= 0:
        return 0.0
    return float(np.clip(1 - cost / (price * (1 - floor)), 0, cap))


def optimise_markdown(stock: float, vel: float, price: float, cost: float, p_dead: float, cfg, horizon: int = 90) -> dict:
    dmax = max_discount(price, cost, cfg.margin_floor_pct)
    k = cfg.assumed_discount_lift_per_10pp
    hold = cost * cfg.capital_cost_annual_pct * horizon / 365

    def profit(d):
        mult = 1 + k * d / 0.10
        sold = min(stock, vel * mult * horizon)
        left = stock - sold
        # expected value of what is sold + carrying cost and expected write-off risk of what is not
        return sold * (price * (1 - d) - cost) - left * (hold + p_dead * cost)

    base = profit(0.0)
    if dmax < 0.05:
        return dict(discount=0.0, max_feasible=dmax, base_profit=base, new_profit=base, uplift=0.0, units_cleared=min(stock, vel * horizon),
                    units_cleared_base=min(stock, vel * horizon), feasible=False)
    res = minimize_scalar(lambda d: -profit(d), bounds=(0, dmax), method="bounded")
    cands = {0.0} | {c for c in (round(np.floor(res.x / 0.05) * 0.05, 2), round(np.ceil(res.x / 0.05) * 0.05, 2),
                                  round(round(res.x / 0.05) * 0.05, 2)) if c <= dmax + 1e-9}
    d_best = max(cands, key=profit)
    mult = 1 + k * d_best / 0.10
    cleared = min(stock, vel * mult * horizon)
    return dict(discount=float(d_best), max_feasible=dmax, base_profit=base, new_profit=profit(d_best),
                uplift=profit(d_best) - base, units_cleared=float(cleared), units_cleared_base=float(min(stock, vel * horizon)),
                feasible=True, lift_multiplier=float(mult), cash_recovered=float(cleared * price * (1 - d_best)))
