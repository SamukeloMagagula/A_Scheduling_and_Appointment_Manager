"""Users: who I am, and a search for the toolbar."""
from flask import Blueprint, jsonify, request
from sqlalchemy import or_, select

from auth import current_user, login_required
from db import session_scope
from models import User

bp = Blueprint("users", __name__, url_prefix="/api")


def _serialize(u: User) -> dict:
    return {
        "id":      u.id,
        "name":    u.name,
        "email":   u.email,
        "role":    u.role,
        "team_id": u.team_id,
        "team":    u.team.name if u.team else None,
    }


@bp.get("/me")
@login_required
def me():
    return jsonify(_serialize(current_user()))


@bp.get("/users")
@login_required
def search_users():
    team_id = request.args.get("team_id", type=int)
    q       = (request.args.get("q") or "").strip()

    with session_scope() as s:
        stmt = select(User)
        if team_id is not None:
            stmt = stmt.where(User.team_id == team_id)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
        stmt = stmt.order_by(User.name).limit(50)
        return jsonify([_serialize(u) for u in s.scalars(stmt)])
