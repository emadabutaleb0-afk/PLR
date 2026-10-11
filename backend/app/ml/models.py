"""Local ML (scikit-learn / LightGBM). Time-based validation, leakage-safe features, honest metrics, local model store.
ML is used only where the data supports it:
  * stockout risk  (LightGBM classifier)
  * dead-stock risk (LightGBM classifier)
  * demand forecast (LightGBM regressors, h=1..3 months, must beat seasonal-naive / moving-average baselines)
Margin erosion is NOT modelled: month-to-month product margin change is statistically noise-like (mean ~0, no stable
drivers) so a deterministic decomposition is used instead (see intelligence/margin.py)."""
from __future__ import annotations
import os, uuid, warnings
from datetime import datetime
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
import lightgbm as lgb
from app.analytics.context import Ctx

warnings.filterwarnings("ignore")
KEYS = ["product_id", "location_id"]
FEATS = ["closing_stock", "sold_qty", "received_qty", "returned_qty", "damaged_qty", "avg_daily_sales_90d", "days_of_cover",
         "safety_stock_units", "reorder_point_units", "supplier_lead_time_days", "stockout_days_in_month", "so_lag1", "so_roll3",
         "sold_lag1", "sold_lag2", "sold_roll3", "sold_ratio", "stock_vs_reorder", "cover_vs_lead", "loc_code", "moy_sin",
         "moy_cos", "fam_code", "price", "margin", "mkt_spend", "units_ly"]


SIGNAL_FEATS = ["mkt_spend_lag1", "mkt_spend_roll3", "mkt_clicks_roll3", "mkt_orders_roll3", "mkt_discount",
                "web_sessions", "web_sessions_mom", "web_conv", "web_atc", "web_checkout"]   # advertising and website momentum (known at the forecast origin)


