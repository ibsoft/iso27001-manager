from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.capa import CapaRequest
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import CapaRequestForm
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate
from datetime import datetime, date

capa_bp = Blueprint("capa", __name__)


@capa_bp.route("/")
@login_required
def list_capas():
    status = request.args.get("status")
    source = request.args.get("source")
    query = CapaRequest.query
    if status:
        query = query.filter_by(status=status)
    if source:
        query = query.filter_by(source_type=source)
    capas = paginate(query.order_by(CapaRequest.created_at.desc()))
    open_count = CapaRequest.query.filter(
        CapaRequest.status.in_(["open", "under_review", "action_planned", "in_progress"])
    ).count()
    critical_count = CapaRequest.query.filter_by(severity="critical").filter(
        CapaRequest.status.in_(["open", "under_review", "action_planned", "in_progress"])
    ).count()
    return render_template("capa/list.html", capas=capas, open_count=open_count,
                           critical_count=critical_count)


@capa_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("capa_create")
def new_capa():
    form = CapaRequestForm()
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    form.action_owner_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    form.assigned_to_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    form.created_by_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    if form.validate_on_submit():
        capa = CapaRequest()
        form.populate_obj(capa)
        for fld in ["action_owner_id", "created_by_id", "assigned_to_id"]:
            if getattr(form, fld).data == 0:
                setattr(capa, fld, None)
        if not capa.created_by_id:
            capa.created_by_id = current_user.id
        db.session.add(capa)
        db.session.commit()
        _log_audit(f"Created CAPA: {capa.title}")
        flash(_("CAPA request created successfully."), "success")
        return redirect(url_for("capa.view_capa", capa_id=capa.id))
    return render_template("capa/form.html", form=form, title=_("New Corrective and Preventive Action (CAPA) Request"))


@capa_bp.route("/<int:capa_id>")
@login_required
def view_capa(capa_id):
    capa = CapaRequest.query.get_or_404(capa_id)
    can_edit = current_user.has_permission("capa_edit") or capa.assigned_to_id == current_user.id
    return render_template("capa/view.html", capa=capa, can_edit=can_edit)


@capa_bp.route("/<int:capa_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("capa_edit")
def edit_capa(capa_id):
    capa = CapaRequest.query.get_or_404(capa_id)
    form = CapaRequestForm(obj=capa)
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    form.action_owner_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    form.assigned_to_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    form.created_by_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    if form.validate_on_submit():
        form.populate_obj(capa)
        for fld in ["action_owner_id", "created_by_id", "assigned_to_id"]:
            if getattr(form, fld).data == 0:
                setattr(capa, fld, None)
        if capa.status == "closed" and not capa.completed_date:
            capa.completed_date = datetime.utcnow()
        capa.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated CAPA: {capa.title}")
        flash(_("CAPA request updated successfully."), "success")
        return redirect(url_for("capa.view_capa", capa_id=capa.id))
    for fld in ["action_owner_id", "created_by_id", "assigned_to_id"]:
        val = getattr(capa, fld, None)
        if val is None:
            getattr(form, fld).data = 0
    return render_template("capa/form.html", form=form, title=_("Edit Corrective and Preventive Action (CAPA) Request"), capa=capa)


@capa_bp.route("/<int:capa_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_capa(capa_id):
    capa = CapaRequest.query.get_or_404(capa_id)
    title = capa.title
    db.session.delete(capa)
    db.session.commit()
    _log_audit_action(f"Deleted CAPA: {title}")
    flash(_("CAPA request deleted."), "success")
    return redirect(url_for("capa.list_capas"))


@capa_bp.route("/<int:capa_id>/status/<new_status>", methods=["POST"])
@login_required
def update_status(capa_id, new_status):
    valid = ["open", "under_review", "action_planned", "in_progress", "verified", "closed"]
    if new_status not in valid:
        flash(_("Invalid status."), "danger")
        return redirect(url_for("capa.view_capa", capa_id=capa_id))
    capa = CapaRequest.query.get_or_404(capa_id)
    capa.status = new_status
    if new_status == "closed" and not capa.completed_date:
        capa.completed_date = datetime.utcnow()
    db.session.commit()
    _log_audit_action(f"Updated CAPA {capa.id} status to {new_status}")
    flash(_("Status updated to %(status)s.", status=new_status.replace("_", " ").title()), "success")
    return redirect(url_for("capa.view_capa", capa_id=capa_id))


def _log_audit(details):
    _log_audit_action(details)


def _log_audit_action(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "CREATE" if "Created" in details else "UPDATE",
            resource_type="CAPA",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
