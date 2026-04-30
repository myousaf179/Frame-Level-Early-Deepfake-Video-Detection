from __future__ import annotations

from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default="user", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    auth_provider = db.Column(db.String(20), default="local", nullable=False)
    google_sub = db.Column(db.String(255), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0, nullable=False)

    @property
    def is_admin(self):
        return self.role == "admin"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, password):
        return bool(self.password_hash and check_password_hash(self.password_hash, password))

    def to_public_dict(self):
        return {
            "id": self.id, "name": self.name, "email": self.email, "role": self.role,
            "is_active": self.is_active, "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "login_count": self.login_count,
        }


class UserSession(db.Model):
    __tablename__ = "sessions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_agent = db.Column(db.String(500))
    client_ip = db.Column(db.String(64), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)


class AnalysisHistory(db.Model):
    __tablename__ = "analysis_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    file_name = db.Column(db.String(255), nullable=False)
    mode = db.Column(db.String(20), default="early", nullable=False)
    result_label = db.Column(db.String(40), default="UNKNOWN", nullable=False)
    fake_count = db.Column(db.Integer, default=0, nullable=False)
    real_count = db.Column(db.Integer, default=0, nullable=False)
    suspicious_count = db.Column(db.Integer, default=0, nullable=False)
    confidence = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processing_time = db.Column(db.Float, default=0.0, nullable=False)
    video_duration = db.Column(db.Float, default=0.0, nullable=False)
    client_ip = db.Column(db.String(64), index=True)
    run_id = db.Column(db.String(64), index=True)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)

    @staticmethod
    def default_expiry(minutes=30):
        return datetime.utcnow() + timedelta(minutes=minutes)


class AdminLog(db.Model):
    __tablename__ = "admin_logs"
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = db.Column(db.String(80), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class IpUsage(db.Model):
    __tablename__ = "ip_usage"
    id = db.Column(db.Integer, primary_key=True)
    client_ip = db.Column(db.String(64), unique=True, nullable=False, index=True)
    free_video_count = db.Column(db.Integer, default=0, nullable=False)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    blocked = db.Column(db.Boolean, default=False, nullable=False)


class SubscriptionPlan(db.Model):
    __tablename__ = "subscription_plans"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    monthly_quota = db.Column(db.Integer, default=0, nullable=False)
    price_cents = db.Column(db.Integer, default=0, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class UserSubscription(db.Model):
    __tablename__ = "user_subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("subscription_plans.id"), nullable=False)
    used_count = db.Column(db.Integer, default=0, nullable=False)
    period_start = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
