from __future__ import annotations
import math
import numpy as np
import pandas as pd

URG_MULT = {"CRITICAL": 1.5, "HIGH": 1.2, "MEDIUM": 1.0, "LOW": 0.7}
DEPT = {"REPLENISH": "Procurement", "RELOCATE": "Operations", "TRANSFER": "Operations", "DISCOUNT": "Merchandising",
        "STOP_REPLENISHMENT": "Merchandising", "PHASE_OUT": "Merchandising", "SCALE": "Merchandising", "FIX": "Quality",
        "MAINTAIN": "Merchandising", "MARKETING_SUPPORT": "Marketing"}


def egp(x) -> str:
    return f"EGP {x:,.0f}"


def num(x, d=0):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), d)


def clean(obj):
    """Make nested python/numpy/pandas objects JSON-safe (NaN -> None)."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if (math.isnan(obj) or math.isinf(obj)) else float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp,)):
        return obj.date().isoformat()
    if obj is pd.NaT:
        return None
    return obj


def records(df: pd.DataFrame) -> list[dict]:
    return clean(df.astype(object).where(df.notna(), None).to_dict("records"))


def make_rec(engine, category, title, problem, why, action, impact_type, value, loss, confidence, urgency, *,
             product_id=None, location_id=None, entity_type="product", entity_id=None, department=None, evidence=None,
             is_estimate=True, suffix="") -> dict:
    eid = entity_id or product_id or "global"
    key = f"{engine}:{category}:{entity_type}:{eid}:{location_id or '-'}{(':' + suffix) if suffix else ''}"
    return dict(rec_key=key, engine=engine, category=category, product_id=product_id, location_id=location_id,
                entity_type=entity_type, entity_id=str(eid), title=title, problem=problem, why=why, action=action,
                department=department or DEPT.get(category, "Management"), impact_type=impact_type,
                estimated_value_egp=float(max(value, 0)), estimated_loss_egp=float(max(loss, 0)),
                confidence=float(min(max(confidence, 0.05), 0.98)), urgency=urgency, evidence=clean(evidence or {}),
                is_estimate=is_estimate)


def confidence_from(signal: float, agree: bool | None, history_months: int, cv: float | None) -> float:
    """Transparent confidence: 0.45 base + signal strength + model agreement + history depth - volatility."""
    c = 0.45 + 0.25 * float(np.clip(signal, 0, 1)) + (0.12 if agree else 0.0) + 0.08 * min(history_months / 24, 1)
    if cv is not None and not np.isnan(cv):
        c -= 0.12 * float(np.clip(cv, 0, 1))
    return float(np.clip(c, 0.3, 0.95))
