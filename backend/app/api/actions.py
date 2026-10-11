from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.deps import require, has
from app.models.app import User, Recommendation, RecommendationFeedback, ActionItem, Alert, DecisionTracking, now
from app.core.config import get_settings
from app.services import outcomes
from app.api.common import PageParams, paginate, freshness, snap
from app.api.business import rec_dict
from app.services.audit import audit

router = APIRouter(tags=["Decisions & Actions"])
ACTION_STATUSES = ["NEW", "UNDER_REVIEW", "APPROVED", "IN_PROGRESS", "DONE", "REJECTED"]


def _get_rec(db, u, key) -> Recommendation:
    r = db.scalars(select(Recommendation).where(Recommendation.rec_key == key)).first()
    if not r:
        raise HTTPException(404, "This recommendation no longer exists.")
    if u.role == "STORE_MANAGER" and r.location_id not in (u.allowed_locations or []):
        raise HTTPException(403, "This recommendation is outside the locations you manage.")
    if r.entity_type == "supplier" and not has(u, "suppliers"):
        raise HTTPException(403, "Procurement details are not available to your role.")
    return r


class FeedbackIn(BaseModel):
    decision: str = Field(pattern="^(ACCEPT|REJECT|DEFER)$")
    comment: str | None = Field(None, max_length=1000)
    owner_email: str | None = None
    acknowledge_stale: bool = False      # approve although the newest business data is older than STALE_DATA_DAYS


def _check_fresh(db, acknowledge: bool):
    f = freshness(db)
    if get_settings().block_stale_approvals and f.get("status") == "STALE" and not acknowledge:
        raise HTTPException(409, f"{f.get('message')} Refresh the data first, or repeat the request with acknowledge_stale=true to approve on old data (this is logged).")
    return f


def _accept(db, u, r: Recommendation, comment, owner_email, plan_name=None, data_as_of=None):
    """Approve one recommendation: feedback row, action item, and a tracked decision with its frozen baseline. Caller commits."""
    fb = RecommendationFeedback(rec_key=r.rec_key, user_id=u.id, user_email=u.email, decision="ACCEPT", comment=comment, expected_value_egp=r.estimated_value_egp, impact_type=r.impact_type)
    db.add(fb)
    r.status, r.updated_at = "ACCEPTED", now()
    item = db.scalars(select(ActionItem).where(ActionItem.rec_key == r.rec_key)).first()
    if not item:
        item = ActionItem(rec_key=r.rec_key, title=r.title, recommended_action=r.action, department=r.department, owner_email=owner_email or u.email,
                          business_impact_egp=r.estimated_value_egp, urgency=r.urgency, status="NEW")
        db.add(item)
    db.flush()
    tr = outcomes.register(db, u, r, fb.id, item.id, data_as_of, plan_name)
    db.flush()
    return item, tr


class FeedbackIn(BaseModel):
    decision: str = Field(pattern="^(ACCEPT|REJECT|DEFER)$")
    comment: str | None = Field(None, max_length=1000)
    owner_email: str | None = None
    acknowledge_stale: bool = False      # approve although the newest business data is older than STALE_DATA_DAYS


def _check_fresh(db, acknowledge: bool):
    f = freshness(db)
    if get_settings().block_stale_approvals and f.get("status") == "STALE" and not acknowledge:
        raise HTTPException(409, f"{f.get('message')} Refresh the data first, or repeat the request with acknowledge_stale=true to approve on old data (this is logged).")
    return f


