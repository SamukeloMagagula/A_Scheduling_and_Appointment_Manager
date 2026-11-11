"""Activity log — manager/admin only."""
from flask import Blueprint, jsonify, request
from sqlalchemy import select

from auth import role_required
from db import session_scope
from models import ActivityLog, User

bp = Blueprint("logs", __name__, url_prefix="/api/logs")


@bp.get("")
@role_required("manager", "admin")
def list_logs():
    limit  = min(500, request.args.get("limit", default=200, type=int))
    search = (request.args.get("q") or "").strip().lower()

    with session_scope() as s:
        rows = s.scalars(
            select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)
        ).all()
        # Hydrate user names in one small extra query.
        user_ids = {r.user_id for r in rows if r.user_id is not None}
        names = {}
        if user_ids:
            users = s.scalars(select(User).where(User.id.in_(user_ids))).all()
            names = {u.id: u.name for u in users}

        payload = [{
            "id":          r.id,
            "when":        r.created_at.isoformat(sep=" ", timespec="seconds"),
            "user_id":     r.user_id,
            "user":        names.get(r.user_id, "—"),
            "action":      r.action,
            "entity_type": r.entity_type,
            "entity_id":   r.entity_id,
            "detail":      r.detail,
        } for r in rows]

        if search:
            payload = [
                r for r in payload
                if search in (r["user"] or "").lower()
                or search in (r["action"] or "").lower()
                or search in (r["detail"] or "").lower()
            ]
        return jsonify(payload)
