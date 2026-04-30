from __future__ import annotations

import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


class Config:
    BASE_DIR = BASE_DIR
    INSTANCE_DIR = INSTANCE_DIR
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
    SECRET_KEY = os.environ.get("DDEFENDER_SECRET_KEY") or secrets.token_hex(32)
    DEBUG = os.environ.get("DDEFENDER_DEBUG", "1").lower() in {"1", "true", "yes"}
    SESSION_COOKIE_NAME = "ddefender_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DDEFENDER_DATABASE_URI",
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'deepfake_defender.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get("DDEFENDER_MAX_UPLOAD_MB", "512")) * 1024 * 1024
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_RESET_TOKEN_TTL_MINUTES = 30
    DEFAULT_ADMIN_EMAIL = os.environ.get("DDEFENDER_ADMIN_EMAIL", "admin@deepfakedefender.local")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DDEFENDER_ADMIN_PASSWORD", "Admin@12345")
    DEFAULT_ADMIN_NAME = os.environ.get("DDEFENDER_ADMIN_NAME", "Site Admin")
    SMTP_HOST = os.environ.get("DDEFENDER_SMTP_HOST")
    SMTP_PORT = int(os.environ.get("DDEFENDER_SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("DDEFENDER_SMTP_USER")
    SMTP_PASSWORD = os.environ.get("DDEFENDER_SMTP_PASSWORD")
    SMTP_FROM = os.environ.get("DDEFENDER_SMTP_FROM", "no-reply@deepfakedefender.local")
    SMTP_USE_TLS = os.environ.get("DDEFENDER_SMTP_TLS", "1").lower() in {"1", "true", "yes"}
    APP_PUBLIC_URL = os.environ.get("DDEFENDER_PUBLIC_URL", "http://localhost:5000")
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get("DDEFENDER_GOOGLE_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("DDEFENDER_GOOGLE_CLIENT_SECRET")