def _accept(db, u, r: Recommendation, comment, owner_email, plan_name=None, data_as_of=None):
    """Approve one recommendation: feedback row, action item, and a tracked decision with its frozen baseline. Caller commits."""
    fb = RecommendationFeedback(rec_key=r.rec_key, user_id=u.id, user_email=u.email, decision="ACCEPT", comment=comment, expected_value_egp=r.estimated_value_egp, impact_type=r.impact_type)
    db.add(fb)
    r.status, r.updated_at = "ACCEPTED", now()
    item = db.scalars(select(ActionItem).where(ActionItem.rec_key == r.rec_key)).first()
    if not item:
        item = ActionItem(rec_key=r.rec_key, title=r.title, recommended_action=r.action, department=r.department, owner_email=owner_email or u.email,
                          business_impact_egp=r.estimated_value_egp, urgency=r.urgency, status="NEW")
        db.add(item)
    db.flush()
    tr = outcomes.register(db, u, r, fb.id, item.id, data_as_of, plan_name)
    db.flush()
    return item, tr


@router.get("/recommendations/{rec_key:path}", summary="Recommendation detail (logged as viewed)")
def get_rec(rec_key: str, db: Session = Depends(get_db), u: User = Depends(require("recovery"))):
    r = _get_rec(db, u, rec_key)
    audit(db, u, "recommendation_viewed", "recommendation", r.rec_key)
    fb = db.scalars(select(RecommendationFeedback).where(RecommendationFeedback.rec_key == r.rec_key).order_by(RecommendationFeedback.ts.desc())).all()
    tr = db.scalars(select(DecisionTracking).where(DecisionTracking.rec_key == r.rec_key).order_by(DecisionTracking.approved_at.desc())).first()
    return {**rec_dict(r), "feedback": [dict(user=f.user_email, decision=f.decision, comment=f.comment, ts=f.ts.isoformat(), expected_value_egp=f.expected_value_egp,
                                              realized_value_egp=f.realized_value_egp, outcome_note=f.outcome_note) for f in fb],
            "tracking": _td(tr) if tr else None, "freshness": freshness(db)}


@router.post("/recommendations/{rec_key:path}/feedback", status_code=201)
def feedback(rec_key: str, body: FeedbackIn, db: Session = Depends(get_db), u: User = Depends(require("decide"))):
    r = _get_rec(db, u, rec_key)
    item = tr = None
    if body.decision == "ACCEPT":
        f = _check_fresh(db, body.acknowledge_stale)
        item, tr = _accept(db, u, r, body.comment, body.owner_email, data_as_of=f.get("data_as_of"))
        if body.acknowledge_stale and f.get("status") == "STALE":
            audit(db, u, "stale_data_approval_acknowledged", "recommendation", r.rec_key, {"data_as_of": f.get("data_as_of")})
    else:
        db.add(RecommendationFeedback(rec_key=r.rec_key, user_id=u.id, user_email=u.email, decision=body.decision, comment=body.comment, expected_value_egp=r.estimated_value_egp, impact_type=r.impact_type))
        r.status = {"REJECT": "REJECTED", "DEFER": "DEFERRED"}[body.decision]
        r.updated_at = now()
    db.commit()
    audit(db, u, f"recommendation_{body.decision.lower()}ed" if body.decision != "DEFER" else "recommendation_deferred", "recommendation", r.rec_key, {"expected_value_egp": round(r.estimated_value_egp)})
    return {"status": r.status, "action_item_id": item.id if item else None, "tracking_id": tr.id if tr else None, "tracking_status": tr.status if tr else None}


class OutcomeIn(BaseModel):
    realized_value_egp: float = Field(ge=-1e10, le=1e10)
    realized_revenue_egp: float | None = None
    note: str | None = Field(None, max_length=1000)


@router.post("/recommendations/{rec_key:path}/outcome")
def outcome(rec_key: str, body: OutcomeIn, db: Session = Depends(get_db), u: User = Depends(require("decide"))):
    r = _get_rec(db, u, rec_key)
    fb = db.scalars(select(RecommendationFeedback).where(RecommendationFeedback.rec_key == r.rec_key, RecommendationFeedback.decision == "ACCEPT").order_by(RecommendationFeedback.ts.desc())).first()
    if not fb:
        raise HTTPException(409, "Only accepted recommendations can have a realised outcome.")
    fb.realized_value_egp, fb.realized_revenue_egp, fb.outcome_note, fb.outcome_ts = body.realized_value_egp, body.realized_revenue_egp, body.note, now()
    db.commit()
    audit(db, u, "outcome_recorded", "recommendation", r.rec_key)
    return {"ok": True}


