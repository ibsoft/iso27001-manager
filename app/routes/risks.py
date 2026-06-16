from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.risk import Risk, RiskTreatment, risk_controls
from app.models.asset import Asset
from app.models.control import Control
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import RiskForm
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate
from datetime import datetime

risks_bp = Blueprint("risks", __name__)


@risks_bp.route("/")
@login_required
def list_risks():
    status = request.args.get("status")
    risk_level = request.args.get("risk_level")
    search = request.args.get("search", "")

    query = Risk.query
    if status:
        query = query.filter_by(status=status)
    if risk_level:
        query = query.filter_by(risk_level=risk_level)
    if search:
        query = query.filter(Risk.title.ilike(f"%{search}%"))

    risks = paginate(query.order_by(Risk.created_at.desc()))
    return render_template("risks/list.html", risks=risks)


@risks_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("risk_create")
def new_risk():
    form = RiskForm()
    form.asset_id.choices = [(0, _("No specific asset"))] + [(a.id, a.name) for a in Asset.query.filter_by(status="active").all()]
    form.owner_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        risk = Risk()
        form.populate_obj(risk)
        if form.asset_id.data == 0:
            risk.asset_id = None
        if form.owner_id.data == 0:
            risk.owner_id = None
        if form.residual_likelihood.data == 0:
            risk.residual_likelihood = None
        if form.residual_impact.data == 0:
            risk.residual_impact = None
        risk.calculate_risk_level()
        risk.calculate_residual_risk()
        db.session.add(risk)
        db.session.commit()
        _log_audit(f"Created risk: {risk.title}")
        flash(_("Risk created successfully."), "success")
        return redirect(url_for("risks.view_risk", risk_id=risk.id))

    return render_template("risks/form.html", form=form, title=_("New Risk Assessment"))


@risks_bp.route("/<int:risk_id>")
@login_required
def view_risk(risk_id):
    risk = Risk.query.get_or_404(risk_id)
    return render_template("risks/view.html", risk=risk)


@risks_bp.route("/<int:risk_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("risk_edit")
def edit_risk(risk_id):
    risk = Risk.query.get_or_404(risk_id)
    form = RiskForm(obj=risk)
    form.asset_id.choices = [(0, _("No specific asset"))] + [(a.id, a.name) for a in Asset.query.filter_by(status="active").all()]
    form.owner_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        form.populate_obj(risk)
        if form.asset_id.data == 0:
            risk.asset_id = None
        if form.owner_id.data == 0:
            risk.owner_id = None
        if form.residual_likelihood.data == 0:
            risk.residual_likelihood = None
        if form.residual_impact.data == 0:
            risk.residual_impact = None
        risk.calculate_risk_level()
        risk.calculate_residual_risk()
        if risk.status == "closed" and not risk.closed_date:
            risk.closed_date = datetime.utcnow()
        risk.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated risk: {risk.title}")
        flash(_("Risk updated successfully."), "success")
        return redirect(url_for("risks.view_risk", risk_id=risk.id))

    form.asset_id.data = risk.asset_id or 0
    form.owner_id.data = risk.owner_id or 0
    form.residual_likelihood.data = risk.residual_likelihood or 0
    form.residual_impact.data = risk.residual_impact or 0
    return render_template("risks/form.html", form=form, title=_("Edit Risk Assessment"), risk=risk)


@risks_bp.route("/risk-matrix")
@login_required
def risk_matrix():
    risks = Risk.query.all()
    return render_template("risks/matrix.html", risks=risks)


@risks_bp.route("/<int:risk_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_risk(risk_id):
    risk = Risk.query.get_or_404(risk_id)
    title = risk.title
    db.session.delete(risk)
    db.session.commit()
    _log_audit_action(f"Deleted risk: {title}")
    flash(_("Risk deleted."), "success")
    return redirect(url_for("risks.list_risks"))


def _log_audit(details):
    _log_audit_action(details)


def _log_audit_action(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "CREATE" if "Created" in details else "UPDATE",
            resource_type="Risk",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
