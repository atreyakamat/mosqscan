"""Audit logging utility."""
from __future__ import annotations

import logging
from sqlalchemy.orm import Session
from app.db.models import AuditEvent

logger = logging.getLogger(__name__)


def log_audit_event(
    db: Session,
    event_type: str,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditEvent:
    """Record an audit trail event."""
    try:
        event = AuditEvent(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except Exception:
        logger.exception("Failed to write audit event")
        db.rollback()
        return None
