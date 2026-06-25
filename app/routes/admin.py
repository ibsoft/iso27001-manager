import io
import os
import zipfile
import shutil
from datetime import datetime
from app.paths import data_root
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.user import User, Role, Permission, Department
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
    return render_template("admin/user_form.html", form=form, title=_("Edit User"), user=user)


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
        role.permissions = Permission.query.filter(Permission.codename.in_(selected)).all()
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
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template("admin/audit_log.html", logs=logs)


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

    settings = {
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
    return render_template("admin/ldap_settings.html", settings=settings)


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
        flash(_("SSO settings saved."), "success")
        return redirect(url_for("admin.sso_settings"))

    settings = {
        "sso_enabled": SystemSetting.get("sso_enabled", "0") == "1",
        "sso_provider": SystemSetting.get("sso_provider", ""),
        "sso_client_id": SystemSetting.get("sso_client_id", ""),
        "sso_client_secret": SystemSetting.get("sso_client_secret", ""),
        "sso_issuer_url": SystemSetting.get("sso_issuer_url", ""),
        "sso_metadata_url": SystemSetting.get("sso_metadata_url", ""),
    }
    return render_template("admin/sso_settings.html", settings=settings)


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