def build_panel(c: Ctx) -> pd.DataFrame:
    inv = c.inv.sort_values(KEYS + ["snapshot_month"]).copy()
    inv["month"] = inv.snapshot_month
    g = inv.groupby(KEYS)
    inv["returned_qty"] = inv["returned_qty"]
    inv["so_lag1"] = g.stockout_days_in_month.shift(1)
    inv["so_roll3"] = g.stockout_days_in_month.transform(lambda x: x.rolling(3, min_periods=1).sum())
    for k in (1, 2):
        inv[f"sold_lag{k}"] = g.sold_qty.shift(k)
    inv["sold_roll3"] = g.sold_qty.transform(lambda x: x.rolling(3, min_periods=1).mean())
    inv["sold_ratio"] = inv.sold_qty / inv.sold_roll3.replace(0, np.nan)
    inv["units_ly"] = g.sold_qty.shift(12)
    inv["stock_vs_reorder"] = inv.closing_stock - inv.reorder_point_units
    inv["cover_vs_lead"] = inv.days_of_cover - inv.supplier_lead_time_days
    inv["loc_code"] = inv.location_id.astype("category").cat.codes
    inv["moy_sin"] = np.sin(2 * np.pi * inv.month.dt.month / 12)
    inv["moy_cos"] = np.cos(2 * np.pi * inv.month.dt.month / 12)
    fam = c.product.set_index("product_id").product_family.astype("category").cat.codes
    inv["fam_code"] = inv.product_id.map(fam)
    s = c.sales
    pm = s.groupby(KEYS + ["month"]).agg(net=("net_sales_egp", "sum"), gp=("gross_profit_egp", "sum"),
                                         u=("quantity", "sum")).reset_index()
    pm["price"] = pm.net / pm.u
    pm["margin"] = pm.gp / pm.net
    inv = inv.merge(pm[KEYS + ["month", "price", "margin"]], on=KEYS + ["month"], how="left")
    mk = c.mkt.copy()
    mk["month"] = mk.start_date.dt.to_period("M").dt.to_timestamp()
    mk = mk.groupby(["product_id", "month"]).agg(mkt_spend=("spend_egp", "sum"), mkt_clicks=("clicks", "sum"), mkt_orders=("orders_attributed", "sum"),
                                                  mkt_discount=("discount_pct", "mean")).reset_index()
    inv = inv.merge(mk, on=["product_id", "month"], how="left")
    for k in ("mkt_spend", "mkt_clicks", "mkt_orders", "mkt_discount"):
        inv[k] = inv[k].fillna(0)
    g = inv.groupby(KEYS)
    inv["mkt_spend_lag1"] = g.mkt_spend.shift(1)
    inv["mkt_spend_roll3"] = g.mkt_spend.transform(lambda x: x.rolling(3, min_periods=1).sum())
    inv["mkt_clicks_roll3"] = g.mkt_clicks.transform(lambda x: x.rolling(3, min_periods=1).sum())
    inv["mkt_orders_roll3"] = g.mkt_orders.transform(lambda x: x.rolling(3, min_periods=1).sum())
    # website: store-wide monthly momentum (same value for every product in a month; the model combines it with location and product)
    w = c.web.copy()
    w["month"] = w.date.dt.to_period("M").dt.to_timestamp()
    wm = w.groupby("month").agg(web_sessions=("sessions", "sum"), web_orders=("orders", "sum"), web_atc=("add_to_cart_rate", "mean"), web_checkout=("checkout_rate", "mean")).reset_index().sort_values("month")
    wm["web_conv"] = wm.web_orders / wm.web_sessions.replace(0, np.nan)
    wm["web_sessions_mom"] = wm.web_sessions / wm.web_sessions.shift(1).rolling(3, min_periods=1).mean()
    inv = inv.merge(wm[["month", "web_sessions", "web_sessions_mom", "web_conv", "web_atc", "web_checkout"]], on="month", how="left")
    # targets (future information, used only as labels)
    g = inv.groupby(KEYS)
    inv["y_stockout"] = (g.stockout_days_in_month.shift(-1) > 0).astype(float).where(g.stockout_days_in_month.shift(-1).notna())
    nxt3 = sum(g.sold_qty.shift(-k) for k in (1, 2, 3))
    valid3 = g.sold_qty.shift(-3).notna()
    inv["y_dead"] = ((nxt3 / inv.closing_stock.clip(lower=1) < 0.4) & (inv.closing_stock >= 20)).astype(float).where(valid3 & (inv.closing_stock >= 20))
    for h in (1, 2, 3):
        inv[f"y_sold_h{h}"] = g.sold_qty.shift(-h)
        inv[f"seas_h{h}"] = g.sold_qty.shift(12 - h)  # same calendar month last year (observed at origin)
    return inv


def _metrics_cls(y, p, base_score):
    y = np.asarray(y); out = {"rows": int(len(y)), "positives": int(y.sum()), "base_rate": round(float(y.mean()), 4)}
    if y.sum() >= 5 and (1 - y).sum() >= 5:
        out["roc_auc"] = round(float(roc_auc_score(y, p)), 3)
        out["pr_auc"] = round(float(average_precision_score(y, p)), 3)
        out["brier"] = round(float(brier_score_loss(y, np.clip(p, 0, 1))), 4)
        out["baseline_roc_auc_rule"] = round(float(roc_auc_score(y, base_score)), 3)
        out["beats_rule_baseline"] = bool(out["roc_auc"] > out["baseline_roc_auc_rule"])
        top = max(int(len(y) * 0.1), 1); idx = np.argsort(-p)[:top]
        out["lift_top10pct"] = round(float(y[idx].mean() / max(y.mean(), 1e-9)), 2)
    else:
        out["note"] = "too few positive cases in the validation window for reliable metrics"
    return out


