from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, request

from .config import Config
from .extensions import db


def create_app(config_class: type[Config] = Config) -> Flask:
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app = Flask(__name__, static_folder=os.path.join(base_dir, "static"), static_url_path="/static")
    app.config.from_object(config_class)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for key in ("UPLOAD_DIR", "OUTPUT_DIR", "INSTANCE_DIR"):
        os.makedirs(app.config[key], exist_ok=True)
    db.init_app(app)
    with app.app_context():
        from . import models  # noqa
        from .services import auth_service, user_service
        db.create_all()
        auth_service.ensure_default_admin(app)
        user_service.ensure_default_plans()
    from .routes.pages import pages_bp
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.analyze import analyze_bp
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(analyze_bp)

    @app.errorhandler(404)
    def _not_found(_):
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "Not found"}), 404
        return "Not found", 404

    return app