# ---------------------------------------------------------------- Action Center
class ActionIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    recommended_action: str = Field(min_length=3)
    department: str
    owner_email: str | None = None
    business_impact_egp: float = 0
    urgency: str = Field("MEDIUM", pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")


class ActionPatch(BaseModel):
    executed_on: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")   # real execution date if the status is updated later
    status: str | None = None
    owner_email: str | None = None
    department: str | None = None


def _ad(a: ActionItem):
    return dict(id=a.id, rec_key=a.rec_key, title=a.title, recommended_action=a.recommended_action, department=a.department, owner_email=a.owner_email,
                business_impact_egp=round(a.business_impact_egp), urgency=a.urgency, status=a.status, created_at=a.created_at.isoformat(), updated_at=a.updated_at.isoformat())


@router.get("/actions")
def list_actions(p: PageParams = Depends(), status: str | None = None, department: str | None = None, db: Session = Depends(get_db), u: User = Depends(require("actions"))):
    q = select(ActionItem)
    if status: q = q.where(ActionItem.status == status)
    if department: q = q.where(ActionItem.department == department)
    rows = [_ad(a) for a in db.scalars(q.order_by(ActionItem.created_at.desc()))]
    if u.role == "STORE_MANAGER":
        mine = {r.rec_key for r in db.scalars(select(Recommendation).where(Recommendation.location_id.in_(u.allowed_locations or [])))}
        rows = [r for r in rows if r["rec_key"] in mine or r["owner_email"] == u.email]
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ACTION_STATUSES}
    return paginate(rows, p, ("title", "department", "owner_email"), db, {"counts": counts})


@router.post("/actions", status_code=201)
def create_action(body: ActionIn, db: Session = Depends(get_db), u: User = Depends(require("decide"))):
    a = ActionItem(**body.model_dump(), status="NEW")
    a.owner_email = a.owner_email or u.email
    db.add(a); db.commit()
    audit(db, u, "action_created", "action", str(a.id))
    return _ad(a)


@router.patch("/actions/{action_id}")
def patch_action(action_id: int, body: ActionPatch, db: Session = Depends(get_db), u: User = Depends(require("decide"))):
    a = db.get(ActionItem, action_id)
    if not a:
        raise HTTPException(404, "Action not found.")
    if body.status:
        if body.status not in ACTION_STATUSES:
            raise HTTPException(422, f"Status must be one of: {', '.join(ACTION_STATUSES)}")
        a.status = body.status
    if body.owner_email: a.owner_email = body.owner_email
    if body.department: a.department = body.department
    a.updated_at = now()
    if body.status in ("IN_PROGRESS", "DONE") and a.rec_key:        # execution starts the before/after measurement window
        tr = db.scalars(select(DecisionTracking).where(DecisionTracking.rec_key == a.rec_key, DecisionTracking.status.in_(["APPROVED", "UNMEASURABLE"])).order_by(DecisionTracking.approved_at.desc())).first()
        if tr:
            outcomes.mark_executed(tr, datetime.fromisoformat(body.executed_on) if body.executed_on else None)
    db.commit()
    audit(db, u, "action_updated", "action", str(a.id), {"status": a.status})
    return _ad(a)


# ---------------------------------------------------------------- Alert Center
class AlertPatch(BaseModel):
    status: str = Field(pattern="^(READ|UNREAD|RESOLVED)$")


def _al(a: Alert):
    return dict(id=a.id, severity=a.severity, title=a.title, body=a.body, rec_key=a.rec_key, location_id=a.location_id, status=a.status, priority=a.priority, created_at=a.created_at.isoformat())


