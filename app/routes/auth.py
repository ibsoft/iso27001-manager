import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_babel import gettext as _
from app.extensions import db, bcrypt, limiter
from app.models.user import User, Role
from app.models.audit_log import AuditLog
from app.models.asset_assignment import AssetAssignment
from app.forms import LoginForm, ChangePasswordForm, ProfileForm
from datetime import datetime
from app.paths import data_root

import pyotp
import qrcode
import io
import base64

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/language/<lang>")
def set_language(lang):
    from flask import session
    from app.models.user import SystemSetting
    forced_lang = SystemSetting.get("forced_language")
    if forced_lang:
        flash(_("Language is enforced by administrator"), "warning")
        return redirect(request.referrer or url_for("dashboard.index"))
    if lang in ("en", "el"):
        session["lang"] = lang
    return redirect(request.referrer or url_for("dashboard.index"))


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()

        # Try LDAP authentication first if enabled and user is an LDAP user (or doesn't exist locally)
        from app.utils.ldap_auth import authenticate as ldap_authenticate
        ldap_result = None
        if not user or user.auth_source == "ldap":
            ldap_result = ldap_authenticate(username, password)

        if ldap_result:
            user = User.query.get(ldap_result["id"])
        elif user and user.auth_source != "ldap":
            # Local authentication
            if not user.verify_password(password):
                user.increment_login_attempts()
                db.session.commit()
                if user.is_locked():
                    flash(_("Account locked due to too many failed attempts. Try again in 15 minutes."), "danger")
                    _log_audit(None, "ACCOUNT_LOCKED", "User", user.id, f"Account locked for {user.username}")
                    return render_template("auth/login.html", form=form)
                flash(_("Invalid username or password."), "danger")
                _log_audit(None, "FAILED_LOGIN", "User", user.id, f"Failed login for {username}")
                return render_template("auth/login.html", form=form)
        else:
            flash(_("Invalid username or password."), "danger")
            _log_audit(None, "FAILED_LOGIN", "User", user.id if user else None, f"Failed login for {username}")
            return render_template("auth/login.html", form=form)

        if not user.is_active:
            flash(_("Account is deactivated. Contact an administrator."), "danger")
            return render_template("auth/login.html", form=form)

        if user.is_locked():
            flash(_("Account locked due to too many failed attempts. Try again in 15 minutes."), "danger")
            return render_template("auth/login.html", form=form)

        if user.is_mfa_enabled:
            session["mfa_user_id"] = user.id
            session["mfa_remember"] = form.data.get("remember", False)
            return redirect(url_for("auth.mfa_verify"))

        user.reset_login_attempts()
        user.last_login = datetime.utcnow()
        db.session.commit()

        login_user(user, remember=form.data.get("remember", False))

        if user.default_language and user.default_language in ("en", "el"):
            session["lang"] = user.default_language
        elif "lang" not in session:
            session["lang"] = "en"
        from app.models.user import SystemSetting
        forced_lang = SystemSetting.get("forced_language")
        if forced_lang:
            session["lang"] = forced_lang

        _log_audit(user.id, "LOGIN", "User", user.id, f"User {user.username} logged in")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/mfa-verify", methods=["GET", "POST"])
