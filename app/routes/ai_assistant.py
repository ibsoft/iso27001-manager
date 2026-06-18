from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.user import SystemSetting
from app.models.audit_log import AuditLog
from app.utils.decorators import admin_required
from app.utils.ai_helper import ask, is_configured, is_enabled

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    if not is_enabled():
        return jsonify({"error": _("AI assistant is disabled by administrator.")}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": _("Invalid request.")}), 400

    question = (data.get("question") or "").strip()
    history = data.get("history") or []

    if not question:
        return jsonify({"error": _("Question is required.")}), 400

    if not is_configured():
        return jsonify({"error": _("AI assistant is not configured. Ask your administrator to set the API key in AI Settings.")}), 400

    answer, error_or_usage = ask(question, history)

    if answer is None:
        return jsonify({"error": error_or_usage}), 500

    return jsonify({"answer": answer, "usage": error_or_usage})


@ai_bp.route("/admin/ai-settings", methods=["GET", "POST"])
@login_required
@admin_required
def ai_settings():
    if request.method == "POST":
        api_key = (request.form.get("api_key") or "").strip()
        enabled = request.form.get("enabled") == "1"

        if api_key:
            SystemSetting.set("openai_api_key", api_key, current_user.id)
        SystemSetting.set("ai_assistant_enabled", "1" if enabled else "0", current_user.id)

        try:
            log = AuditLog(
                user_id=current_user.id,
                action="UPDATE",
                resource_type="SystemSetting",
                details="Updated AI assistant settings",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", "")[:256],
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            pass
        flash(_("AI settings saved successfully."), "success")
        return redirect(url_for("ai.ai_settings"))

    current_key = SystemSetting.get("openai_api_key")
    current_enabled = SystemSetting.get("ai_assistant_enabled", "0") == "1"
    return render_template("admin/ai_settings.html", has_key=bool(current_key), enabled=current_enabled)
