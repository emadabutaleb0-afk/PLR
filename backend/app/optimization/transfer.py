"""Inventory transfer optimisation (real LP/MIP with PuLP + CBC).
For each product, donor locations hold surplus, recipient locations hold a deficit over the planning window.
minimise:  transfer_cost*x  +  lost_profit_per_unit * unmet_demand  +  holding_cost_per_unit * un-moved_surplus
Transfer cost per unit is NOT in the data: it comes from configuration (default 0) and is shown in the evidence."""
from __future__ import annotations
import pandas as pd
import pulp


def optimise_transfers(pl: pd.DataFrame, cfg, vel_col="vel", keep_days=60, min_units=10) -> pd.DataFrame:
    rows = []
    for pid, g in pl.groupby("product_id"):
        g = g.reset_index(drop=True)
        H = (g.supplier_lead_time_days.fillna(7) + 14).clip(lower=cfg.planning_horizon_days)
        need = g[vel_col] * H + g.safety_stock_units.fillna(0)
        deficit = (need - g.closing_stock).clip(lower=0)
        surplus = (g.closing_stock - (g[vel_col] * keep_days + g.safety_stock_units.fillna(0))).clip(lower=0)
        donors = [i for i in g.index if surplus[i] >= min_units]
        recips = [i for i in g.index if deficit[i] >= min_units and i not in donors]
        if not donors or not recips:
            continue
        hold = (g.cogs_unit.fillna(0) * cfg.capital_cost_annual_pct * 90 / 365)
        prob = pulp.LpProblem(f"transfer_{pid}", pulp.LpMinimize)
        x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0, cat="Integer") for i in donors for j in recips}
        unmet = {j: pulp.LpVariable(f"u_{j}", lowBound=0) for j in recips}
        left = {i: pulp.LpVariable(f"l_{i}", lowBound=0) for i in donors}
        prob += (pulp.lpSum(cfg.transfer_cost_per_unit_egp * x[k] for k in x)
                 + pulp.lpSum(float(g.gp_unit[j] if pd.notna(g.gp_unit[j]) else 0) * unmet[j] for j in recips)
                 + pulp.lpSum(float(hold[i]) * left[i] for i in donors))
        for j in recips:
            prob += pulp.lpSum(x[(i, j)] for i in donors) + unmet[j] == float(deficit[j])
        for i in donors:
            prob += pulp.lpSum(x[(i, j)] for j in recips) + left[i] == float(surplus[i])
        prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=10))
        if pulp.LpStatus[prob.status] != "Optimal":
            continue
        for (i, j), var in x.items():
            u = int(round(var.value() or 0))
            if u >= min_units:
                rows.append(dict(product_id=pid, from_location=g.location_id[i], to_location=g.location_id[j], units=u,
                                 from_cover_days=float(g.doc[i]) if pd.notna(g.doc[i]) else None,
                                 to_cover_days=float(g.doc[j]) if pd.notna(g.doc[j]) else None,
                                 from_stock=int(g.closing_stock[i]), to_stock=int(g.closing_stock[j]),
                                 from_velocity=float(g[vel_col][i]), to_velocity=float(g[vel_col][j]),
                                 to_deficit=float(deficit[j]), from_surplus=float(surplus[i]),
                                 net_unit_to=float(g.net_unit[j]), gp_unit_to=float(g.gp_unit[j]),
                                 cogs_unit=float(g.cogs_unit[i]), transfer_cost=float(cfg.transfer_cost_per_unit_egp * u)))
    return pd.DataFrame(rows)
