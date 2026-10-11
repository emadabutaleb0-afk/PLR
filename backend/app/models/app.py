"""Application tables: users, audit, refresh runs, data quality, recommendations, feedback, actions, alerts, jobs."""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40))
    allowed_locations: Mapped[list | None] = mapped_column(JSON, nullable=True)  # None = all (STORE_MANAGER is restricted)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # metadata only, never raw records/passwords


class DataRefreshRun(Base):
    __tablename__ = "data_refresh_runs"
    run_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=now)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")  # RUNNING/SUCCESS/PARTIAL/FAILED
    mode: Mapped[str] = mapped_column(String(20), default="import")
    files_processed: Mapped[int] = mapped_column(Integer, default=0)
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    validation_warnings: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str] = mapped_column(String(40), default="extract")
    progress: Mapped[float] = mapped_column(Float, default=0)
    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(String(255), nullable=True)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(40), index=True)
    file: Mapped[str] = mapped_column(String(80))
    rule: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(10))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text)
    sample: Mapped[list | None] = mapped_column(JSON, nullable=True)


class QuarantineRow(Base):
    __tablename__ = "quarantine_rows"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(40), index=True)
    file: Mapped[str] = mapped_column(String(80))
    row_number: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class FileHealth(Base):
    __tablename__ = "file_health"
    file: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(40))
    present: Mapped[bool] = mapped_column(Boolean, default=True)
    rows_read: Mapped[int] = mapped_column(Integer, default=0)
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    null_rate: Mapped[float] = mapped_column(Float, default=0)
    duplicate_rate: Mapped[float] = mapped_column(Float, default=0)
    latest_data_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_modified: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="OK")  # OK/WARNING/FAILED/MISSING
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_class: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Recommendation(Base):
    """One explainable, ranked decision. Re-generated on every refresh; rec_key is stable across refreshes."""
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    rec_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    engine: Mapped[str] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)  # TRANSFER, REPLENISH, DISCOUNT, ...
    product_id: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    location_id: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(20), default="product")
    entity_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    problem: Mapped[str] = mapped_column(Text)
    why: Mapped[list] = mapped_column(JSON)
    action: Mapped[str] = mapped_column(Text)
    department: Mapped[str] = mapped_column(String(40))
    impact_type: Mapped[str] = mapped_column(String(40))  # revenue_protected / loss_avoided / profit_recovered / capital_released
    estimated_value_egp: Mapped[float] = mapped_column(Float, default=0)
    estimated_loss_egp: Mapped[float] = mapped_column(Float, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    urgency: Mapped[str] = mapped_column(String(10), default="MEDIUM")  # CRITICAL/HIGH/MEDIUM/LOW
    priority_score: Mapped[float] = mapped_column(Float, default=0, index=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)  # OPEN/ACCEPTED/REJECTED/DEFERRED/EXPIRED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    run_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    rec_key: Mapped[str] = mapped_column(String(160), index=True)
    user_id: Mapped[int] = mapped_column(Integer)
    user_email: Mapped[str] = mapped_column(String(255))
    decision: Mapped[str] = mapped_column(String(10))  # ACCEPT / REJECT / DEFER
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=now)
    expected_value_egp: Mapped[float] = mapped_column(Float, default=0)
    impact_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    realized_value_egp: Mapped[float | None] = mapped_column(Float, nullable=True)  # entered later
    realized_revenue_egp: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ActionItem(Base):
    __tablename__ = "action_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    rec_key: Mapped[str | None] = mapped_column(String(160), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    recommended_action: Mapped[str] = mapped_column(Text)
    department: Mapped[str] = mapped_column(String(40))
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_impact_egp: Mapped[float] = mapped_column(Float, default=0)
    urgency: Mapped[str] = mapped_column(String(10), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(20), default="NEW", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    severity: Mapped[str] = mapped_column(String(15), index=True)  # CRITICAL/WARNING/OPPORTUNITY
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    rec_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="UNREAD", index=True)  # UNREAD/READ/RESOLVED
    priority: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(15), default="QUEUED")  # QUEUED/RUNNING/SUCCESS/FAILED
    progress: Mapped[float] = mapped_column(Float, default=0)
    stage: Mapped[str | None] = mapped_column(String(60), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)


class ModelRecord(Base):
    __tablename__ = "model_registry"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), index=True)
    version: Mapped[str] = mapped_column(String(40))
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    algorithm: Mapped[str] = mapped_column(String(40))
    rows_train: Mapped[int] = mapped_column(Integer, default=0)
    rows_valid: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feature_importance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    train_window: Mapped[str | None] = mapped_column(String(80), nullable=True)
    path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    prediction_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AnalyticsSnapshot(Base):
    """Materialised analytics 'views' (JSON payloads) refreshed after every import."""
    __tablename__ = "analytics_snapshots"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    run_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class DecisionTracking(Base):
    """Life of one approved decision: APPROVED -> EXECUTED -> MEASURING -> MEASURED | UNMEASURABLE.
    `baseline` is what was known at approval time; the measured effect is stored separately from the engine's expected value."""
    __tablename__ = "decision_tracking"
    id: Mapped[int] = mapped_column(primary_key=True)
    rec_key: Mapped[str] = mapped_column(String(160), index=True)
    feedback_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    engine: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(40))
    product_id: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    location_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    department: Mapped[str] = mapped_column(String(40), default="")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    data_as_of: Mapped[str | None] = mapped_column(String(20), nullable=True)      # newest business data when it was approved
    expected_value_egp: Mapped[float] = mapped_column(Float, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    baseline: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    measure_days: Mapped[int] = mapped_column(Integer, default=28)
    status: Mapped[str] = mapped_column(String(20), default="APPROVED", index=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    measured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
