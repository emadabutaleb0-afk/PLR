"""9. RECOVERY PRIORITY ENGINE - one ranked list, deduplicated, never hundreds of alerts."""
from __future__ import annotations
import numpy as np
from app.intelligence.common import URG_MULT

TOP_N = 60


def prioritise(recs: list[dict]) -> list[dict]:
    if not recs:
        return []
    for r in recs:
        r["_raw"] = r["estimated_value_egp"] * r["confidence"] * URG_MULT.get(r["urgency"], 1.0)
    # one issue per entity: keep the strongest recommendation per (entity, product, location)
    best: dict = {}
    for r in sorted(recs, key=lambda x: -x["_raw"]):
        k = (r["entity_type"], r["entity_id"] if r["entity_type"] != "product" else r["product_id"], r["location_id"])
        if r["engine"] in ("size_curve",):
            k = k + ("size",)
        if k not in best:
            best[k] = r
    uniq = sorted(best.values(), key=lambda x: -x["_raw"])
    mx = max((r["_raw"] for r in uniq), default=1) or 1
    for r in uniq:
        r["priority_score"] = round(100 * np.log1p(r["_raw"]) / np.log1p(mx), 1)
    for r in recs:
        r.setdefault("priority_score", 0.0)
        r.pop("_raw", None)
    for r in uniq:
        r.pop("_raw", None)
    return uniq
