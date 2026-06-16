from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.incident import Incident
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import IncidentForm
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate
from datetime import datetime

incidents_bp = Blueprint("incidents", __name__)


@incidents_bp.route("/")
@login_required
def list_incidents():
    status = request.args.get("status")
    severity = request.args.get("severity")
    search = request.args.get("search", "")

    query = Incident.query
    if status:
        query = query.filter_by(status=status)
    if severity:
        query = query.filter_by(severity=severity)
    if search:
        query = query.filter(Incident.title.ilike(f"%{search}%"))

    incidents = paginate(query.order_by(Incident.created_at.desc()))
    return render_template("incidents/list.html", incidents=incidents)


@incidents_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("incident_create")
def new_incident():
    form = IncidentForm()
    form.assigned_to_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        incident = Incident()
        form.populate_obj(incident)
        if form.assigned_to_id.data == 0:
            incident.assigned_to_id = None
        incident.reported_by_id = current_user.id
        db.session.add(incident)
        db.session.commit()
        _log_audit(f"Created incident: {incident.title}")
        flash(_("Incident reported successfully."), "success")
        return redirect(url_for("incidents.view_incident", incident_id=incident.id))

    return render_template("incidents/form.html", form=form, title=_("Report Incident"))


@incidents_bp.route("/<int:incident_id>")
@login_required
def view_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    return render_template("incidents/view.html", incident=incident)


@incidents_bp.route("/<int:incident_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("incident_edit")
def edit_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    form = IncidentForm(obj=incident)
    form.assigned_to_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        form.populate_obj(incident)
        if form.assigned_to_id.data == 0:
            incident.assigned_to_id = None
        if incident.status == "resolved" and not incident.resolved_at:
            incident.resolved_at = datetime.utcnow()
        if incident.status == "contained" and not incident.contained_at:
            incident.contained_at = datetime.utcnow()
        incident.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated incident: {incident.title}")
        flash(_("Incident updated successfully."), "success")
        return redirect(url_for("incidents.view_incident", incident_id=incident.id))

    form.assigned_to_id.data = incident.assigned_to_id or 0
    return render_template("incidents/form.html", form=form, title=_("Edit Incident"), incident=incident)


@incidents_bp.route("/<int:incident_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    title = incident.title
    db.session.delete(incident)
    db.session.commit()
    _log_audit_action(f"Deleted incident: {title}")
    flash(_("Incident deleted."), "success")
    return redirect(url_for("incidents.list_incidents"))


def _log_audit(details):
    _log_audit_action(details)


def _log_audit_action(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "CREATE" if "Created" in details else "UPDATE",
            resource_type="Incident",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
