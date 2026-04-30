"""Admin JSON APIs."""
from __future__ import annotations

from flask import Blueprint, request

from ..models import UserSession
from ..services import user_service
from ..utils.decorators import admin_required, current_user
from ..utils.helpers import json_err, json_ok

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/summary", methods=["GET"])
@admin_required
def summary():
    users = user_service.list_users(limit=500)
    histories = user_service.list_recent_history(limit=500)
    ips = user_service.list_ip_usage(limit=500)
    return json_ok(
        {
            "counts": {
                "users": len(users),
                "active_users": sum(1 for u in users if u.is_active),
                "analyses": len(histories),
                "tracked_ips": len(ips),
            }
        }
    )


@admin_bp.route("/users", methods=["GET"])
@admin_required
def users():
    search = request.args.get("q", "").strip()
    return json_ok({"users": [u.to_public_dict() for u in user_service.list_users(search=search)]})


@admin_bp.route("/users/<int:user_id>/active", methods=["PATCH"])
@admin_required
def set_user_active(user_id: int):
    admin = current_user()
    data = request.get_json(silent=True) or {}
    user = user_service.set_user_active(user_id, bool(data.get("is_active")), admin.id)
    if not user:
        return json_err("User not found.", 404)
    return json_ok({"user": user.to_public_dict()})


@admin_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@admin_required
def set_user_role(user_id: int):
    admin = current_user()
    data = request.get_json(silent=True) or {}
    user = user_service.set_user_role(user_id, data.get("role", "user"), admin.id)
    if not user:
        return json_err("User not found or invalid role.", 400)
    return json_ok({"user": user.to_public_dict()})


@admin_bp.route("/history", methods=["GET"])
@admin_required
def history():
    rows = []
    for h in user_service.list_recent_history():
        rows.append(
            {
                "id": h.id,
                "user_id": h.user_id,
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
        )
    return json_ok({"history": rows})


@admin_bp.route("/sessions", methods=["GET"])
@admin_required
def sessions():
    rows = []
    for s in UserSession.query.order_by(UserSession.created_at.desc()).limit(200).all():
        rows.append(
            {
                "id": s.id,
                "user_id": s.user_id,
                "client_ip": s.client_ip,
                "user_agent": s.user_agent,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "revoked": s.revoked,
            }
        )
    return json_ok({"sessions": rows})


@admin_bp.route("/ip-usage", methods=["GET"])
@admin_required
def ip_usage():
    rows = [
        {
            "id": ip.id,
            "client_ip": ip.client_ip,
            "free_video_count": ip.free_video_count,
            "last_used_at": ip.last_used_at.isoformat() if ip.last_used_at else None,
            "blocked": ip.blocked,
        }
        for ip in user_service.list_ip_usage()
    ]
    return json_ok({"ip_usage": rows})


@admin_bp.route("/ip-usage/<path:client_ip>/reset", methods=["POST"])
@admin_required
def reset_ip(client_ip: str):
    admin = current_user()
    usage = user_service.reset_ip_usage(client_ip, admin.id)
    if not usage:
        return json_err("IP usage row not found.", 404)
    return json_ok({"message": "IP usage reset."})


@admin_bp.route("/ip-usage/<path:client_ip>/block", methods=["PATCH"])
@admin_required
def block_ip(client_ip: str):
    admin = current_user()
    data = request.get_json(silent=True) or {}
    usage = user_service.block_ip(client_ip, bool(data.get("blocked")), admin.id)
    return json_ok(
        {
            "client_ip": usage.client_ip,
            "blocked": usage.blocked,
            "free_video_count": usage.free_video_count,
        }
    )


@admin_bp.route("/logs", methods=["GET"])
@admin_required
def logs():
    rows = [
        {
            "id": l.id,
            "admin_id": l.admin_id,
            "action": l.action,
            "target_user_id": l.target_user_id,
            "details": l.details,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in user_service.list_recent_admin_logs()
    ]
    return json_ok({"logs": rows})
