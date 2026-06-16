from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.user import User, Role, Permission
from app.models.audit_log import AuditLog
from app.forms import UserForm
from app.utils.decorators import admin_required
from app.utils.pagination import paginate
from datetime import datetime

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
