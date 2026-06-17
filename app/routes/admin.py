import io
import os
import json
import subprocess
import zipfile
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.user import User, Role, Permission
from app.models.audit_log import AuditLog
from app.models.backup import BackupRecord
from app.forms import UserForm
from app.utils.decorators import admin_required
from app.utils.pagination import paginate

admin_bp = Blueprint("admin", __name__)

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")


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


@admin_bp.route("/audit-log")
@login_required
@admin_required
def view_audit_log():
    page = request.args.get("page", 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template("admin/audit_log.html", logs=logs)


@admin_bp.route("/backups")
@login_required
@admin_required
def backup_list():
    backups = BackupRecord.query.order_by(BackupRecord.created_at.desc()).paginate(
        page=request.args.get("page", 1, type=int), per_page=20, error_out=False
    )
    total_size = sum(b.file_size or 0 for b in BackupRecord.query.all())
    if total_size > 1024 * 1024:
        total_display = f"{total_size / (1024 * 1024):.1f} MB"
    else:
        total_display = f"{total_size / 1024:.1f} KB"
    return render_template("admin/backups.html", backups=backups, total_size=total_display)


@admin_bp.route("/backups/create", methods=["POST"])
@login_required
@admin_required
def create_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    db_type = "sqlite"
    db_dump = None

    if "postgresql" in db_uri:
        db_type = "postgresql"
        parts = db_uri.replace("postgresql://", "").split("@")
        user_pass, host_part = parts[0], parts[1] if len(parts) > 1 else ""
        user, pw = user_pass.split(":") if ":" in user_pass else (user_pass, "")
        host_port, db_name = host_part.split("/") if "/" in host_part else ("", host_part)
        host = host_port.split(":")[0] if ":" in host_port else host_port
        port = host_port.split(":")[1] if ":" in host_port else "5432"
        dump_file = os.path.join(BACKUP_DIR, f"db_{timestamp}.sql")
        env = os.environ.copy()
        if pw:
            env["PGPASSWORD"] = pw
        try:
            subprocess.run(
                ["pg_dump", "-h", host, "-p", port, "-U", user, "-d", db_name,
                 "-f", dump_file, "--no-owner", "--no-acl"],
                env=env, capture_output=True, text=True, check=True, timeout=120,
            )
            db_dump = dump_file
        except subprocess.CalledProcessError as e:
            flash(_("Database backup failed: ") + e.stderr, "danger")
            return redirect(url_for("admin.backup_list"))
    else:
        db_path = db_uri.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(current_app.instance_path), db_path)
        dump_file = os.path.join(BACKUP_DIR, f"db_{timestamp}.sql")
        try:
            subprocess.run(
                ["sqlite3", db_path, ".dump"],
                capture_output=True, text=True, check=True, timeout=60,
            )
            with open(dump_file, "w") as f:
                result = subprocess.run(
                    ["sqlite3", db_path, ".dump"],
                    capture_output=True, text=True, check=True, timeout=60,
                )
                f.write(result.stdout)
            db_dump = dump_file
        except subprocess.CalledProcessError as e:
            flash(_("Database backup failed."), "danger")
            return redirect(url_for("admin.backup_list"))

    zip_filename = f"backup_{timestamp}.zip"
    zip_path = os.path.join(BACKUP_DIR, zip_filename)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if db_dump and os.path.exists(db_dump):
            zf.write(db_dump, f"database/{os.path.basename(db_dump)}")
        app_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
        for root, _dirs, files in os.walk(app_dir):
            rel = os.path.relpath(root, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            for f in files:
                fpath = os.path.join(root, f)
                zf.write(fpath, os.path.join(rel, f))
        meta = {
            "created_at": timestamp,
            "db_type": db_type,
            "app_version": "1.0",
        }
        zf.writestr("backup_meta.json", json.dumps(meta, indent=2))

    if db_dump and os.path.exists(db_dump):
        os.remove(db_dump)

    notes = request.form.get("notes", "")
    record = BackupRecord(
        filename=zip_filename,
        filepath=zip_path,
        file_size=os.path.getsize(zip_path),
        db_type=db_type,
        notes=notes,
        created_by_id=current_user.id,
    )
    db.session.add(record)
    _log_audit(f"Created backup: {zip_filename}")
    db.session.commit()
    flash(_("Backup created successfully."), "success")
    return redirect(url_for("admin.backup_list"))


@admin_bp.route("/backups/<int:backup_id>/download")
@login_required
@admin_required
def download_backup(backup_id):
    rec = BackupRecord.query.get_or_404(backup_id)
    if not os.path.exists(rec.filepath):
        flash(_("Backup file not found on disk."), "danger")
        return redirect(url_for("admin.backup_list"))
    return send_file(rec.filepath, as_attachment=True, download_name=rec.filename)


@admin_bp.route("/backups/<int:backup_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_backup(backup_id):
    rec = BackupRecord.query.get_or_404(backup_id)
    if os.path.exists(rec.filepath):
        os.remove(rec.filepath)
    db.session.delete(rec)
    _log_audit(f"Deleted backup: {rec.filename}")
    db.session.commit()
    flash(_("Backup deleted."), "success")
    return redirect(url_for("admin.backup_list"))


@admin_bp.route("/backups/restore", methods=["POST"])
@login_required
@admin_required
def restore_backup():
    file = request.files.get("backup_file")
    if not file or not file.filename:
        flash(_("No file uploaded."), "danger")
        return redirect(url_for("admin.backup_list"))

    os.makedirs(BACKUP_DIR, exist_ok=True)
    restore_path = os.path.join(BACKUP_DIR, f"restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip")
    file.save(restore_path)

    extract_dir = restore_path.replace(".zip", "")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(restore_path, "r") as zf:
            zf.extractall(extract_dir)
    except zipfile.BadZipFile:
        flash(_("Invalid backup file."), "danger")
        return redirect(url_for("admin.backup_list"))

    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    sql_dir = os.path.join(extract_dir, "database")
    if os.path.isdir(sql_dir):
        for fname in sorted(os.listdir(sql_dir)):
            if fname.endswith(".sql"):
                sql_path = os.path.join(sql_dir, fname)
                if "postgresql" in db_uri:
                    parts = db_uri.replace("postgresql://", "").split("@")
                    user_pass, host_part = parts[0], parts[1] if len(parts) > 1 else ""
                    user, pw = user_pass.split(":") if ":" in user_pass else (user_pass, "")
                    host_port, db_name = host_part.split("/") if "/" in host_part else ("", host_part)
                    host = host_port.split(":")[0] if ":" in host_port else host_port
                    port = host_port.split(":")[1] if ":" in host_port else "5432"
                    env = os.environ.copy()
                    if pw:
                        env["PGPASSWORD"] = pw
                    try:
                        subprocess.run(
                            ["psql", "-h", host, "-p", port, "-U", user, "-d", db_name,
                             "-f", sql_path],
                            env=env, capture_output=True, text=True, check=True, timeout=300,
                        )
                    except subprocess.CalledProcessError as e:
                        flash(_("Database restore failed: ") + e.stderr[-200:], "danger")
                        return redirect(url_for("admin.backup_list"))
                else:
                    db_path = db_uri.replace("sqlite:///", "")
                    if not os.path.isabs(db_path):
                        db_path = os.path.join(os.path.dirname(current_app.instance_path), db_path)
                    try:
                        subprocess.run(
                            ["sqlite3", db_path, f".read {sql_path}"],
                            capture_output=True, text=True, check=True, timeout=120,
                        )
                    except subprocess.CalledProcessError:
                        flash(_("Database restore failed."), "danger")
                        return redirect(url_for("admin.backup_list"))
                break

    _log_audit("Restored from backup")
    flash(_("Backup restored successfully. Please restart the application."), "success")
    return redirect(url_for("admin.backup_list"))


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
