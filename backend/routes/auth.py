"""Authentication JSON APIs."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import User
from ..services import auth_service, email_service, user_service
from ..utils.decorators import current_user, login_required
from ..utils.helpers import get_client_ip, json_err, json_ok
from ..utils.validators import normalize_email

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/me", methods=["GET"])
def me():
    user = current_user()
    ip = get_client_ip(request)
    payload = {
        "user": user.to_public_dict() if user else None,
        "guest_usage": {
            "client_ip": ip,
            "free_remaining": user_service.guest_remaining_quota(ip),
        },
    }
    return json_ok(payload)


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    user, err = auth_service.signup(
        name=data.get("name", ""),
        email=data.get("email", ""),
        password=data.get("password", ""),
    )
    if err:
        return json_err(err, 400)
    auth_service.login(data.get("email", ""), data.get("password", ""), request)
    return json_ok({"user": user.to_public_dict(), "message": "Account created."}, 201)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    user, err = auth_service.login(data.get("email", ""), data.get("password", ""), request)
    if err:
        return json_err(err, 401)
    return json_ok({"user": user.to_public_dict(), "message": "Logged in."})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    auth_service.logout()
    return json_ok({"message": "Logged out."})


@auth_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    user = current_user()
    history = [
        {
            "id": h.id,
            "file_name": h.file_name,
            "mode": h.mode,
            "result_label": h.result_label,
            "fake_count": h.fake_count,
            "real_count": h.real_count,
            "suspicious_count": h.suspicious_count,
            "confidence": h.confidence,
            "processing_time": h.processing_time,
            "client_ip": h.client_ip,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in user_service.get_user_history(user.id)
    ]
    return json_ok({"user": user.to_public_dict(), "history": history})


@auth_bp.route("/profile", methods=["PATCH"])
@login_required
def update_profile():
    user = current_user()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if len(name) < 2:
        return json_err("Name must be at least 2 characters.", 400)
    user.name = name[:120]
    db.session.commit()
    return json_ok({"user": user.to_public_dict(), "message": "Profile updated."})


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    token, err = auth_service.request_password_reset(data.get("email", ""))
    if err:
        return json_err(err, 400)
    # Privacy-safe default response.
    payload = {"message": "If the email exists, a reset link has been sent."}
    if token:
        user = db.session.get(User, token.user_id)
        delivery = email_service.send_password_reset(user, token)
        payload.update(delivery)
    return json_ok(payload)


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    user, err = auth_service.consume_reset_token(
        token_value=data.get("token", ""),
        new_password=data.get("password", ""),
    )
    if err:
        return json_err(err, 400)
    return json_ok({"message": "Password reset successfully.", "email": user.email})


@auth_bp.route("/google/start", methods=["GET"])
def google_start():
    """Safe placeholder unless the user configures free Google OAuth credentials."""
    from flask import current_app

    if not current_app.config.get("GOOGLE_OAUTH_CLIENT_ID"):
        return json_err(
            "Google login is not configured. Add DDEFENDER_GOOGLE_CLIENT_ID and DDEFENDER_GOOGLE_CLIENT_SECRET to enable it.",
            501,
            configured=False,
        )
    return json_err(
        "Google OAuth credentials are present, but the OAuth callback flow is intentionally left as a safe integration point.",
        501,
        configured=True,
    )
