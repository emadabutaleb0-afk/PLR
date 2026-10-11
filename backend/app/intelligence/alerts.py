"""Alert Center content derived from recommendations: priority-limited so users are not spammed."""
from __future__ import annotations
from app.intelligence.common import egp

MAX_ALERTS = 40


def build_alerts(ranked: list[dict]) -> list[dict]:
    out = []
    for r in ranked[:200]:
        cat = r["category"]
        if r["urgency"] == "CRITICAL" or (r["urgency"] == "HIGH" and cat in ("REPLENISH", "LOW_STOCK_PUSH", "INVESTIGATE_SUPPLIER")):
            sev = "CRITICAL" if r["urgency"] == "CRITICAL" else "WARNING"
        elif cat in ("SCALE",):
            sev = "OPPORTUNITY"
        elif r["urgency"] in ("HIGH", "MEDIUM") and cat in ("DISCOUNT", "STOP_REPLENISHMENT", "PHASE_OUT", "OVERSTOCK_UNDERSUPPORTED", "FIX_MARGIN", "FIX_QUALITY", "MAINTAIN_MACHINE", "FIX_BOTTLENECK"):
            sev = "WARNING"
        else:
            continue
        out.append(dict(alert_key="alert:" + r["rec_key"], severity=sev, title=r["title"], body=f"{r['problem']}. {r['why'][0] if r['why'] else ''} Expected impact {egp(r['estimated_value_egp'])}.",
                        rec_key=r["rec_key"], location_id=r["location_id"], priority=r["priority_score"]))
        if len(out) >= MAX_ALERTS:
            break
    return out
