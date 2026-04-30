from __future__ import annotations
from datetime import datetime
from flask import current_app
from ..extensions import db
from ..models import AdminLog, AnalysisHistory, IpUsage, SubscriptionPlan, User


def ensure_default_plans():
    plans = [
        ("free", "Free", 5, 0),
        ("pro", "Pro", 100, 900),
        ("premium", "Premium", 0, 2900),
    ]
    for code, name, quota, price in plans:
        if not SubscriptionPlan.query.filter_by(code=code).first():
            db.session.add(SubscriptionPlan(code=code, name=name, monthly_quota=quota, price_cents=price, is_active=True))
    db.session.commit()


def get_or_create_ip_usage(client_ip):
    usage = IpUsage.query.filter_by(client_ip=client_ip).first()
    if not usage:
        usage = IpUsage(client_ip=client_ip, free_video_count=0, last_used_at=datetime.utcnow())
        db.session.add(usage)
        db.session.commit()
    return usage


def guest_remaining_quota(client_ip):
    get_or_create_ip_usage(client_ip)
    return "unlimited"


def can_guest_analyze(client_ip):
    usage = get_or_create_ip_usage(client_ip)
    return not usage.blocked


def increment_guest_usage(client_ip):
    usage = get_or_create_ip_usage(client_ip)
    usage.free_video_count += 1
    usage.last_used_at = datetime.utcnow()
    db.session.commit()
    return usage.free_video_count


def record_analysis(**kwargs):
    row = AnalysisHistory(**kwargs)
    db.session.add(row)
    db.session.commit()
    return row


def get_user_history(user_id, limit=50):
    return AnalysisHistory.query.filter_by(user_id=user_id).order_by(AnalysisHistory.created_at.desc()).limit(limit).all()


def list_users(search="", limit=100):
    q = User.query
    if search:
        like = f"%{search}%"
        q = q.filter((User.email.ilike(like)) | (User.name.ilike(like)))
    return q.order_by(User.created_at.desc()).limit(limit).all()


def set_user_active(target_user_id, active, admin_id):
    user = db.session.get(User, target_user_id)
    if not user:
        return None
    user.is_active = active
    db.session.add(AdminLog(admin_id=admin_id, action="unblock_user" if active else "block_user", target_user_id=target_user_id))
    db.session.commit()
    return user


def set_user_role(target_user_id, role, admin_id):
    if role not in {"user", "admin"}:
        return None
    user = db.session.get(User, target_user_id)
    if not user:
        return None
    user.role = role
    db.session.add(AdminLog(admin_id=admin_id, action="set_role", target_user_id=target_user_id, details=role))
    db.session.commit()
    return user


def list_recent_history(limit=100):
    return AnalysisHistory.query.order_by(AnalysisHistory.created_at.desc()).limit(limit).all()


def list_recent_admin_logs(limit=100):
    return AdminLog.query.order_by(AdminLog.created_at.desc()).limit(limit).all()


def list_ip_usage(limit=200):
    return IpUsage.query.order_by(IpUsage.last_used_at.desc()).limit(limit).all()


def reset_ip_usage(client_ip, admin_id):
    usage = IpUsage.query.filter_by(client_ip=client_ip).first()
    if not usage:
        return None
    usage.free_video_count = 0
    usage.blocked = False
    db.session.add(AdminLog(admin_id=admin_id, action="reset_ip_usage", details=client_ip))
    db.session.commit()
    return usage


def block_ip(client_ip, blocked, admin_id):
    usage = get_or_create_ip_usage(client_ip)
    usage.blocked = blocked
    db.session.add(AdminLog(admin_id=admin_id, action="block_ip" if blocked else "unblock_ip", details=client_ip))
    db.session.commit()
    return usage
