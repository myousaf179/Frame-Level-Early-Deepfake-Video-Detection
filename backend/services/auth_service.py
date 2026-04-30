from __future__ import annotations
from datetime import datetime, timedelta
from flask import current_app, session
from ..extensions import db
from ..models import PasswordResetToken, User, UserSession
from ..utils.helpers import get_client_ip, new_token
from ..utils.validators import is_valid_email, normalize_email, password_problems


def signup(name, email, password):
    name = (name or "").strip()
    email = normalize_email(email)
    if len(name) < 2:
        return None, "Please enter a valid name."
    if not is_valid_email(email):
        return None, "Please enter a valid email address."
    problems = password_problems(password, current_app.config["PASSWORD_MIN_LENGTH"])
    if problems:
        return None, " ".join(problems)
    if User.query.filter_by(email=email).first():
        return None, "An account already exists for this email."
    user = User(name=name[:120], email=email, role="user", is_active=True, auth_provider="local")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, None


def login(email, password, request_obj=None):
    user = User.query.filter_by(email=normalize_email(email)).first()
    if not user or not user.check_password(password):
        return None, "Invalid email or password."
    if not user.is_active:
        return None, "This account has been disabled."
    user.last_login = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    record = UserSession(
        user_id=user.id,
        session_id=new_token(24),
        user_agent=request_obj.user_agent.string if request_obj else None,
        client_ip=get_client_ip(request_obj) if request_obj else None,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.session.add(record)
    db.session.commit()
    session.clear()
    session["user_id"] = user.id
    session["session_record_id"] = record.id
    session.permanent = True
    return user, None


def logout():
    sid = session.get("session_record_id")
    if sid:
        record = db.session.get(UserSession, sid)
        if record:
            record.revoked = True
            db.session.commit()
    session.clear()


def request_password_reset(email):
    email = normalize_email(email)
    if not is_valid_email(email):
        return None, "Please provide a valid email."
    user = User.query.filter_by(email=email).first()
    if not user:
        return None, None
    PasswordResetToken.query.filter_by(user_id=user.id, used=False).update({"used": True})
    token = PasswordResetToken(
        user_id=user.id,
        token=new_token(32),
        expires_at=PasswordResetToken.default_expiry(current_app.config["PASSWORD_RESET_TOKEN_TTL_MINUTES"]),
    )
    db.session.add(token)
    db.session.commit()
    return token, None


def consume_reset_token(token_value, new_password):
    problems = password_problems(new_password, current_app.config["PASSWORD_MIN_LENGTH"])
    if problems:
        return None, " ".join(problems)
    token = PasswordResetToken.query.filter_by(token=token_value).first()
    if not token or token.used:
        return None, "This reset link is invalid or already used."
    if token.expires_at < datetime.utcnow():
        return None, "This reset link has expired."
    user = db.session.get(User, token.user_id)
    if not user or not user.is_active:
        return None, "Account is unavailable."
    user.set_password(new_password)
    token.used = True
    db.session.commit()
    return user, None


def ensure_default_admin(app):
    if User.query.filter_by(role="admin").first():
        return
    user = User(
        name=app.config["DEFAULT_ADMIN_NAME"],
        email=normalize_email(app.config["DEFAULT_ADMIN_EMAIL"]),
        role="admin",
        is_active=True,
        auth_provider="local",
    )
    user.set_password(app.config["DEFAULT_ADMIN_PASSWORD"])
    db.session.add(user)
    db.session.commit()
