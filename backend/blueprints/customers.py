"""Customers — read by everyone, write by admins only."""
from flask import Blueprint, jsonify, request
from sqlalchemy import select

from auth import current_user, login_required, role_required
from db import session_scope
from logging_helpers import record
from models import Customer

bp = Blueprint("customers", __name__, url_prefix="/api/customers")


def _serialize(c: Customer) -> dict:
    return {"id": c.id, "name": c.name, "active": bool(c.active)}


@bp.get("")
@login_required
def list_customers():
    only_active = request.args.get("active", "1") == "1"
    with session_scope() as s:
        stmt = select(Customer)
        if only_active:
            stmt = stmt.where(Customer.active.is_(True))
        stmt = stmt.order_by(Customer.name)
        return jsonify([_serialize(c) for c in s.scalars(stmt)])


@bp.post("")
@role_required("admin")
def create_customer():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name is required"), 400
    with session_scope() as s:
        if s.scalar(select(Customer).where(Customer.name == name)):
            return jsonify(error="a customer with that name already exists"), 409
        c = Customer(name=name, created_by=current_user().id)
        s.add(c); s.flush()
        record(s, user_id=current_user().id, action="customer.create",
               entity_type="customer", entity_id=c.id, detail=name)
        return jsonify(_serialize(c)), 201


@bp.patch("/<int:customer_id>")
@role_required("admin")
def update_customer(customer_id: int):
    data = request.get_json(silent=True) or {}
    with session_scope() as s:
        c = s.get(Customer, customer_id)
        if c is None:
            return jsonify(error="not found"), 404
        if "name"   in data: c.name   = (data["name"] or "").strip() or c.name
        if "active" in data: c.active = bool(data["active"])
        record(s, user_id=current_user().id, action="customer.update",
               entity_type="customer", entity_id=c.id)
        s.flush()
        return jsonify(_serialize(c))


@bp.delete("/<int:customer_id>")
@role_required("admin")
def delete_customer(customer_id: int):
    with session_scope() as s:
        c = s.get(Customer, customer_id)
        if c is None:
            return jsonify(error="not found"), 404
        # Soft-delete so historical entries keep their customer name.
        c.active = False
        record(s, user_id=current_user().id, action="customer.deactivate",
               entity_type="customer", entity_id=c.id, detail=c.name)
    return "", 204
