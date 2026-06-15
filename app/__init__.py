import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_talisman import Talisman
from config import config

talisman = Talisman()

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config["default"]))
    config[config_name].init_app(app)

    from app.extensions import (
        db,
        login_manager,
        bcrypt,
        csrf,
        migrate,
        session_ext,
        mail,
        limiter,
        babel,
    )

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    session_ext.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    from flask import request, session

    LANGUAGES = {"en": "English", "el": "Ελληνικά"}

    def get_locale():
        lang = session.get("lang")
        if lang in LANGUAGES:
            return lang
        return request.accept_languages.best_match(list(LANGUAGES.keys()), default="en")

    babel.init_app(app, locale_selector=get_locale)

    csp = {
        "default-src": ["'self'"],
        "style-src": [
            "'self'",
            "'unsafe-inline'",
            "https://cdn.jsdelivr.net",
            "https://fonts.googleapis.com",
            "https://cdnjs.cloudflare.com",
        ],
        "script-src": [
            "'self'",
            "'unsafe-inline'",
            "https://cdn.jsdelivr.net",
        ],
        "font-src": [
            "'self'",
            "https://fonts.gstatic.com",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
        ],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": ["'self'"],
    }

    if not app.config.get("TALISMAN_FORCE_HTTPS"):
        talisman.init_app(app, content_security_policy=csp, force_https=False)
    else:
        talisman.init_app(app, content_security_policy=csp)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from datetime import datetime as dt_now
    app.jinja_env.globals.update(now=dt_now.utcnow, LANGUAGES=LANGUAGES)

    @app.context_processor
    def inject_globals():
        from flask import session as _session
        return {
            "current_lang": _session.get("lang", "en"),
            "LANGUAGES": LANGUAGES,
        }

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.controls import controls_bp
    from app.routes.clauses import clauses_bp
    from app.routes.risks import risks_bp
    from app.routes.assets import assets_bp
    from app.routes.incidents import incidents_bp
    from app.routes.policies import policies_bp
    from app.routes.audits import audits_bp
    from app.routes.suppliers import suppliers_bp
    from app.routes.soa import soa_bp
    from app.routes.reports import reports_bp
    from app.routes.admin import admin_bp
    from app.routes.gdpr import gdpr_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/")
    app.register_blueprint(controls_bp, url_prefix="/controls")
    app.register_blueprint(clauses_bp, url_prefix="/clauses")
    app.register_blueprint(risks_bp, url_prefix="/risks")
    app.register_blueprint(assets_bp, url_prefix="/assets")
    app.register_blueprint(incidents_bp, url_prefix="/incidents")
    app.register_blueprint(policies_bp, url_prefix="/policies")
    app.register_blueprint(audits_bp, url_prefix="/audits")
    app.register_blueprint(suppliers_bp, url_prefix="/suppliers")
    app.register_blueprint(soa_bp, url_prefix="/soa")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(gdpr_bp, url_prefix="/gdpr")

    @app.route("/health")
    def health():
        return {"status": "ok", "service": "iso27001-manager"}

    if not os.path.exists(app.config["LOG_DIR"]):
        os.makedirs(app.config["LOG_DIR"])

    log_file = os.path.join(app.config["LOG_DIR"], "app.log")
    handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=10)
    handler.setLevel(getattr(logging, app.config.get("LOG_LEVEL", "INFO")))
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, app.config.get("LOG_LEVEL", "INFO")))
    app.logger.info("ISO27001-Manager starting")

    with app.app_context():
        from app.extensions import db as _db
        _db.create_all()
        from app.utils.seed import seed_database
        seed_database()

    return app
