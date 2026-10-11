from app.models.app import AuditLog, User


def audit(db, user: User | None, action: str, entity: str | None = None, entity_id: str | None = None, detail: dict | None = None):
    """Business-action audit trail. Metadata only - never passwords, tokens or raw records."""
    db.add(AuditLog(user_id=user.id if user else None, user_email=user.email if user else None, action=action, entity=entity, entity_id=entity_id, detail=detail))
    db.commit()
