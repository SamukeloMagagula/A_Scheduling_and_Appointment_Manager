"""Projects — read by everyone, write by admins only."""
from flask import Blueprint, jsonify, request
from sqlalchemy import select

from auth import current_user, login_required, role_required
from db import session_scope
from logging_helpers import record
from models import Project

bp = Blueprint("projects", __name__, url_prefix="/api/projects")


def _serialize(p: Project) -> dict:
    return {"id": p.id, "name": p.name, "active": bool(p.active)}


@bp.get("")
@login_required
def list_projects():
    only_active = request.args.get("active", "1") == "1"
    with session_scope() as s:
        stmt = select(Project)
        if only_active:
            stmt = stmt.where(Project.active.is_(True))
        stmt = stmt.order_by(Project.name)
        return jsonify([_serialize(p) for p in s.scalars(stmt)])


@bp.post("")
@role_required("admin")
def create_project():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name is required"), 400
    with session_scope() as s:
        if s.scalar(select(Project).where(Project.name == name)):
            return jsonify(error="a project with that name already exists"), 409
        p = Project(name=name, created_by=current_user().id)
        s.add(p); s.flush()
        record(s, user_id=current_user().id, action="project.create",
               entity_type="project", entity_id=p.id, detail=name)
        return jsonify(_serialize(p)), 201


@bp.patch("/<int:project_id>")
@role_required("admin")
def update_project(project_id: int):
    data = request.get_json(silent=True) or {}
    with session_scope() as s:
        p = s.get(Project, project_id)
        if p is None:
            return jsonify(error="not found"), 404
        if "name"   in data: p.name   = (data["name"] or "").strip() or p.name
        if "active" in data: p.active = bool(data["active"])
        record(s, user_id=current_user().id, action="project.update",
               entity_type="project", entity_id=p.id)
        s.flush()
        return jsonify(_serialize(p))


@bp.delete("/<int:project_id>")
@role_required("admin")
def delete_project(project_id: int):
    with session_scope() as s:
        p = s.get(Project, project_id)
        if p is None:
            return jsonify(error="not found"), 404
        p.active = False
        record(s, user_id=current_user().id, action="project.deactivate",
               entity_type="project", entity_id=p.id, detail=p.name)
    return "", 204
