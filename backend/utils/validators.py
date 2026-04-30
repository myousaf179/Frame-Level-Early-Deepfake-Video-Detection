from __future__ import annotations
import re

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(email):
    return (email or "").strip().lower()


def is_valid_email(email):
    return bool(email and EMAIL_RE.match(email.strip()))


def password_problems(password, min_length=8):
    if not password:
        return ["Password is required."]
    problems = []
    if len(password) < min_length:
        problems.append(f"Password must be at least {min_length} characters.")
    if not re.search(r"[A-Za-z]", password):
        problems.append("Password must include at least one letter.")
    if not re.search(r"\d", password):
        problems.append("Password must include at least one digit.")
    return problems


def is_allowed_filename(filename, allowed):
    return bool(filename and "." in filename and filename.rsplit(".", 1)[1].lower() in set(allowed))
