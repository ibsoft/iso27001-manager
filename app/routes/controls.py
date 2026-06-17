from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.control import Control
from app.models.domain import Domain
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.soa import SoAEntry
from app.models.risk import risk_controls
from app.models.audit import AuditFinding
from app.forms import ControlForm
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate
from datetime import datetime

controls_bp = Blueprint("controls", __name__)


@controls_bp.route("/")
@login_required
def list_controls():
    domain_id = request.args.get("domain_id", type=int)
    status = request.args.get("status")
    search = request.args.get("search", "")

    query = Control.query

    if domain_id:
        query = query.filter_by(domain_id=domain_id)
    if status:
        query = query.filter_by(implementation_status=status)
    if search:
        query = query.filter(
            db.or_(
                Control.title.ilike(f"%{search}%"),
                Control.code.ilike(f"%{search}%"),
                Control.description.ilike(f"%{search}%"),
            )
        )

    controls = paginate(query.order_by(Control.code))
    domains = Domain.query.order_by(Domain.code).all()
    return render_template("controls/list.html", controls=controls, domains=domains,
                           selected_domain=domain_id, selected_status=status, search=search)


@controls_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("control_create")
def new_control():
    from flask import session
    form = ControlForm()
    lang = session.get("lang", "en")
    form.domain_id.choices = [(d.id, f"{d.code}. {d.localized_name(lang)}") for d in Domain.query.order_by(Domain.code).all()]
    form.owner_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        control = Control()
        form.populate_obj(control)
        if form.owner_id.data == 0:
            control.owner_id = None
        db.session.add(control)
        db.session.commit()
        _log_audit(f"Created control {control.code}: {control.title}")
        flash(_("Control created successfully."), "success")
        return redirect(url_for("controls.view_control", control_id=control.id))

    return render_template("controls/form.html", form=form, title=_("New Control"), control=None)


@controls_bp.route("/<int:control_id>")
@login_required
def view_control(control_id):
    control = Control.query.get_or_404(control_id)
    return render_template("controls/view.html", control=control)


@controls_bp.route("/<int:control_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("control_edit")
def edit_control(control_id):
    from flask import session
    control = Control.query.get_or_404(control_id)
    form = ControlForm(obj=control)
    lang = session.get("lang", "en")
    form.domain_id.choices = [(d.id, f"{d.code}. {d.localized_name(lang)}") for d in Domain.query.order_by(Domain.code).all()]
    form.owner_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]

    if lang == "el" and not form.validate_on_submit():
        form.title.data = control.localized_title("el")
        form.description.data = control.localized_description("el")
        form.detailed_description.data = control.localized_detailed_description("el")
        form.purpose.data = control.localized_purpose("el")
        form.guidance.data = control.localized_guidance("el")

    if form.validate_on_submit():
        form.populate_obj(control)
        if form.owner_id.data == 0:
            control.owner_id = None
        control.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated control {control.code}: {control.title}")
        flash(_("Control updated successfully."), "success")
        return redirect(url_for("controls.view_control", control_id=control.id))

    form.owner_id.data = control.owner_id or 0
    return render_template("controls/form.html", form=form, title=_("Edit Control"), control=control)


@controls_bp.route("/<int:control_id>/update-status", methods=["POST"])
@login_required
@permission_required("control_edit")
def update_status(control_id):
    control = Control.query.get_or_404(control_id)
    new_status = request.form.get("implementation_status")
    if new_status in ["not_started", "in_progress", "implemented", "not_applicable"]:
        control.implementation_status = new_status
        control.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Changed control {control.code} status to {new_status}")
        flash(_("Status updated."), "success")
    return redirect(url_for("controls.view_control", control_id=control.id))


@controls_bp.route("/<int:control_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_control(control_id):
    control = Control.query.get_or_404(control_id)
    code = control.code
    SoAEntry.query.filter_by(control_id=control.id).delete()
    db.session.execute(risk_controls.delete().where(risk_controls.c.control_id == control.id))
    AuditFinding.query.filter_by(control_id=control.id).update({"control_id": None})
    db.session.delete(control)
    db.session.commit()
    _log_audit_action(f"Deleted control {code}: {control.title}")
    flash(_("Control deleted."), "success")
    return redirect(url_for("controls.list_controls"))


def _log_audit(details):
    _log_audit_action(details)


def _log_audit_action(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "UPDATE",
            resource_type="Control",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
