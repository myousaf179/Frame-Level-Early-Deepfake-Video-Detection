from __future__ import annotations
from functools import wraps
from flask import g, jsonify, redirect, request, session
from ..extensions import db
from ..models import User


def current_user():
    if hasattr(g, "current_user"):
        return g.current_user
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if user and not user.is_active:
        user = None
    g.current_user = user
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Authentication required"}), 401
            return redirect("/login.html")
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"ok": False, "error": "Authentication required"}), 401
        if not user.is_admin:
            return jsonify({"ok": False, "error": "Admin privileges required"}), 403
        return view(*args, **kwargs)
    return wrapped
