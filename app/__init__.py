import os
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import Flask
from flask_talisman import Talisman
from config import config
from app.paths import data_root, app_root

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
    from flask import request, session, flash, redirect, url_for, jsonify, render_template
    import flask_babel as _fb
    import unicodedata as _uc

    def _strip_el_accents(text):
        result = []
        for ch in text:
            if '\u0386' <= ch <= '\u03CE':
                ch = _uc.normalize('NFD', ch)[0]
            result.append(ch)
        return ''.join(result)

    _original_gettext = _fb.gettext
    _fb.gettext = lambda *args, **kwargs: _strip_el_accents(_original_gettext(*args, **kwargs))
    from flask_babel import gettext as _
    app.jinja_env.globals.update(_strip_el_accents=_strip_el_accents)
    app.jinja_env.filters["strip_el_accents"] = _strip_el_accents

    LANGUAGES = {"en": "English", "el": "Ελληνικά"}

    def get_locale():
        lang = session.get("lang")
        if lang in LANGUAGES:
            return lang
        return request.accept_languages.best_match(list(LANGUAGES.keys()), default="en")

    babel.init_app(app, locale_selector=get_locale)

    from app.utils.sso_auth import init_sso
    init_sso(app)

    csp = {
        "default-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "script-src": ["'self'", "'unsafe-inline'"],
        "font-src": ["'self'", "data:"],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": ["'self'", "https:"],
    }

    if not app.config.get("TALISMAN_FORCE_HTTPS"):
        talisman.init_app(app, content_security_policy=csp, force_https=False)
    else:
        talisman.init_app(app, content_security_policy=csp)

    from app.models.user import User
    from app.models.notification import Notification

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from datetime import datetime as dt_now
    app.jinja_env.globals.update(now=dt_now.utcnow, LANGUAGES=LANGUAGES)

    def _apply_forced_settings():
        from flask import session as _session
        from app.models.user import SystemSetting
        forced_lang = SystemSetting.get("forced_language")
        forced_tz = SystemSetting.get("forced_timezone")
        if forced_lang:
            _session["lang"] = forced_lang
        if forced_tz:
            _session["timezone"] = forced_tz

    @app.template_filter()
    def without_page(params):
        return {k: v for k, v in params.items() if k != "page"}

    @app.template_filter()
    def nl2br(s):
        from markupsafe import Markup, escape
        if s is None:
            return ""
        return Markup(escape(s).replace("\n", "<br>\n"))

    @app.context_processor
    def inject_globals():
        from flask import session as _session, current_app as _current_app
        from app.models.user import SystemSetting
        from app.utils.ai_helper import is_enabled as _ai_enabled
        from app.utils.menu_permissions import ENDPOINT_MENU_PERMISSION, PERMISSION_GROUPS
        from flask_login import current_user

        _apply_forced_settings()

        def has_menu_access(endpoint):
            from flask_login import current_user as _cu
            if _cu.is_authenticated and _cu.has_role("admin"):
                return True
            perm = ENDPOINT_MENU_PERMISSION.get(endpoint)
            if perm is None:
                return True
            write_perm = perm + "_write"
            return _cu.is_authenticated and (_cu.has_permission(perm) or _cu.has_permission(write_perm))

        unread_count = 0
        recent_notifications = []
        if current_user.is_authenticated:
            from app.models.notification import Notification as _Notification
            unread_count = _Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            recent_notifications = _Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(_Notification.created_at.desc()).limit(5).all()

        return {
            "current_lang": _session.get("lang", "en"),
            "LANGUAGES": LANGUAGES,
            "system_settings": {
                "forced_language": SystemSetting.get("forced_language"),
                "forced_timezone": SystemSetting.get("forced_timezone"),
            },
            "ai_enabled": _ai_enabled(),
            "is_demo": _current_app.config.get("DEMO", False),
            "has_menu_access": has_menu_access,
            "permission_groups": PERMISSION_GROUPS,
            "unread_count": unread_count,
            "recent_notifications": recent_notifications,
        }

    @app.before_request
    def apply_forced_settings_before():
        from flask_login import current_user as _cu
        from flask import session as _session
        from app.models.user import SystemSetting
        forced_lang = SystemSetting.get("forced_language")
        forced_tz = SystemSetting.get("forced_timezone")
        if forced_lang:
            session["lang"] = forced_lang
        if forced_tz:
            session["timezone"] = forced_tz

        if _cu.is_authenticated and request.endpoint not in ("auth.logout", "auth.login", "auth.sso_login", "auth.sso_callback", "auth.sso_acs", "auth.sso_metadata", "static"):
            from app.models.user import UserSession
            try:
                _s = UserSession.query.filter_by(session_id=_session.sid, user_id=_cu.id).first()
                if not _s:
                    current_app.logger.warning("Session record NOT found for sid=%s uid=%s — allowing pass-through for debugging",
                                               _session.sid, _cu.id)
                else:
                    _s.last_activity = datetime.utcnow()
                    db.session.commit()
            except Exception:
                pass

    @app.errorhandler(403)
    def forbidden(error):
        message = _("You do not have permission to access this resource.")
        if request.accept_mimetypes.best == "application/json":
            return jsonify({"error": _("Forbidden"), "message": message}), 403
        flash(message, "forbidden")
        if request.referrer and request.referrer != request.url and "login" not in request.referrer:
            return redirect(request.referrer)
        return redirect(url_for("auth.profile"))

    @app.errorhandler(429)
    def too_many_requests(error):
        if request.accept_mimetypes.best == "application/json":
            return jsonify({"error": _("Too Many Requests"), "message": _("Rate limit exceeded. Please wait before retrying.")}), 429
        return render_template("errors/429.html"), 429

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
    from app.routes.nis2 import nis2_bp
    from app.routes.assignments import assignments_bp
    from app.routes.management_review import mgmt_review_bp
    from app.routes.capa import capa_bp
    from app.routes.training import training_bp
    from app.routes.business_continuity import business_continuity_bp
    from app.routes.filled_forms import filled_forms_bp
    from app.routes.kpi import kpi_bp
    from app.routes.ai_assistant import ai_bp
    from app.routes.notifications import notifications_bp
    from app.routes.approval import approval_bp
    from app.routes.general_requests import general_requests_bp

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
    app.register_blueprint(nis2_bp, url_prefix="/nis2")
    app.register_blueprint(assignments_bp, url_prefix="/assignments")
    app.register_blueprint(mgmt_review_bp, url_prefix="/management-review")
    app.register_blueprint(capa_bp, url_prefix="/capa")
    app.register_blueprint(training_bp, url_prefix="/training")
    app.register_blueprint(business_continuity_bp, url_prefix="/business-continuity")
    app.register_blueprint(filled_forms_bp, url_prefix="/filled-forms")
    app.register_blueprint(kpi_bp, url_prefix="/")
    app.register_blueprint(ai_bp, url_prefix="/")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")
    app.register_blueprint(approval_bp, url_prefix="/approval")
    app.register_blueprint(general_requests_bp, url_prefix="/requests")



    from app.models.approval import ApprovalRequest
    from app.models.policy import Policy
    from app.models.capa import CapaRequest
    from app.models.supplier import Supplier
    from app.models.general_request import GeneralRequest

    ApprovalRequest.register_target_model("policy", Policy)
    ApprovalRequest.register_target_model("capa", CapaRequest)
    ApprovalRequest.register_target_model("supplier", Supplier)
    ApprovalRequest.register_target_model("general_request", GeneralRequest)

    @app.route("/health")
    def health():
        return {"status": "ok", "service": "iso27001-manager"}

    if not os.path.exists(app.config["LOG_DIR"]):
        os.makedirs(app.config["LOG_DIR"])

    for _dir in ("app/static/uploads/avatars", "app/static/uploads/filled_forms", "app/static/uploads/general_requests"):
        _path = os.path.join(data_root(), _dir)
        if not os.path.exists(_path):
            os.makedirs(_path)

    _backup_dir = os.path.join(data_root(), "backups")
    if not os.path.exists(_backup_dir):
        os.makedirs(_backup_dir)

    log_file = os.path.join(app.config["LOG_DIR"], "app.jsonl")
    handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=10, utc=True)
    _level_name = app.config.get("LOG_LEVEL", "INFO")
    handler.setLevel(getattr(logging, _level_name))
    class JsonlFormatter(logging.Formatter):
        def format(self, record):
            return json.dumps({
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "line": record.lineno,
            }, ensure_ascii=False)
    handler.setFormatter(JsonlFormatter())
    app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, _level_name))
    app.logger.info("ISO27001-Manager starting")

    with app.app_context():
        from app.extensions import db as _db
        _db.create_all()
        try:
            from app.models.user import SystemSetting
            _db_level = SystemSetting.get("log_level")
            if _db_level and _db_level in ("DEBUG", "INFO", "WARNING", "ERROR"):
                _level_name = _db_level
                handler.setLevel(getattr(logging, _level_name))
                app.logger.setLevel(getattr(logging, _level_name))
        except Exception:
            pass
        from app.utils.schema import ensure_supplier_risk_columns, ensure_control_columns, ensure_nis2_columns, ensure_auth_columns, ensure_user_org_columns, ensure_notification_ref_columns
        ensure_supplier_risk_columns()
        ensure_control_columns()
        ensure_nis2_columns()
        ensure_auth_columns()
        ensure_user_org_columns()
        ensure_notification_ref_columns()
        from app.utils.seed import seed_database
        seed_database()
        try:
            from app.utils.schema import update_control_guidance
            update_control_guidance()
        except Exception:
            app.logger.warning("Guidance update failed")
        try:
            from app.utils.schema import update_nis2_guidance
            update_nis2_guidance()
        except Exception:
            app.logger.warning("NIS2 guidance update failed")
        try:
            import subprocess
            subprocess.run(["pybabel", "compile", "-d",
                            os.path.join(app.root_path, "translations")],
                           capture_output=True)
        except Exception:
            app.logger.warning("Translation compilation failed")

    register_commands(app)

    return app


def register_commands(app):
    import click
    import json
    import os
    from app.models.control import Control

    @app.cli.command("update-guidance")
    def update_guidance():
        """Update control guidance from the seed JSON file."""
        seed_dir = os.path.join(app_root(), "seed_data")
        json_path = os.path.join(seed_dir, "annex_a_controls.json")
        if not os.path.exists(json_path):
            click.echo("JSON file not found.")
            return
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        lookup = {}
        for domain in data["domains"]:
            for ctrl in domain["controls"]:
                lookup[ctrl["code"]] = ctrl
        updated = 0
        for control in Control.query.all():
            jc = lookup.get(control.code)
            if jc:
                changed = False
                for field in ("guidance", "guidance_el"):
                    if jc.get(field) and jc[field] != getattr(control, field):
                        setattr(control, field, jc[field])
                        changed = True
                if changed:
                    updated += 1
        from app.extensions import db
        db.session.commit()
        click.echo(f"Updated {updated} controls.")