def mfa_verify():
    if "mfa_user_id" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.get(session["mfa_user_id"])
    if not user:
        session.pop("mfa_user_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        totp_code = request.form.get("totp_code", "")
        if not totp_code:
            flash(_("Please enter your TOTP code."), "warning")
            return render_template("auth/mfa_verify.html")

        if user.mfa_secret:
            totp = pyotp.TOTP(user.mfa_secret)
            if totp.verify(totp_code):
                user.reset_login_attempts()
                user.last_login = datetime.utcnow()
                db.session.commit()

                login_user(user)
                session.pop("mfa_user_id", None)

                if user.default_language and user.default_language in ("en", "el"):
                    session["lang"] = user.default_language
                elif "lang" not in session:
                    session["lang"] = "en"

                _log_audit(user.id, "LOGIN", "User", user.id, f"User {user.username} logged in with MFA")

                next_page = request.args.get("next")
                if next_page and next_page.startswith("/"):
                    return redirect(next_page)
                return redirect(url_for("dashboard.index"))
            else:
                flash(_("Invalid TOTP code."), "danger")

    return render_template("auth/mfa_verify.html")


@auth_bp.route("/logout")
@login_required
def logout():
    _log_audit(current_user.id, "LOGOUT", "User", current_user.id, f"User {current_user.username} logged out")
    logout_user()
    session.clear()
    flash(_("You have been logged out."), "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    my_assignments = current_user.asset_assignments.order_by(
        AssetAssignment.checkout_date.desc()
    ).all()

    if form.validate_on_submit():
        if form.email.data != current_user.email and User.query.filter_by(email=form.email.data).first():
            flash(_("Email already in use."), "danger")
            return render_template("auth/profile.html", form=form, my_assignments=my_assignments)

        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        current_user.phone_number = form.phone_number.data or None
        current_user.mobile_phone = form.mobile_phone.data or None

        if form.avatar_file.data:
            file = form.avatar_file.data
            if allowed_file(file.filename):
                upload_dir = os.path.join(data_root(), "app", "static", "uploads", "avatars")
                os.makedirs(upload_dir, exist_ok=True)
                ext = file.filename.rsplit(".", 1)[1].lower()
                filename = f"user_{current_user.id}_{int(datetime.utcnow().timestamp())}.{ext}"
                file.save(os.path.join(upload_dir, filename))
                current_user.avatar_url = url_for("static", filename=f"uploads/avatars/{filename}")
            else:
                flash(_("Invalid image format. Allowed: PNG, JPG, GIF, WebP, SVG"), "warning")
        elif form.avatar_url.data:
            current_user.avatar_url = form.avatar_url.data
        else:
            current_user.avatar_url = None

        if current_user.has_role("admin"):
            current_user.timezone = form.timezone.data
            current_user.default_language = form.default_language.data or None
            if current_user.default_language:
                session["lang"] = current_user.default_language
            from app.models.user import SystemSetting
            if form.force_language.data and form.default_language.data:
                SystemSetting.set("forced_language", form.default_language.data, current_user.id)
            elif not form.force_language.data:
                SystemSetting.set("forced_language", "", current_user.id)
            if form.force_timezone.data and form.timezone.data:
                SystemSetting.set("forced_timezone", form.timezone.data, current_user.id)
            elif not form.force_timezone.data:
                SystemSetting.set("forced_timezone", "", current_user.id)

        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(current_user.id, "PROFILE_UPDATE", "User", current_user.id, "Profile updated")
        flash(_("Profile updated successfully."), "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form, my_assignments=my_assignments)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.verify_password(form.current_password.data):
            flash(_("Current password is incorrect."), "danger")
            return render_template("auth/change_password.html", form=form)

        if form.new_password.data != form.confirm_password.data:
            flash(_("New passwords do not match."), "danger")
            return render_template("auth/change_password.html", form=form)

        current_user.password = form.new_password.data
        current_user.password_changed_at = datetime.utcnow()
        db.session.commit()
        _log_audit(current_user.id, "PASSWORD_CHANGE", "User", current_user.id, "Password changed")
        flash(_("Password changed successfully."), "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/change_password.html", form=form)


@auth_bp.route("/setup-mfa", methods=["GET", "POST"])
@login_required
def setup_mfa():
    if current_user.is_mfa_enabled:
        flash(_("MFA is already enabled."), "info")
        return redirect(url_for("auth.profile"))

    if not current_user.mfa_secret:
        current_user.mfa_secret = pyotp.random_base32()
        db.session.commit()

    totp = pyotp.TOTP(current_user.mfa_secret)
    provisioning_uri = totp.provisioning_uri(
        current_user.email,
        issuer_name="ISO27001-Manager",
    )

    qr = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    if request.method == "POST":
        verification_code = request.form.get("verification_code", "")
        if totp.verify(verification_code):
            current_user.is_mfa_enabled = True
            db.session.commit()
            _log_audit(current_user.id, "MFA_ENABLED", "User", current_user.id, "MFA enabled")
            flash(_("MFA has been enabled successfully."), "success")
            return redirect(url_for("auth.profile"))
        flash(_("Invalid verification code. Please try again."), "danger")

    return render_template("auth/setup_mfa.html", qr_code=qr_b64, secret=current_user.mfa_secret)


@auth_bp.route("/disable-mfa", methods=["POST"])
@login_required
def disable_mfa():
    current_user.is_mfa_enabled = False
    current_user.mfa_secret = None
    db.session.commit()
    _log_audit(current_user.id, "MFA_DISABLED", "User", current_user.id, "MFA disabled")
    flash(_("MFA has been disabled."), "info")
    return redirect(url_for("auth.profile"))


def _log_audit(user_id, action, resource_type, resource_id, details=None):
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
