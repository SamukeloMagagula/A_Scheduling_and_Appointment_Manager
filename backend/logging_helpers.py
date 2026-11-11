"""Small helper so every write path records an audit row the same way."""
from sqlalchemy.orm import Session

from models import ActivityLog


def record(session: Session, *, user_id: int | None, action: str,
           entity_type: str | None = None, entity_id: int | None = None,
           detail: str | None = None) -> None:
    session.add(ActivityLog(
        user_id=user_id, action=action,
        entity_type=entity_type, entity_id=entity_id, detail=detail,
    ))
