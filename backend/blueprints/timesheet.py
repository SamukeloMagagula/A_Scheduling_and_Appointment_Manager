"""Monthly timesheet for one person."""
from calendar import monthrange
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import select

from auth import login_required
from db import session_scope
from models import TimeEntry, User

bp = Blueprint("timesheet", __name__, url_prefix="/api/timesheet")


def _parse_month(s: str) -> tuple[date, date]:
    y, m = s.split("-")
    first = date(int(y), int(m), 1)
    last  = date(int(y), int(m), monthrange(int(y), int(m))[1])
    return first, last


def _minutes(e: TimeEntry) -> int:
    s_, en = e.start_time, e.end_time
    return max(0, (en.hour * 60 + en.minute) - (s_.hour * 60 + s_.minute))


def _collect(user_id: int, month: str):
    first, last = _parse_month(month)
    with session_scope() as s:
        user = s.get(User, user_id)
        if user is None:
            return None
        rows = s.scalars(
            select(TimeEntry)
            .where(TimeEntry.user_id == user_id)
            .where(TimeEntry.entry_date >= first)
            .where(TimeEntry.entry_date <= last)
            .order_by(TimeEntry.entry_date, TimeEntry.start_time)
        ).all()

        totals = {"work": 0, "customer": 0, "standby": 0, "break": 0, "leave": 0}
        leave_days = set()
        days_out = []
        for e in rows:
            totals[e.entry_type] += _minutes(e)
            if e.entry_type == "leave":
                leave_days.add(e.entry_date)
            days_out.append({
                "date":     e.entry_date.isoformat(),
                "day":      e.entry_date.strftime("%a"),
                "start":    e.start_time.strftime("%H:%M"),
                "end":      e.end_time.strftime("%H:%M"),
                "project":  e.project.name if e.project else None,
                "customer": e.customer.name if e.customer else None,
                "hours":    round(_minutes(e) / 60, 2),
                "type":     e.entry_type,
                "notes":    e.notes,
            })

        return {
            "user":   {"id": user.id, "name": user.name, "email": user.email},
            "month":  month,
            "first":  first.isoformat(),
            "last":   last.isoformat(),
            "totals": {
                "total_hours":    round(sum(totals.values()) / 60, 2),
                "work_hours":     round(totals["work"]     / 60, 2),
                "customer_hours": round(totals["customer"] / 60, 2),
                "standby_hours":  round(totals["standby"]  / 60, 2),
                "break_hours":    round(totals["break"]    / 60, 2),
                "leave_days":     len(leave_days),
            },
            "rows":   days_out,
        }


@bp.get("")
@login_required
def monthly_timesheet():
    user_id = request.args.get("user_id", type=int)
    month   = request.args.get("month",   type=str)
    if not user_id or not month:
        return jsonify(error="user_id and month (YYYY-MM) are required"), 400
    data = _collect(user_id, month)
    if data is None:
        return jsonify(error="user not found"), 404
    return jsonify(data)


@bp.get("/export.csv")
@login_required
def monthly_timesheet_csv():
    user_id = request.args.get("user_id", type=int)
    month   = request.args.get("month",   type=str)
    if not user_id or not month:
        return "user_id and month (YYYY-MM) are required", 400
    data = _collect(user_id, month)
    if data is None:
        return "user not found", 404

    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Day", "Start", "End", "Project", "Customer", "Hours", "Type", "Notes"])
    for r in data["rows"]:
        w.writerow([r["date"], r["day"], r["start"], r["end"],
                    r["project"] or "", r["customer"] or "",
                    r["hours"], r["type"], r["notes"] or ""])
    w.writerow([])
    w.writerow(["Total hours", "", "", "", "", "", data["totals"]["total_hours"], "", ""])

    filename = f"timesheet_{data['user']['name'].replace(' ', '_')}_{month}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
