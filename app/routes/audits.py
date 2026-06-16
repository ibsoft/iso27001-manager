from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.audit import InternalAudit, AuditFinding, NonConformity, CorrectiveAction
from app.models.control import Control
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import AuditForm, AuditFindingForm, CorrectiveActionForm
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate
from datetime import datetime

audits_bp = Blueprint("audits", __name__)


@audits_bp.route("/")
@login_required
def list_audits():
    status = request.args.get("status")
    query = InternalAudit.query
    if status:
        query = query.filter_by(status=status)
    audits = paginate(query.order_by(InternalAudit.audit_date.desc()))
    return render_template("audits/list.html", audits=audits)


@audits_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("audit_create")
def new_audit():
    form = AuditForm()
    form.lead_auditor_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        audit = InternalAudit()
        form.populate_obj(audit)
        if form.lead_auditor_id.data == 0:
            audit.lead_auditor_id = None
        db.session.add(audit)
        db.session.commit()
        _log_audit(f"Created audit: {audit.title}")
        flash(_("Audit created successfully."), "success")
        return redirect(url_for("audits.view_audit", audit_id=audit.id))

    return render_template("audits/form.html", form=form, title=_("New Internal Audit"))


@audits_bp.route("/<int:audit_id>")
@login_required
def view_audit(audit_id):
    audit = InternalAudit.query.get_or_404(audit_id)
    return render_template("audits/view.html", audit=audit)


@audits_bp.route("/<int:audit_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("audit_edit")
def edit_audit(audit_id):
    audit = InternalAudit.query.get_or_404(audit_id)
    form = AuditForm(obj=audit)
    form.lead_auditor_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        form.populate_obj(audit)
        if form.lead_auditor_id.data == 0:
            audit.lead_auditor_id = None
        audit.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated audit: {audit.title}")
        flash(_("Audit updated successfully."), "success")
        return redirect(url_for("audits.view_audit", audit_id=audit.id))

    form.lead_auditor_id.data = audit.lead_auditor_id or 0
    return render_template("audits/form.html", form=form, title=_("Edit Audit"), audit=audit)


@audits_bp.route("/<int:audit_id>/findings/new", methods=["GET", "POST"])
@login_required
@permission_required("audit_create")
def new_finding(audit_id):
    audit = InternalAudit.query.get_or_404(audit_id)
    form = AuditFindingForm()
    form.control_id.choices = [(0, _("No specific control"))] + [(c.id, f"{c.code} - {c.title}") for c in Control.query.order_by(Control.code).all()]

    if form.validate_on_submit():
        finding = AuditFinding(audit_id=audit.id)
        form.populate_obj(finding)
        if form.control_id.data == 0:
            finding.control_id = None
        db.session.add(finding)
        db.session.commit()
        _log_audit(f"Added finding to audit: {audit.title}")
        flash(_("Finding added successfully."), "success")
        return redirect(url_for("audits.view_audit", audit_id=audit.id))

    return render_template("audits/finding_form.html", form=form, audit=audit, title=_("Add Finding"))


@audits_bp.route("/non-conformities")
@login_required
def list_non_conformities():
    status = request.args.get("status")
    query = NonConformity.query
    if status:
        query = query.filter_by(status=status)
    ncs = paginate(query.order_by(NonConformity.created_at.desc()))
    return render_template("audits/non_conformities.html", non_conformities=ncs)


@audits_bp.route("/corrective-actions")
@login_required
def list_corrective_actions():
    status = request.args.get("status")
    query = CorrectiveAction.query
    if status:
        query = query.filter_by(status=status)
    actions = paginate(query.order_by(CorrectiveAction.created_at.desc()))
    return render_template("audits/corrective_actions.html", actions=actions)


@audits_bp.route("/<int:audit_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_audit(audit_id):
    audit = InternalAudit.query.get_or_404(audit_id)
    title = audit.title
    db.session.delete(audit)
    db.session.commit()
    _log_audit_action(f"Deleted audit: {title}")
    flash(_("Audit deleted."), "success")
    return redirect(url_for("audits.list_audits"))


@audits_bp.route("/<int:audit_id>/findings/<int:finding_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_finding(audit_id, finding_id):
    finding = AuditFinding.query.get_or_404(finding_id)
    db.session.delete(finding)
    db.session.commit()
    _log_audit_action(f"Deleted finding from audit {audit_id}")
    flash(_("Finding deleted."), "success")
    return redirect(url_for("audits.view_audit", audit_id=audit_id))


def _log_audit(details):
    _log_audit_action(details)


def _log_audit_action(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "CREATE" if "Created" in details or "Added" in details else "UPDATE",
            resource_type="Audit",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