@router.get("/alerts")
def list_alerts(p: PageParams = Depends(), severity: str | None = Query(None, pattern="^(CRITICAL|WARNING|OPPORTUNITY)$"), status: str | None = None, db: Session = Depends(get_db), u: User = Depends(require("alerts"))):
    q = select(Alert).order_by(Alert.priority.desc())
    if severity: q = q.where(Alert.severity == severity)
    q = q.where(Alert.status == status) if status else q.where(Alert.status != "RESOLVED")
    rows = [_al(a) for a in db.scalars(q)]
    if u.role == "STORE_MANAGER":
        rows = [r for r in rows if r["location_id"] in (u.allowed_locations or [])]
    # users should not get hundreds of alerts: the table is already priority-limited; the unread count helps the bell badge
    unread = sum(1 for r in rows if r["status"] == "UNREAD")
    return paginate(rows, p, ("title", "body"), db, {"unread": unread})


@router.patch("/alerts/{alert_id}")
def patch_alert(alert_id: int, body: AlertPatch, db: Session = Depends(get_db), u: User = Depends(require("alerts"))):
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found.")
    if u.role == "STORE_MANAGER" and a.location_id not in (u.allowed_locations or []):
        raise HTTPException(403, "This alert is outside the locations you manage.")
    a.status = body.status; db.commit()
    return _al(a)


# ---------------------------------------------------------------- Value Realisation
@router.get("/value/summary", tags=["Value Realization"])
def value_summary(month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), u: User = Depends(require("value"))):
    month = month or datetime.utcnow().strftime("%Y-%m")
    fbs = db.scalars(select(RecommendationFeedback)).all()
    recs = db.scalars(select(Recommendation)).all()
    ym = lambda d: d.strftime("%Y-%m")
    gen = [r for r in recs if ym(r.created_at) == month]
    acc = [f for f in fbs if f.decision == "ACCEPT" and ym(f.ts) == month]
    rej = [f for f in fbs if f.decision == "REJECT" and ym(f.ts) == month]
    dfr = [f for f in fbs if f.decision == "DEFER" and ym(f.ts) == month]
    realised = [f for f in acc if f.realized_value_egp is not None]
    by = lambda types: sum(f.realized_value_egp or 0 for f in realised if f.impact_type in types)
    exp_by = lambda types: sum(f.expected_value_egp for f in acc if f.impact_type in types)
    series: dict = {}
    for f in fbs:
        if f.decision == "ACCEPT":
            s = series.setdefault(ym(f.ts), dict(month=ym(f.ts), accepted=0, expected=0.0, realized=0.0))
            s["accepted"] += 1; s["expected"] += f.expected_value_egp; s["realized"] += f.realized_value_egp or 0
    return {"month": month,
            "recommendations_generated": len(gen), "open_recommendations": sum(1 for r in recs if r.status == "OPEN"), "accepted": len(acc), "rejected": len(rej), "deferred": len(dfr),
            "acceptance_rate": round(len(acc) / max(len(acc) + len(rej), 1), 3),
            "expected_value_egp": round(sum(f.expected_value_egp for f in acc)), "realized_value_egp": round(sum(f.realized_value_egp or 0 for f in realised)),
            "outcomes_recorded": len(realised), "realization_rate": round(sum(f.realized_value_egp or 0 for f in realised) / max(sum(f.expected_value_egp for f in realised), 1), 3) if realised else None,
            "recovered_profit_egp": round(by({"profit_recovered", "profit_generated"})), "loss_avoided_egp": round(by({"loss_avoided", "capital_released"})),
            "revenue_protected_egp": round(sum(f.realized_revenue_egp or 0 for f in realised) or by({"profit_protected"})),
            "expected_by_type": {k: round(exp_by({k})) for k in ("profit_protected", "loss_avoided", "profit_recovered", "profit_generated", "capital_released")},
            "monthly": sorted(({**s, "expected": round(s["expected"]), "realized": round(s["realized"])} for s in series.values()), key=lambda x: x["month"]),
            "measured_outcomes": outcomes.summary(db),
            "note": "Realised values are entered by users after acting on a recommendation. Nothing is assumed: an accepted recommendation with no recorded outcome counts as expected value only.",
            "freshness": freshness(db)}


