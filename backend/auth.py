"""Stubbed authentication.

Until real sign-in lands, every request pretends to be logged in as
Config.STUB_USER_ID. Swap `current_user` for a session-reading version
later and nothing else in the codebase changes.
"""
from functools import wraps

from flask import g, jsonify, request
from sqlalchemy.orm import Session

from config import Config
from db import SessionLocal
from models import User


def _load_stub_user(s: Session) -> User | None:
    uid = Config.STUB_USER_ID
    return s.get(User, uid)


def load_current_user():
    """Flask before_request: stash the current user on `g`."""
    s = SessionLocal()
    try:
        g.current_user = _load_stub_user(s)
    finally:
        s.close()


def current_user() -> User | None:
    return getattr(g, "current_user", None)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return jsonify(error="not authenticated"), 401
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles: str):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = current_user()
            if u is None:
                return jsonify(error="not authenticated"), 401
            if u.role not in roles:
                return jsonify(error="forbidden"), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco
