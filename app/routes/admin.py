import io
import os
import csv
import zipfile
import shutil
from datetime import datetime
from app.paths import data_root
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, session, current_app, Response
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db, bcrypt
from app.models.user import User, Role, Permission, Department, UserSession
from app.models.audit_log import AuditLog
from app.forms import UserForm
from app.utils.decorators import admin_required, permission_required
from app.utils.pagination import paginate
from app.utils.menu_permissions import PERMISSION_GROUPS

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users")
@login_required
@admin_required
def list_users():
    users = paginate(User.query.order_by(User.username))
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/export")
@login_required
@admin_required
def export_users():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["username", "email", "first_name", "last_name", "is_active", "auth_source", "roles"])
    for u in User.query.order_by(User.username).all():
        writer.writerow([
            u.username, u.email, u.first_name, u.last_name,
            "1" if u.is_active else "0", u.auth_source,
            ",".join(r.name for r in u.roles),
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=users.csv"},
    )


@admin_bp.route("/users/import", methods=["POST"])
@login_required
@admin_required
def import_users_csv():
    file = request.files.get("file")
    if not file:
        flash(_("No file uploaded."), "danger")
        return redirect(url_for("admin.list_users"))
    try:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        reader = csv.DictReader(stream)
        created = 0
        errors = []
        for row in reader:
            username = row.get("username", "").strip()
            if not username:
                continue
            if User.query.filter_by(username=username).first():
                errors.append(f"{username}: already exists")
                continue
            try:
                user = User(
                    username=username,
                    email=row.get("email", "").strip() or f"{username}@imported",
                    first_name=row.get("first_name", "").strip() or username,
                    last_name=row.get("last_name", "").strip() or "",
                    is_active=row.get("is_active", "1").strip() in ("1", "true", "yes"),
                    auth_source="local",
                    password_hash=bcrypt.generate_password_hash(
                        row.get("password", "").strip() or os.urandom(16).hex()
                    ).decode("utf-8"),
                )
                roles_str = row.get("roles", "").strip()
                if roles_str:
                    for rname in roles_str.split(","):
                        rname = rname.strip()
                        role = Role.query.filter_by(name=rname).first()
                        if role:
                            user.roles.append(role)
                db.session.add(user)
                db.session.commit()
                created += 1
            except Exception as e:
                db.session.rollback()
                errors.append(f"{username}: {e}")
        msg = _("Imported %(count)s user(s).", count=created)
        if errors:
            msg += " " + _("Errors: %(err)s", err="; ".join(errors[:5]))
            flash(msg, "warning" if created else "danger")
        else:
            flash(msg, "success")
    except Exception as e:
        flash(_("Failed to parse file: %(err)s", err=str(e)), "danger")
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/users/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_user():
    form = UserForm()
    form.roles.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name).all()]
    form.department.choices = [(0, _("None"))] + [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]
    form.manager.choices = [(0, _("None"))] + [(u.id, u.full_name) for u in User.query.filter_by(is_active=True).order_by(User.first_name).all()]

    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash(_("Username already exists."), "danger")
            return render_template("admin/user_form.html", form=form, title=_("New User"))

        if User.query.filter_by(email=form.email.data).first():
            flash(_("Email already exists."), "danger")
            return render_template("admin/user_form.html", form=form, title=_("New User"))

        if not form.password.data:
            flash(_("Password is required for new users."), "danger")
            return render_template("admin/user_form.html", form=form, title=_("New User"))

        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            is_active=form.is_active.data,
            department_id=form.department.data if form.department.data else None,
            manager_id=form.manager.data if form.manager.data else None,
        )
        user.password = form.password.data
        for role_id in form.roles.data:
            role = Role.query.get(role_id)
            if role:
                user.roles.append(role)

        db.session.add(user)
        db.session.commit()
        _log_audit(f"Created user: {user.username}")
        flash(_("User created successfully."), "success")
        return redirect(url_for("admin.list_users"))

    return render_template("admin/user_form.html", form=form, title=_("New User"))


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    form.roles.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name).all()]
    form.department.choices = [(0, _("None"))] + [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]
    form.manager.choices = [(0, _("None"))] + [(u.id, u.full_name) for u in User.query.filter_by(is_active=True).order_by(User.first_name).all()]

    if form.validate_on_submit():
        if form.username.data != user.username and User.query.filter_by(username=form.username.data).first():
            flash(_("Username already exists."), "danger")
            return render_template("admin/user_form.html", form=form, title=_("Edit User"), user=user)

        if form.email.data != user.email and User.query.filter_by(email=form.email.data).first():
            flash(_("Email already exists."), "danger")
            return render_template("admin/user_form.html", form=form, title=_("Edit User"), user=user)

        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.is_active = form.is_active.data
        user.department_id = form.department.data if form.department.data else None
        user.manager_id = form.manager.data if form.manager.data else None

        if form.password.data:
            user.password = form.password.data

        user.roles = []
        for role_id in form.roles.data:
            role = Role.query.get(role_id)
            if role:
                user.roles.append(role)

        user.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated user: {user.username}")
        flash(_("User updated successfully."), "success")
        return redirect(url_for("admin.list_users"))

    form.roles.data = [r.id for r in user.roles]
    form.department.data = user.department_id or 0
    form.manager.data = user.manager_id or 0
    sessions = UserSession.query.filter_by(user_id=user.id).order_by(UserSession.created_at.desc()).all()
    return render_template("admin/user_form.html", form=form, title=_("Edit User"), user=user, sessions=sessions)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash(_("You cannot deactivate your own account."), "danger")
        return redirect(url_for("admin.list_users"))

    user.is_active = not user.is_active
    db.session.commit()
    _log_audit(f"{'Activated' if user.is_active else 'Deactivated'} user: {user.username}")
    flash(_("User activated.") if user.is_active else _("User deactivated."), "success")
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/users/<int:user_id>/unlock", methods=["POST"])
@login_required
@admin_required
def unlock_user(user_id):
    user = User.query.get_or_404(user_id)
    user.reset_login_attempts()
    db.session.commit()
    _log_audit(f"Unlocked user: {user.username}")
    flash(_("Account unlocked."), "success")
    return redirect(url_for("admin.edit_user", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/kill-sessions", methods=["POST"])
@login_required
@admin_required
def kill_user_sessions(user_id):
    user = User.query.get_or_404(user_id)
    count = UserSession.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    _log_audit(f"Killed {count} session(s) for user: {user.username}")
    flash(_("All sessions terminated."), "success")
    return redirect(url_for("admin.edit_user", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/kill-session/<int:session_id>", methods=["POST"])
@login_required
@admin_required
def kill_user_session(user_id, session_id):
    session_record = UserSession.query.filter_by(id=session_id, user_id=user_id).first_or_404()
    db.session.delete(session_record)
    db.session.commit()
    _log_audit(f"Killed session {session_id} for user: {session_record.user.username}")
    flash(_("Session terminated."), "success")
    return redirect(url_for("admin.edit_user", user_id=user_id))


@admin_bp.route("/sessions")
@login_required
@admin_required
def list_my_sessions():
    sessions = UserSession.query.filter_by(user_id=current_user.id).order_by(UserSession.created_at.desc()).all()
    return render_template("auth/sessions.html", sessions=sessions)


@admin_bp.route("/kill-own-sessions", methods=["POST"])
@login_required
def kill_own_sessions():
    count = UserSession.query.filter(
        UserSession.user_id == current_user.id,
        UserSession.session_id != session.sid
    ).delete()
    db.session.commit()
    if count:
        flash(_("Other sessions terminated."), "success")
    else:
        flash(_("No other active sessions."), "info")
    return redirect(url_for("auth.profile"))


@admin_bp.route("/roles")
@login_required
@admin_required
def list_roles():
    roles = Role.query.all()
    return render_template("admin/roles.html", roles=roles)


@admin_bp.route("/roles/<int:role_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    if request.method == "POST":
        selected = request.form.getlist("permissions")
        perms = []
        for codename in selected:
            perm = Permission.query.filter_by(codename=codename).first()
            if not perm:
                perm = Permission(name=codename.replace("_", " ").title(), codename=codename)
                db.session.add(perm)
            perms.append(perm)
        role.permissions = perms
        db.session.commit()
        _log_audit(f"Updated permissions for role: {role.name}")
        flash(_("Role permissions updated."), "success")
        return redirect(url_for("admin.list_roles"))
    all_perms = Permission.query.order_by(Permission.codename).all()
    role_perm_codenames = {p.codename for p in role.permissions}
    return render_template("admin/role_edit.html", role=role, all_perms=all_perms, role_perms=role_perm_codenames, permission_groups=PERMISSION_GROUPS)


@admin_bp.route("/audit-log")
@login_required
@admin_required
def view_audit_log():
    page = request.args.get("page", 1, type=int)
    action = request.args.get("action", "")
    user_id = request.args.get("user_id", type=int)
    resource_type = request.args.get("resource_type", "")
    q = request.args.get("q", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    query = AuditLog.query

    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if q:
        query = query.filter(
            AuditLog.details.ilike(f"%{q}%") |
            AuditLog.ip_address.ilike(f"%{q}%") |
            AuditLog.user_agent.ilike(f"%{q}%")
        )
    if date_from:
        query = query.filter(AuditLog.created_at >= datetime.strptime(date_from, "%Y-%m-%d"))
    if date_to:
        query = query.filter(AuditLog.created_at <= datetime.strptime(date_to, "%Y-%m-%d") + __import__("datetime").timedelta(days=1))

    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )

    actions = [r[0] for r in db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()]
    resource_types = [r[0] for r in db.session.query(AuditLog.resource_type).distinct().order_by(AuditLog.resource_type).all()]
    users = User.query.order_by(User.username).all()

    return render_template(
        "admin/audit_log.html", logs=logs,
        actions=actions, resource_types=resource_types, users=users,
        filters=dict(action=action, user_id=user_id, resource_type=resource_type, q=q, date_from=date_from, date_to=date_to),
    )


@admin_bp.route("/log-settings", methods=["GET", "POST"])
@login_required
@admin_required
def log_settings():
    from app.models.user import SystemSetting

    if request.method == "POST":
        level = request.form.get("level", "INFO")
        if level in ("DEBUG", "INFO", "WARNING", "ERROR"):
            SystemSetting.set("log_level", level, current_user.id)
            import logging
            current_app.logger.setLevel(getattr(logging, level))
            for h in current_app.logger.handlers:
                h.setLevel(getattr(logging, level))
            flash(_("Log level updated to %(level)s.", level=level), "success")
        return redirect(url_for("admin.log_settings"))

    current_level = SystemSetting.get("log_level", current_app.config.get("LOG_LEVEL", "INFO"))
    return render_template("admin/log_settings.html", current_level=current_level)


def _log_audit(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="CREATE" if "Created" in details else "UPDATE",
            resource_type="User",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
        from app.utils.notify import dispatch_alert
        dispatch_alert("audit_log", f"Admin Action: {details}", f"<p>{details}</p>", context_user=current_user)
    except Exception:
        pass


def _get_db_path():
    import re
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    m = re.match(r"sqlite:///(.*)", uri)
    if m:
        return os.path.normpath(os.path.join(current_app.root_path, m.group(1)))
    return None


def _get_backup_dir():
    backup_dir = os.path.join(data_root(), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


@admin_bp.route("/backup")
@login_required
@admin_required
def list_backups():
    backup_dir = _get_backup_dir()
    backups = []
    if os.path.exists(backup_dir):
        for f in sorted(os.listdir(backup_dir), reverse=True):
            if f.endswith(".zip"):
                path = os.path.join(backup_dir, f)
                size = os.path.getsize(path)
                mod = datetime.fromtimestamp(os.path.getmtime(path))
                backups.append({"filename": f, "size": size, "modified": mod})
    return render_template("admin/backup.html", backups=backups)


@admin_bp.route("/backup/create", methods=["POST"])
@login_required
@admin_required
def create_backup():
    notes = request.form.get("notes", "").strip()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.zip"
    backup_dir = _get_backup_dir()
    backup_path = os.path.join(backup_dir, backup_filename)

    db_path = _get_db_path()
    upload_folder = current_app.config["UPLOAD_FOLDER"]

    try:
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if db_path and os.path.exists(db_path):
                zf.write(db_path, "database/isms.db")

            if notes:
                zf.writestr("notes.txt", notes)

            if os.path.exists(upload_folder):
                for root, dirs, files in os.walk(upload_folder):
                    for f in files:
                        full = os.path.join(root, f)
                        arcname = os.path.relpath(full, os.path.dirname(upload_folder))
                        zf.write(full, arcname)

        try:
            log = AuditLog(
                user_id=current_user.id,
                action="CREATE",
                resource_type="Backup",
                details=f"Created backup: {backup_filename}",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", "")[:256],
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            pass

        flash(_("Backup created successfully."), "success")
    except Exception as e:
        flash(_("Database backup failed: ") + str(e), "danger")

    return redirect(url_for("admin.list_backups"))


@admin_bp.route("/backup/<filename>/download")
@login_required
@admin_required
def download_backup(filename):
    backup_dir = _get_backup_dir()
    path = os.path.join(backup_dir, filename)
    if not os.path.exists(path):
        flash(_("Backup file not found on disk."), "danger")
        return redirect(url_for("admin.list_backups"))
    return send_file(path, as_attachment=True, download_name=filename)


@admin_bp.route("/backup/<filename>/delete", methods=["POST"])
@login_required
@admin_required
def delete_backup(filename):
    backup_dir = _get_backup_dir()
    path = os.path.join(backup_dir, filename)
    if os.path.exists(path):
        os.remove(path)
        try:
            log = AuditLog(
                user_id=current_user.id,
                action="DELETE",
                resource_type="Backup",
                details=f"Deleted backup: {filename}",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", "")[:256],
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            pass
        flash(_("Backup deleted."), "success")
    return redirect(url_for("admin.list_backups"))


@admin_bp.route("/backup/restore", methods=["POST"])
@login_required
@admin_required
def restore_backup():
    file = request.files.get("backup_file")
    if not file or not file.filename:
        flash(_("No file uploaded."), "danger")
        return redirect(url_for("admin.list_backups"))

    if not file.filename.endswith(".zip"):
        flash(_("Invalid backup file."), "danger")
        return redirect(url_for("admin.list_backups"))

    zip_data = file.read()
    db_path = _get_db_path()
    upload_folder = current_app.config["UPLOAD_FOLDER"]

    try:
        with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zf:
            if "database/isms.db" in zf.namelist():
                if db_path and os.path.exists(db_path):
                    os.replace(db_path, db_path + ".bak")
                zf.extract("database/isms.db", os.path.dirname(db_path))
                restored_db = os.path.join(os.path.dirname(db_path), "database", "isms.db")
                if os.path.exists(restored_db):
                    os.replace(restored_db, db_path)
                    shutil.rmtree(os.path.join(os.path.dirname(db_path), "database"), ignore_errors=True)

            for name in zf.namelist():
                if name.startswith("static/uploads/"):
                    zf.extract(name, os.path.dirname(upload_folder))

        try:
            log = AuditLog(
                user_id=current_user.id,
                action="RESTORE",
                resource_type="Backup",
                details="Restored from backup",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", "")[:256],
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            pass

        flash(_("Backup restored successfully."), "success")
    except Exception as e:
        flash(_("Database restore failed: ") + str(e), "danger")

    return redirect(url_for("admin.list_backups"))


@admin_bp.route("/reset-demo-data", methods=["POST"])
@login_required
@admin_required
def reset_demo_data():
    if not current_app.config.get("DEMO", False):
        flash(_("This action is only available in demo mode."), "danger")
        return redirect(url_for("admin.list_backups"))

    from app.utils.seed import reset_demo_data as _reset
    _reset()
    _log_audit("Reset demo data")
    flash(_("Demo data has been reset successfully."), "success")
    return redirect(url_for("admin.list_backups"))


@admin_bp.route("/ldap-settings", methods=["GET", "POST"])
@login_required
@admin_required
def ldap_settings():
    from app.models.user import SystemSetting

    if request.method == "POST":
        SystemSetting.set("ldap_enabled", "1" if request.form.get("ldap_enabled") else "0", current_user.id)
        SystemSetting.set("ldap_server", request.form.get("ldap_server", ""), current_user.id)
        SystemSetting.set("ldap_port", request.form.get("ldap_port", "389"), current_user.id)
        SystemSetting.set("ldap_use_tls", "1" if request.form.get("ldap_use_tls") else "0", current_user.id)
        SystemSetting.set("ldap_base_dn", request.form.get("ldap_base_dn", ""), current_user.id)
        SystemSetting.set("ldap_bind_dn", request.form.get("ldap_bind_dn", ""), current_user.id)
        if request.form.get("ldap_bind_password"):
            SystemSetting.set("ldap_bind_password", request.form.get("ldap_bind_password", ""), current_user.id)
        SystemSetting.set("ldap_user_filter", request.form.get("ldap_user_filter", "(sAMAccountName={username})"),
                           current_user.id)
        SystemSetting.set("ldap_attribute_map",
                           request.form.get("ldap_attribute_map",
                                            '{"email":"mail","first_name":"givenName","last_name":"sn"}'),
                           current_user.id)
        flash(_("LDAP settings saved."), "success")
        return redirect(url_for("admin.ldap_settings"))

    settings = _get_ldap_settings_dict()
    return render_template("admin/ldap_settings.html", settings=settings, test_result=None, ldap_users=None)


@admin_bp.route("/ldap-settings/test", methods=["POST"])
@login_required
@admin_required
def test_ldap_connection():
    from app.utils.ldap_auth import test_connection
    result = test_connection()
    current_app.logger.info("LDAP test: %s", result["message"])
    settings = _get_ldap_settings_dict()
    return render_template("admin/ldap_settings.html", settings=settings, test_result=result, ldap_users=None)


@admin_bp.route("/ldap-settings/list-users", methods=["POST"])
@login_required
@admin_required
def list_ldap_users():
    from app.utils.ldap_auth import list_users
    search = request.form.get("search", "")
    page = request.form.get("page", 1, type=int)
    result = list_users(search=search, page=page)
    settings = _get_ldap_settings_dict()
    return render_template("admin/ldap_settings.html", settings=settings, test_result=None, ldap_users=result)


@admin_bp.route("/ldap-settings/import-users", methods=["POST"])
@login_required
@admin_required
def import_ldap_users():
    from app.utils.ldap_auth import import_users
    selected = request.form.getlist("selected_users")
    if not selected:
        flash(_("No users selected."), "warning")
        return redirect(url_for("admin.ldap_settings"))
    result = import_users(selected)
    if result["imported"]:
        flash(_("Imported %(count)s user(s).", count=result["imported"]), "success")
    if result["skipped"]:
        flash(_("Skipped %(count)s existing LDAP user(s).", count=result["skipped"]), "info")
    for err in result["errors"]:
        flash(err, "danger")
    return redirect(url_for("admin.ldap_settings"))


def _get_ldap_settings_dict():
    from app.models.user import SystemSetting
    return {
        "ldap_enabled": SystemSetting.get("ldap_enabled", "0") == "1",
        "ldap_server": SystemSetting.get("ldap_server", ""),
        "ldap_port": SystemSetting.get("ldap_port", "389"),
        "ldap_use_tls": SystemSetting.get("ldap_use_tls", "0") == "1",
        "ldap_base_dn": SystemSetting.get("ldap_base_dn", ""),
        "ldap_bind_dn": SystemSetting.get("ldap_bind_dn", ""),
        "ldap_bind_password": SystemSetting.get("ldap_bind_password", ""),
        "ldap_user_filter": SystemSetting.get("ldap_user_filter", "(sAMAccountName={username})"),
        "ldap_attribute_map": SystemSetting.get("ldap_attribute_map",
                                                 '{"email":"mail","first_name":"givenName","last_name":"sn"}'),
    }


@admin_bp.route("/sso-settings", methods=["GET", "POST"])
@login_required
@admin_required
def sso_settings():
    from app.models.user import SystemSetting

    if request.method == "POST":
        SystemSetting.set("sso_enabled", "1" if request.form.get("sso_enabled") else "0", current_user.id)
        SystemSetting.set("sso_provider", request.form.get("sso_provider", ""), current_user.id)
        SystemSetting.set("sso_client_id", request.form.get("sso_client_id", ""), current_user.id)
        if request.form.get("sso_client_secret"):
            SystemSetting.set("sso_client_secret", request.form.get("sso_client_secret", ""), current_user.id)
        SystemSetting.set("sso_issuer_url", request.form.get("sso_issuer_url", ""), current_user.id)
        SystemSetting.set("sso_metadata_url", request.form.get("sso_metadata_url", ""), current_user.id)
        if request.form.get("saml_x509_cert"):
            SystemSetting.set("saml_x509_cert", request.form.get("saml_x509_cert", ""), current_user.id)
        flash(_("SSO settings saved."), "success")
        return redirect(url_for("admin.sso_settings"))

    settings = _get_sso_settings_dict()
    return render_template("admin/sso_settings.html", settings=settings, validate_result=None)


@admin_bp.route("/sso-settings/validate", methods=["POST"])
@login_required
@admin_required
def validate_sso_settings():
    import urllib.request, urllib.error
    import json as _json
    log = []
    settings = _get_sso_settings_dict()

    log.append(f"Provider: {settings['sso_provider'] or '(not set)'}")
    log.append(f"Client ID: {settings['sso_client_id'] or '(not set)'}")
    log.append(f"Issuer URL: {settings['sso_issuer_url'] or '(not set)'}")
    log.append(f"Metadata URL: {settings['sso_metadata_url'] or '(not set)'}")
    log.append("")

    if not settings["sso_provider"]:
        return _sso_validate_result("Provider not selected", log, settings)

    if not settings["sso_client_id"]:
        log.append("[WARN] Client ID is empty")

    if settings["sso_issuer_url"]:
        if not settings["sso_issuer_url"].startswith("https://"):
            log.append("[WARN] Issuer URL should use HTTPS")
        log.append(f"Checking issuer URL reachability...")
        try:
            req = urllib.request.Request(settings["sso_issuer_url"], method="HEAD")
            resp = urllib.request.urlopen(req, timeout=10)
            log.append(f"  HTTP {resp.status} — OK")
        except urllib.error.HTTPError as e:
            log.append(f"  HTTP {e.code} — issuer responds (expected for SSO endpoints)")
        except Exception as e:
            log.append(f"  [WARN] Cannot reach issuer URL: {e}")

    if settings["sso_metadata_url"]:
        if not settings["sso_metadata_url"].startswith("https://"):
            log.append("[WARN] Metadata URL should use HTTPS")
        log.append("Fetching metadata URL...")
        try:
            req = urllib.request.Request(settings["sso_metadata_url"])
            resp = urllib.request.urlopen(req, timeout=15)
            body = resp.read()
            log.append(f"  HTTP {resp.status} — {len(body)} bytes received")
            content_type = resp.headers.get("Content-Type", "")
            if "xml" in content_type.lower() or body.startswith(b"<?xml") or b"EntityDescriptor" in body[:500]:
                log.append("  Content appears to be valid SAML metadata (XML)")
            else:
                log.append(f"  [WARN] Content-Type: {content_type}, may not be SAML metadata")
        except Exception as e:
            log.append(f"  [ERROR] Cannot fetch metadata URL: {e}")

    log.append("")
    log.append("Validation complete.")
    return _sso_validate_result("Validation complete" if not any("[ERROR]" in l for l in log) else "Some checks failed", log, settings)


def _sso_validate_result(message, log, settings):
    result = {"success": "[ERROR]" not in message and "[WARN]" not in message, "message": message, "log": log}
    current_app.logger.info("SSO validate: %s", message)
    return render_template("admin/sso_settings.html", settings=settings, validate_result=result)


def _get_sso_settings_dict():
    from app.models.user import SystemSetting
    return {
        "sso_enabled": SystemSetting.get("sso_enabled", "0") == "1",
        "sso_provider": SystemSetting.get("sso_provider", ""),
        "sso_client_id": SystemSetting.get("sso_client_id", ""),
        "sso_client_secret": SystemSetting.get("sso_client_secret", ""),
        "sso_issuer_url": SystemSetting.get("sso_issuer_url", ""),
        "sso_metadata_url": SystemSetting.get("sso_metadata_url", ""),
        "saml_x509_cert": SystemSetting.get("saml_x509_cert", ""),
    }


@admin_bp.route("/departments")
@login_required
@admin_required
def list_departments():
    departments = Department.query.order_by(Department.name).all()
    return render_template("admin/departments.html", departments=departments)


@admin_bp.route("/departments/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_department():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        head_id = request.form.get("head_id", type=int)

        if not name:
            flash(_("Department name is required."), "danger")
            users = User.query.order_by(User.first_name).all()
            return render_template("admin/department_form.html", users=users)

        existing = Department.query.filter_by(name=name).first()
        if existing:
            flash(_("A department with this name already exists."), "danger")
            users = User.query.order_by(User.first_name).all()
            return render_template("admin/department_form.html", users=users)

        dept = Department(name=name, description=description or None, head_id=head_id or None)
        db.session.add(dept)
        db.session.commit()
        _log_audit(f"Created department: {name}")
        flash(_("Department created."), "success")
        return redirect(url_for("admin.list_departments"))

    users = User.query.order_by(User.first_name).all()
    return render_template("admin/department_form.html", users=users)


@admin_bp.route("/departments/<int:dept_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        head_id = request.form.get("head_id", type=int)

        if not name:
            flash(_("Department name is required."), "danger")
            users = User.query.order_by(User.first_name).all()
            return render_template("admin/department_form.html", dept=dept, users=users)

        existing = Department.query.filter(Department.name == name, Department.id != dept.id).first()
        if existing:
            flash(_("A department with this name already exists."), "danger")
            users = User.query.order_by(User.first_name).all()
            return render_template("admin/department_form.html", dept=dept, users=users)

        dept.name = name
        dept.description = description or None
        dept.head_id = head_id or None
        db.session.commit()
        _log_audit(f"Edited department: {name}")
        flash(_("Department updated."), "success")
        return redirect(url_for("admin.list_departments"))

    users = User.query.order_by(User.first_name).all()
    return render_template("admin/department_form.html", dept=dept, users=users)


@admin_bp.route("/departments/<int:dept_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    name = dept.name
    User.query.filter_by(department_id=dept.id).update({User.department_id: None})
    db.session.delete(dept)
    db.session.commit()
    _log_audit(f"Deleted department: {name}")
    flash(_("Department deleted."), "success")
    return redirect(url_for("admin.list_departments"))


# ─── Mail Settings ───────────────────────────────────────────────────────

@admin_bp.route("/mail-settings", methods=["GET", "POST"])
@login_required
@admin_required
def mail_settings():
    from app.models.user import SystemSetting

    if request.method == "POST":
        SystemSetting.set("mail_server", request.form.get("mail_server", ""), current_user.id)
        SystemSetting.set("mail_port", request.form.get("mail_port", "587"), current_user.id)
        SystemSetting.set("mail_use_tls", request.form.get("mail_use_tls", "true"), current_user.id)
        SystemSetting.set("mail_username", request.form.get("mail_username", ""), current_user.id)
        if request.form.get("mail_password"):
            SystemSetting.set("mail_password", request.form.get("mail_password", ""), current_user.id)
        SystemSetting.set("mail_default_sender", request.form.get("mail_default_sender", ""), current_user.id)
        flash(_("Mail settings saved."), "success")
        return redirect(url_for("admin.mail_settings"))

    settings = _get_mail_settings_dict()
    return render_template("admin/mail_settings.html", settings=settings, test_result=None)


@admin_bp.route("/mail-settings/test", methods=["POST"])
@login_required
@admin_required
def test_mail_settings():
    from app.utils.email import send_test_email
    success = send_test_email(current_user.email)
    settings = _get_mail_settings_dict()
    if success:
        flash(_("Test email sent to {}.").format(current_user.email), "success")
    else:
        flash(_("Failed to send test email. Check server logs for details."), "danger")
    return render_template("admin/mail_settings.html", settings=settings, test_result=success)


def _get_mail_settings_dict():
    from app.models.user import SystemSetting
    return {
        "mail_server": SystemSetting.get("mail_server", current_app.config.get("MAIL_SERVER", "")),
        "mail_port": SystemSetting.get("mail_port", str(current_app.config.get("MAIL_PORT", 587))),
        "mail_use_tls": SystemSetting.get("mail_use_tls", "true"),
        "mail_username": SystemSetting.get("mail_username", current_app.config.get("MAIL_USERNAME", "")),
        "mail_password": "",
        "mail_default_sender": SystemSetting.get("mail_default_sender", current_app.config.get("MAIL_DEFAULT_SENDER", "")),
    }


# ─── Email Alerts ────────────────────────────────────────────────────────

EVENT_TYPE_CHOICES = [
    ("audit_log", _("All Audit Log Actions")),
    ("approval_requested", _("Approval Requested")),
    ("approved", _("Approved")),
    ("rejected", _("Rejected")),
    ("failed_login", _("Failed Login")),
    ("account_locked", _("Account Locked")),
    ("user_created", _("User Created")),
    ("backup_created", _("Backup Created")),
    ("login", _("User Login")),
]


@admin_bp.route("/email-alerts")
@login_required
@admin_required
def list_email_alerts():
    from app.models.email_alert import EmailAlert
    alerts = EmailAlert.query.order_by(EmailAlert.created_at.desc()).all()
    return render_template("admin/email_alerts.html", alerts=alerts, event_types=EVENT_TYPE_CHOICES)


@admin_bp.route("/email-alerts/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_email_alert():
    from app.models.email_alert import EmailAlert
    from app.models.user import Role, User

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        event_type = request.form.get("event_type", "")
        recipient_type = request.form.get("recipient_type", "role")
        try:
            recipient_id = int(request.form.get("recipient_id", 0))
        except (ValueError, TypeError):
            recipient_id = 0

        if not name or not event_type or not recipient_id:
            flash(_("All fields are required."), "danger")
            return redirect(url_for("admin.create_email_alert"))

        alert = EmailAlert(
            name=name,
            event_type=event_type,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            created_by_id=current_user.id,
        )
        db.session.add(alert)
        db.session.commit()
        _log_audit(f"Created email alert: {name}")
        flash(_("Email alert created."), "success")
        return redirect(url_for("admin.list_email_alerts"))

    roles = Role.query.order_by(Role.name).all()
    users = User.query.order_by(User.username).all()
    return render_template("admin/email_alert_form.html", event_types=EVENT_TYPE_CHOICES, roles=roles, users=users, alert=None)


@admin_bp.route("/email-alerts/<int:alert_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_email_alert(alert_id):
    from app.models.email_alert import EmailAlert
    alert = EmailAlert.query.get_or_404(alert_id)
    alert.is_active = not alert.is_active
    db.session.commit()
    status = "enabled" if alert.is_active else "disabled"
    _log_audit(f"{status} email alert: {alert.name}")
    flash(_("Email alert {}.").format(status), "success")
    return redirect(url_for("admin.list_email_alerts"))


@admin_bp.route("/email-alerts/<int:alert_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_email_alert(alert_id):
    from app.models.email_alert import EmailAlert
    alert = EmailAlert.query.get_or_404(alert_id)
    db.session.delete(alert)
    db.session.commit()
    _log_audit(f"Deleted email alert: {alert.name}")
    flash(_("Email alert deleted."), "success")
    return redirect(url_for("admin.list_email_alerts"))


# ─── ISMS Roles ──────────────────────────────────────────────────────────

@admin_bp.route("/isms-roles")
@login_required
@admin_required
def list_isms_roles():
    from app.models.isms_role import ISMSRole
    roles = ISMSRole.query.order_by(ISMSRole.sort_order, ISMSRole.title).all()
    return render_template("admin/isms_roles.html", roles=roles)


@admin_bp.route("/isms-roles/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_isms_role():
    from app.models.isms_role import ISMSRole
    from app.models.user import Department, User

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash(_("Title is required."), "danger")
            return redirect(url_for("admin.create_isms_role"))
        role = ISMSRole(
            title=title,
            description=request.form.get("description", "").strip() or None,
            department_id=request.form.get("department_id", type=int) or None,
            user_id=request.form.get("user_id", type=int) or None,
            parent_role_id=request.form.get("parent_role_id", type=int) or None,
            sort_order=request.form.get("sort_order", 0, type=int),
            is_management=request.form.get("is_management") == "1",
        )
        db.session.add(role)
        db.session.commit()
        _log_audit(f"Created ISMS role: {title}")
        flash(_("ISMS role created."), "success")
        return redirect(url_for("admin.list_isms_roles"))

    departments = Department.query.order_by(Department.name).all()
    users = User.query.order_by(User.first_name).all()
    parent_roles = ISMSRole.query.order_by(ISMSRole.title).all()
    return render_template("admin/isms_role_form.html", departments=departments, users=users, parent_roles=parent_roles, role=None)


@admin_bp.route("/isms-roles/<int:role_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_isms_role(role_id):
    from app.models.isms_role import ISMSRole
    from app.models.user import Department, User

    role = ISMSRole.query.get_or_404(role_id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash(_("Title is required."), "danger")
            return redirect(url_for("admin.edit_isms_role", role_id=role_id))
        role.title = title
        role.description = request.form.get("description", "").strip() or None
        role.department_id = request.form.get("department_id", type=int) or None
        role.user_id = request.form.get("user_id", type=int) or None
        role.parent_role_id = request.form.get("parent_role_id", type=int) or None
        role.sort_order = request.form.get("sort_order", 0, type=int)
        role.is_management = request.form.get("is_management") == "1"
        role.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Edited ISMS role: {title}")
        flash(_("ISMS role updated."), "success")
        return redirect(url_for("admin.list_isms_roles"))

    departments = Department.query.order_by(Department.name).all()
    users = User.query.order_by(User.first_name).all()
    parent_roles = ISMSRole.query.filter(ISMSRole.id != role_id).order_by(ISMSRole.title).all()
    return render_template("admin/isms_role_form.html", departments=departments, users=users, parent_roles=parent_roles, role=role)


@admin_bp.route("/isms-roles/<int:role_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_isms_role(role_id):
    from app.models.isms_role import ISMSRole
    role = ISMSRole.query.get_or_404(role_id)
    ISMSRole.query.filter_by(parent_role_id=role_id).update({ISMSRole.parent_role_id: None})
    title = role.title
    db.session.delete(role)
    db.session.commit()
    _log_audit(f"Deleted ISMS role: {title}")
    flash(_("ISMS role deleted."), "success")
    return redirect(url_for("admin.list_isms_roles"))


# ─── Organisation Chart ─────────────────────────────────────────────────

@admin_bp.route("/org-chart")
@login_required
@admin_required
def org_chart():
    from app.models.isms_role import ISMSRole
    from app.models.user import Department, User

    top_roles = ISMSRole.query.filter_by(is_management=True).order_by(ISMSRole.sort_order).all()
    dept_roles = ISMSRole.query.filter_by(is_management=False).order_by(ISMSRole.department_id, ISMSRole.sort_order).all()
    departments = Department.query.order_by(Department.name).all()
    unassigned_users = User.query.filter(User.department_id.is_(None)).order_by(User.first_name).all()

    return render_template("admin/org_chart.html",
                           top_roles=top_roles, dept_roles=dept_roles,
                           departments=departments, unassigned_users=unassigned_users)


@admin_bp.route("/org-chart/pdf")
@login_required
@admin_required
def org_chart_pdf():
    from app.models.isms_role import ISMSRole
    from app.models.user import Department, User
    from app.utils.pdf import render_pdf
    from datetime import datetime as _dt

    top_roles = ISMSRole.query.filter_by(is_management=True).order_by(ISMSRole.sort_order).all()
    dept_roles = ISMSRole.query.filter_by(is_management=False).order_by(ISMSRole.department_id, ISMSRole.sort_order).all()
    departments = Department.query.order_by(Department.name).all()

    dept_data = []
    for dept in departments:
        role_list = [r for r in dept_roles if r.department_id == dept.id]
        member_list = dept.members.order_by(User.first_name).all() if dept.members else []
        shown_ids = {r.user_id for r in role_list if r.user_id}
        unassigned = [u for u in member_list if u.id not in shown_ids]
        dept_data.append({"dept": dept, "roles": role_list, "members": unassigned})

    response = render_pdf("admin/org_chart_pdf.html",
                          top_roles=top_roles, dept_data=dept_data,
                          now=_dt.utcnow(),
                          filename="organisation_chart")
    if response is None:
        flash(_("Failed to generate PDF."), "danger")
        return redirect(url_for("admin.org_chart"))
    return response
