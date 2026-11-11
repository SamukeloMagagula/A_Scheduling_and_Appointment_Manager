"""Time entries. Owner-only edits enforced server-side."""
from datetime import date, datetime, time, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import and_, select

from auth import current_user, login_required
from db import session_scope
from logging_helpers import record
from models import ENTRY_TYPES, Customer, Project, TimeEntry, User

bp = Blueprint("entries", __name__, url_prefix="/api/entries")


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _parse_time(s: str) -> time:
    # Accept "HH:MM" or "HH:MM:SS".
    fmt = "%H:%M:%S" if s.count(":") == 2 else "%H:%M"
    return datetime.strptime(s, fmt).time()


def _serialize(e: TimeEntry) -> dict:
    return {
        "id":           e.id,
        "user_id":      e.user_id,
        "date":         e.entry_date.isoformat(),
        "start":        e.start_time.strftime("%H:%M"),
        "end":          e.end_time.strftime("%H:%M"),
        "type":         e.entry_type,
        "project_id":   e.project_id,
        "project":      e.project.name if e.project else None,
        "customer_id":  e.customer_id,
        "customer":     e.customer.name if e.customer else None,
        "notes":        e.notes,
    }


def _overlap_exists(session, *, user_id: int, d: date, start: time, end: time,
                    ignore_id: int | None = None) -> bool:
    q = select(TimeEntry).where(
        TimeEntry.user_id == user_id,
        TimeEntry.entry_date == d,
        and_(TimeEntry.start_time < end, TimeEntry.end_time > start),
    )
    if ignore_id is not None:
        q = q.where(TimeEntry.id != ignore_id)
    return session.scalar(q.limit(1)) is not None


# ---------- list ----------
@bp.get("")
@login_required
def list_entries():
    user_id = request.args.get("user_id", type=int) or current_user().id
    d_from  = request.args.get("from", type=str)
    d_to    = request.args.get("to",   type=str)

    with session_scope() as s:
        q = select(TimeEntry).where(TimeEntry.user_id == user_id)
        if d_from:
            q = q.where(TimeEntry.entry_date >= _parse_date(d_from))
        if d_to:
            q = q.where(TimeEntry.entry_date <= _parse_date(d_to))
        q = q.order_by(TimeEntry.entry_date, TimeEntry.start_time)
        rows = s.scalars(q).all()
        return jsonify([_serialize(e) for e in rows])


# ---------- create ----------
@bp.post("")
@login_required
def create_entry():
    data = request.get_json(silent=True) or {}
    me   = current_user()

    try:
        d     = _parse_date(data["date"])
        start = _parse_time(data["start"])
        end   = _parse_time(data["end"])
        etype = data["type"]
    except (KeyError, ValueError):
        return jsonify(error="date, start, end and type are required"), 400

    if etype not in ENTRY_TYPES:
        return jsonify(error=f"type must be one of {ENTRY_TYPES}"), 400
    if end <= start:
        return jsonify(error="end must be after start"), 400

    proj_id = data.get("project_id")
    cust_id = data.get("customer_id")
    notes   = (data.get("notes") or "").strip() or None

    with session_scope() as s:
        if proj_id is not None and s.get(Project, proj_id) is None:
            return jsonify(error="unknown project"), 400
        if cust_id is not None and s.get(Customer, cust_id) is None:
            return jsonify(error="unknown customer"), 400
        if _overlap_exists(s, user_id=me.id, d=d, start=start, end=end):
            return jsonify(error="this overlaps another entry on the same day"), 409

        e = TimeEntry(
            user_id=me.id, entry_date=d, start_time=start, end_time=end,
            entry_type=etype, project_id=proj_id, customer_id=cust_id, notes=notes,
        )
        s.add(e)
        s.flush()
        record(s, user_id=me.id, action="entry.create",
               entity_type="time_entry", entity_id=e.id,
               detail=f"{d.isoformat()} {start}-{end} {etype}")
        s.refresh(e)
        return jsonify(_serialize(e)), 201


# ---------- read / update / delete ----------
@bp.get("/<int:entry_id>")
@login_required
def get_entry(entry_id: int):
    with session_scope() as s:
        e = s.get(TimeEntry, entry_id)
        if e is None:
            return jsonify(error="not found"), 404
        return jsonify(_serialize(e))


@bp.patch("/<int:entry_id>")
@login_required
def update_entry(entry_id: int):
    me   = current_user()
    data = request.get_json(silent=True) or {}

    with session_scope() as s:
        e = s.get(TimeEntry, entry_id)
        if e is None:
            return jsonify(error="not found"), 404
        if e.user_id != me.id:
            return jsonify(error="you can only edit your own entries"), 403

        if "date"  in data: e.entry_date = _parse_date(data["date"])
        if "start" in data: e.start_time = _parse_time(data["start"])
        if "end"   in data: e.end_time   = _parse_time(data["end"])
        if "type"  in data:
            if data["type"] not in ENTRY_TYPES:
                return jsonify(error=f"type must be one of {ENTRY_TYPES}"), 400
            e.entry_type = data["type"]
        if "project_id"  in data: e.project_id  = data["project_id"]
        if "customer_id" in data: e.customer_id = data["customer_id"]
        if "notes"       in data: e.notes       = (data["notes"] or "").strip() or None

        if e.end_time <= e.start_time:
            return jsonify(error="end must be after start"), 400
        if _overlap_exists(s, user_id=e.user_id, d=e.entry_date,
                           start=e.start_time, end=e.end_time, ignore_id=e.id):
            return jsonify(error="this overlaps another entry on the same day"), 409

        record(s, user_id=me.id, action="entry.update",
               entity_type="time_entry", entity_id=e.id)
        s.flush()
        s.refresh(e)
        return jsonify(_serialize(e))


@bp.delete("/<int:entry_id>")
@login_required
def delete_entry(entry_id: int):
    me = current_user()
    with session_scope() as s:
        e = s.get(TimeEntry, entry_id)
        if e is None:
            return jsonify(error="not found"), 404
        if e.user_id != me.id:
            return jsonify(error="you can only delete your own entries"), 403
        s.delete(e)
        record(s, user_id=me.id, action="entry.delete",
               entity_type="time_entry", entity_id=entry_id)
    return "", 204