# ---------------------------------------------------------------- Decision tracking (approve -> execute -> measure)
def _td(r: DecisionTracking):
    return dict(id=r.id, rec_key=r.rec_key, plan=r.plan_name, category=r.category, product_id=r.product_id, location_id=r.location_id, department=r.department, status=r.status,
                approved_by=r.approved_by, approved_at=r.approved_at.isoformat(), data_as_of=r.data_as_of, executed_at=r.executed_at.isoformat() if r.executed_at else None,
                expected_value_egp=round(r.expected_value_egp), confidence=round(r.confidence, 2), window_days=r.measure_days, baseline=r.baseline, result=r.result,
                measured_at=r.measured_at.isoformat() if r.measured_at else None)


@router.get("/decisions/tracking", tags=["Decision Tracking"], summary="Approved decisions with their baseline, execution date and measured result")
def tracking(p: PageParams = Depends(), status: str | None = Query(None, pattern="^(APPROVED|EXECUTED|MEASURING|MEASURED|UNMEASURABLE)$"), db: Session = Depends(get_db), u: User = Depends(require("value"))):
    q = select(DecisionTracking).order_by(DecisionTracking.approved_at.desc())
    if status: q = q.where(DecisionTracking.status == status)
    rows = [_td(r) for r in db.scalars(q)]
    return paginate(rows, p, ("rec_key", "product_id", "department"), db, {"summary": outcomes.summary(db)})


@router.post("/decisions/tracking/measure", tags=["Decision Tracking"], summary="Measure every executed decision whose after-window is complete")
def measure_now(db: Session = Depends(get_db), u: User = Depends(require("decide"))):
    res = outcomes.measure_due(db)
    audit(db, u, "outcomes_measured", "decision_tracking", None, res)
    return {**res, "summary": outcomes.summary(db)}


class PlanApproveIn(BaseModel):
    comment: str | None = Field(None, max_length=1000)
    owner_email: str | None = None
    acknowledge_stale: bool = False


@router.post("/commercial/decision-plans/{name}/approve", tags=["Decision Tracking"], status_code=201, summary="Approve a whole plan: every decision becomes an action item with a tracked baseline")
def approve_plan(name: str, body: PlanApproveIn, db: Session = Depends(get_db), u: User = Depends(require("decide")), _r: User = Depends(require("recovery"))):
    plans = snap(db, "decision_plans") or {}
    plan = next((p for p in plans.get("plans", []) if p["name"] == name), None)
    if not plan:
        raise HTTPException(404, "No such plan. Use max_profit, balanced or min_risk after a data import.")
    f = _check_fresh(db, body.acknowledge_stale)
    approved, skipped = [], []
    for d in plan["decisions"]:
        r = db.scalars(select(Recommendation).where(Recommendation.rec_key == d["rec_key"])).first()
        if not r or r.status != "OPEN":
            skipped.append(dict(rec_key=d["rec_key"], reason="No longer open (already decided or expired)"))
            continue
        try:
            _get_rec(db, u, r.rec_key)
        except HTTPException as e:
            skipped.append(dict(rec_key=d["rec_key"], reason=e.detail))
            continue
        item, tr = _accept(db, u, r, body.comment or f"Approved with plan '{name}'", body.owner_email, plan_name=name, data_as_of=f.get("data_as_of"))
        approved.append(dict(rec_key=r.rec_key, action_item_id=item.id, tracking_id=tr.id))
    db.commit()
    audit(db, u, "plan_approved", "decision_plan", name, {"approved": len(approved), "skipped": len(skipped), "nominal_value_egp": plan["totals"]["nominal_value_egp"]})
    return dict(plan=name, approved=len(approved), skipped=len(skipped), items=approved, skipped_items=skipped,
                note="Nothing is executed automatically: each action item is for its department to carry out and mark In progress / Done, which starts the measurement window.")