def _fit_cls(df: pd.DataFrame, target: str, baseline_col: str, sign: int, horizon_embargo: int):
    d = df[df[target].notna()].copy()
    months = sorted(d.month.unique())
    val_n = 6
    if len(months) < 14:
        return None, {"usable": False, "note": "not enough history for time-based validation"}, None
    val_months = months[-val_n:]
    tr = d[d.month < pd.Timestamp(val_months[0]) - pd.DateOffset(months=horizon_embargo)]
    va = d[d.month.isin(val_months)]
    params = dict(n_estimators=250, learning_rate=0.04, num_leaves=12, min_child_samples=15, subsample=0.8, subsample_freq=1,
                  colsample_bytree=0.8, reg_lambda=2.0, scale_pos_weight=1.0, verbose=-1, n_jobs=1, random_state=7)
    pos = max(tr[target].sum(), 1); params["scale_pos_weight"] = float(min((len(tr) - pos) / pos, 30))
    m = lgb.LGBMClassifier(**params).fit(tr[FEATS], tr[target])
    pv = m.predict_proba(va[FEATS])[:, 1]
    met = _metrics_cls(va[target].values, pv, sign * va[baseline_col].fillna(0).values)
    met.update(train_rows=int(len(tr)), valid_rows=int(len(va)), usable=bool(met.get("roc_auc", 0) >= 0.6 and met.get("positives", 0) >= 10))
    window_s = f"train<{(pd.Timestamp(val_months[0]) - pd.DateOffset(months=horizon_embargo)).date()} valid={pd.Timestamp(val_months[0]).date()}..{pd.Timestamp(val_months[-1]).date()}"
    final = lgb.LGBMClassifier(**params).fit(d[FEATS], d[target])  # refit on all labelled history for inference
    imp = dict(sorted(zip(FEATS, map(float, final.booster_.feature_importance("gain"))), key=lambda x: -x[1])[:10])
    return final, met, (imp, window_s)


def _wape(y, p):
    return float(np.abs(y - p).sum() / max(np.abs(y).sum(), 1e-9))


def _fit_demand(df: pd.DataFrame, h: int):
    """Two candidate models per horizon: base features, and base + advertising/website signals. The signals are used only if they
    beat the base model on the time-based validation window by at least 2%; the choice and both errors are reported."""
    t = f"y_sold_h{h}"; sc = f"seas_h{h}"
    d = df[df[t].notna() & df[sc].notna()].copy()
    months = sorted(d.month.unique())
    if len(months) < 10:
        return None, {"usable": False, "note": "not enough history"}, None, None
    val_months = months[-4:]
    tr = d[d.month < pd.Timestamp(val_months[0]) - pd.DateOffset(months=h)]
    va = d[d.month.isin(val_months)]
    new_model = lambda: lgb.LGBMRegressor(n_estimators=300, learning_rate=0.04, num_leaves=15, min_child_samples=10, subsample=0.8,
                                          subsample_freq=1, colsample_bytree=0.8, verbose=-1, n_jobs=1, random_state=7)
    X = lambda x, cols: x[cols].rename(columns={sc: "seasonal_lag"})
    base_cols, sig_cols = FEATS + [sc], FEATS + SIGNAL_FEATS + [sc]
    wape = {}
    for k, cols in (("base", base_cols), ("signals", sig_cols)):
        m = new_model().fit(X(tr, cols), np.log1p(tr[t]))
        wape[k] = _wape(va[t].values, np.expm1(m.predict(X(va, cols))).clip(min=0))
    use_signals = wape["signals"] < wape["base"] * 0.98
    cols = sig_cols if use_signals else base_cols
    w_model = wape["signals"] if use_signals else wape["base"]
    base_seas, base_ma = va[sc].values, va.sold_roll3.values
    w_seas, w_ma = _wape(va[t].values, base_seas), _wape(va[t].values, base_ma)
    use_model = w_model < min(w_seas, w_ma) * 0.98
    met = dict(horizon_months=h, wape_model=round(w_model, 3), wape_seasonal_naive=round(w_seas, 3), wape_moving_avg3=round(w_ma, 3),
               wape_base_features=round(wape["base"], 3), wape_with_signals=round(wape["signals"], 3), signals_used=bool(use_signals),
               train_rows=int(len(tr)), valid_rows=int(len(va)), usable=True, selected="lightgbm" if use_model else
               ("seasonal_naive" if w_seas <= w_ma else "moving_avg3"))
    final = new_model().fit(X(d, cols), np.log1p(d[t]))
    imp = dict(sorted(zip(["seasonal_lag" if c_ == sc else c_ for c_ in cols], map(float, final.booster_.feature_importance("gain"))), key=lambda x: -x[1])[:8])
    return (final if use_model else None), met, (imp, f"valid={pd.Timestamp(val_months[0]).date()}..{pd.Timestamp(val_months[-1]).date()}"), cols


