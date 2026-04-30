"""Password-reset email delivery with a safe development fallback."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from flask import current_app

from ..models import PasswordResetToken, User

log = logging.getLogger("email_service")


def build_reset_url(token: str) -> str:
    base = current_app.config.get("APP_PUBLIC_URL", "http://localhost:5000").rstrip("/")
    return f"{base}/reset-password.html?token={token}"


def send_password_reset(user: User, token: PasswordResetToken) -> dict:
    """
    Send a reset link if SMTP is configured.

    In development, if SMTP settings are missing, we return the reset URL in the
    API response. That keeps testing possible without pretending to send email.
    """
    reset_url = build_reset_url(token.token)
    smtp_host = current_app.config.get("SMTP_HOST")
    if not smtp_host:
        log.warning("SMTP not configured; returning development reset link for %s", user.email)
        return {
            "sent": False,
            "dev_reset_url": reset_url,
            "message": "SMTP is not configured. Development reset link returned for testing.",
        }

    msg = EmailMessage()
    msg["Subject"] = "Reset your Deepfake Defender password"
    msg["From"] = current_app.config["SMTP_FROM"]
    msg["To"] = user.email
    msg.set_content(
        "Hello,\n\n"
        "Use the link below to reset your Deepfake Defender password. "
        "The link expires soon and can only be used once.\n\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )

    port = int(current_app.config.get("SMTP_PORT", 587))
    username: Optional[str] = current_app.config.get("SMTP_USER")
    password: Optional[str] = current_app.config.get("SMTP_PASSWORD")
    use_tls = bool(current_app.config.get("SMTP_USE_TLS", True))

    with smtplib.SMTP(smtp_host, port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg)

    log.info("Password reset email sent to %s", user.email)
    return {"sent": True, "message": "Password reset link sent."}
