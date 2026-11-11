"""Department rollup for the Department screen's team cards."""
from datetime import date, datetime, time, timedelta

from flask import Blueprint, jsonify
from sqlalchemy import func, select

from auth import login_required
from db import session_scope
from models import Team, TimeEntry, User

bp = Blueprint("department", __name__, url_prefix="/api/department")


def _week_bounds(today: date):
    start = today - timedelta(days=today.weekday())
    end   = start + timedelta(days=6)
    return start, end


@bp.get("")
@login_required
def department_overview():
    today = date.today()
    now   = datetime.now().time()
    wk_start, wk_end = _week_bounds(today)

    with session_scope() as s:
        teams = s.scalars(select(Team).order_by(Team.name)).all()

        # One pass over this week's entries to drive every per-team roll-up.
        all_entries = s.scalars(
            select(TimeEntry)
            .where(TimeEntry.entry_date >= wk_start)
            .where(TimeEntry.entry_date <= wk_end)
        ).all()

        by_user: dict[int, list[TimeEntry]] = {}
        for e in all_entries:
            by_user.setdefault(e.user_id, []).append(e)

        def busy_now(u: User) -> str:
            # Status right now: what's the person doing at this moment?
            if u.id not in by_user:
                return "free"
            todays = [e for e in by_user[u.id] if e.entry_date == today]
            for e in todays:
                if e.start_time <= now < e.end_time:
                    if e.entry_type == "leave":    return "leave"
                    if e.entry_type == "standby":  return "standby"
                    return "busy"
            # On leave for the whole day counts even outside working hours.
            if any(e.entry_type == "leave" for e in todays):
                return "leave"
            return "free"

        def minutes(entries: list[TimeEntry]) -> int:
            total = 0
            for e in entries:
                s_ = e.start_time; en = e.end_time
                total += (en.hour * 60 + en.minute) - (s_.hour * 60 + s_.minute)
            return max(0, total)

        teams_payload = []
        dept_people = 0
        dept_minutes = 0
        dept_standby = 0

        for t in teams:
            members = t.members
            dept_people += len(members)
            team_min = sum(minutes(by_user.get(u.id, [])) for u in members)
            dept_minutes += team_min

            statuses = [busy_now(u) for u in members]
            on_standby_week = sum(
                1 for u in members
                if any(e.entry_type == "standby" for e in by_user.get(u.id, []))
            )
            dept_standby += on_standby_week

            teams_payload.append({
                "id":              t.id,
                "name":            t.name,
                "member_count":    len(members),
                "free_now":        statuses.count("free"),
                "busy_now":        statuses.count("busy"),
                "standby_now":     statuses.count("standby"),
                "on_leave_now":    statuses.count("leave"),
                "hours_this_week": round(team_min / 60, 1),
                "on_standby_week": on_standby_week,
            })

        return jsonify({
            "week_start":          wk_start.isoformat(),
            "week_end":            wk_end.isoformat(),
            "team_count":          len(teams),
            "people_count":        dept_people,
            "hours_this_week":     round(dept_minutes / 60, 1),
            "on_standby_this_week": dept_standby,
            "teams":               teams_payload,
        })