def train_and_predict(c: Ctx, model_dir: str) -> dict:
    """Returns {'predictions': DataFrame(product x location), 'registry': [dict], 'forecast': DataFrame}"""
    os.makedirs(model_dir, exist_ok=True)
    panel = build_panel(c)
    latest = panel[panel.month == c.inv_month].copy()
    ver = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    registry, preds = [], latest[KEYS].copy().reset_index(drop=True)
    latest = latest.reset_index(drop=True)

    for name, target, base_col, sign, emb in [("stockout_risk", "y_stockout", "days_of_cover", -1, 1),
                                               ("dead_stock_risk", "y_dead", "days_of_cover", 1, 3)]:
        model, met, extra = _fit_cls(panel, target, base_col, sign, emb)
        if model is None:
            registry.append(dict(name=name, version=ver, algorithm="lightgbm", metrics=met, usable=False)); continue
        p = model.predict_proba(latest[FEATS])[:, 1]
        preds[f"p_{name}"] = p
        path = os.path.join(model_dir, f"{name}_{ver}.joblib"); joblib.dump(model, path)
        registry.append(dict(name=name, version=ver, algorithm="lightgbm", metrics=met, usable=met.get("usable", False),
                             feature_importance=extra[0], train_window=extra[1], path=path,
                             rows_train=met.get("train_rows", 0), rows_valid=met.get("valid_rows", 0),
                             prediction_stats=dict(mean=round(float(p.mean()), 4), p90=round(float(np.quantile(p, .9)), 4),
                                                   high_share=round(float((p > 0.5).mean()), 4)),
                             feature_snapshot={f: [float(latest[f].mean()), float(latest[f].std())] for f in FEATS}))
    # demand forecast: h = 1..3 months of units
    fc = latest[KEYS].copy()
    for h in (1, 2, 3):
        model, met, extra, dcols = _fit_demand(panel, h)
        sc = f"seas_h{h}"
        if model is not None:
            X = latest[dcols].rename(columns={sc: "seasonal_lag"})
            fc[f"units_m{h}"] = np.expm1(model.predict(X)).clip(min=0)
            path = os.path.join(model_dir, f"demand_h{h}_{ver}.joblib"); joblib.dump(model, path)
        else:
            use_seas = met.get("selected") == "seasonal_naive"
            fc[f"units_m{h}"] = (latest[sc] if use_seas else latest.sold_roll3).fillna(latest.sold_roll3).values
            path = None
        registry.append(dict(name=f"demand_forecast_h{h}", version=ver, algorithm=met.get("selected", "baseline"), metrics=met,
                             usable=met.get("usable", False), feature_importance=extra[0] if extra else None,
                             train_window=extra[1] if extra else None, path=path,
                             rows_train=met.get("train_rows", 0), rows_valid=met.get("valid_rows", 0),
                             prediction_stats=dict(mean=round(float(fc[f"units_m{h}"].mean()), 2))))
    fc["ly_next90_units"] = latest[["seas_h1", "seas_h2", "seas_h3"]].sum(axis=1).values   # what happened in the same 3 months last year
    fc["forecast_90d_units"] = fc[["units_m1", "units_m2", "units_m3"]].sum(axis=1)
    fc["forecast_daily"] = fc.forecast_90d_units / 91.0
    return dict(predictions=preds, forecast=fc, registry=registry)
