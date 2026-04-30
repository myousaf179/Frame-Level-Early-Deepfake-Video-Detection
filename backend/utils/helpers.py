from __future__ import annotations
import secrets
from flask import jsonify


def get_client_ip(request):
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return forwarded or request.headers.get("X-Real-IP") or request.remote_addr or "0.0.0.0"


def new_token(nbytes=32):
    return secrets.token_urlsafe(nbytes)


def json_ok(payload=None, status=200):
    body = {"ok": True}
    if payload:
        body.update(payload)
    return jsonify(body), status


def json_err(message, status=400, **extra):
    body = {"ok": False, "error": message}
    body.update(extra)
    return jsonify(body), status
