"""HTML page routes."""
from __future__ import annotations

import os

from flask import Blueprint, current_app, send_from_directory

pages_bp = Blueprint("pages", __name__)


def _base_dir() -> str:
    return current_app.config["BASE_DIR"]


@pages_bp.route("/")
def index():
    return send_from_directory(_base_dir(), "index.html")


@pages_bp.route("/index.html")
def index_html():
    return send_from_directory(_base_dir(), "index.html")


@pages_bp.route("/login.html")
def login_page():
    return send_from_directory(_base_dir(), "login.html")


@pages_bp.route("/signup.html")
def signup_page():
    return send_from_directory(_base_dir(), "signup.html")


@pages_bp.route("/subscription.html")
def subscription_page():
    return send_from_directory(_base_dir(), "subscription.html")


@pages_bp.route("/forgot-password.html")
def forgot_password_page():
    return send_from_directory(_base_dir(), "forgot-password.html")


@pages_bp.route("/reset-password.html")
def reset_password_page():
    return send_from_directory(_base_dir(), "reset-password.html")


@pages_bp.route("/profile.html")
def profile_page():
    return send_from_directory(_base_dir(), "profile.html")


@pages_bp.route("/admin.html")
def admin_page():
    return send_from_directory(_base_dir(), "admin.html")


@pages_bp.route("/logo11.png")
def legacy_logo():
    return send_from_directory(os.path.join(_base_dir(), "static"), "logo11.png")
