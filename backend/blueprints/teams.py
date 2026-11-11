"""Teams + the week grid behind the Team Calendar screen."""
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from auth import login_required
from db import session_scope
from models import Team, TimeEntry, User

bp = Blueprint("teams", __name__, url_prefix="/api/teams")


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


@bp.get("")
@login_required
def list_teams():
    with session_scope() as s:
        rows = s.scalars(select(Team).order_by(Team.name)).all()
        return jsonify([
            {"id": t.id, "name": t.name, "department_id": t.department_id,
             "member_count": len(t.members)}
            for t in rows
        ])


@bp.get("/<int:team_id>/week")
@login_required
def team_week(team_id: int):
    start = request.args.get("start", type=str)
    try:
        start_d = _monday_of(_parse_date(start)) if start else _monday_of(date.today())
    except ValueError:
        return jsonify(error="start must be YYYY-MM-DD"), 400
    end_d = start_d + timedelta(days=6)

    with session_scope() as s:
        team = s.get(Team, team_id)
        if team is None:
            return jsonify(error="team not found"), 404

        members = sorted(team.members, key=lambda u: u.name)
        member_ids = [m.id for m in members]

        entries = []
        if member_ids:
            rows = s.scalars(
                select(TimeEntry)
                .where(TimeEntry.user_id.in_(member_ids))
                .where(TimeEntry.entry_date >= start_d)
                .where(TimeEntry.entry_date <= end_d)
                .order_by(TimeEntry.entry_date, TimeEntry.start_time)
            ).all()
            entries = [{
                "id":       e.id,
                "user_id":  e.user_id,
                "date":     e.entry_date.isoformat(),
                "start":    e.start_time.strftime("%H:%M"),
                "end":      e.end_time.strftime("%H:%M"),
                "type":     e.entry_type,
                "project":  e.project.name if e.project else None,
                "customer": e.customer.name if e.customer else None,
            } for e in rows]

        return jsonify({
            "team":    {"id": team.id, "name": team.name},
            "start":   start_d.isoformat(),
            "end":     end_d.isoformat(),
            "members": [{"id": u.id, "name": u.name, "role": u.role} for u in members],
            "entries": entries,
        })
