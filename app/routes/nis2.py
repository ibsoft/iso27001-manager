from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.nis2 import (
    Nis2EntityRegistration, Nis2IncidentNotification, Nis2SupplyChainAssessment,
    Nis2ContinuityPlan, Nis2ComplianceCheck
)
from app.models.incident import Incident
from app.models.supplier import Supplier
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import (
    Nis2EntityForm, Nis2NotificationForm, Nis2SupplyChainForm,
    Nis2ContinuityForm, Nis2ComplianceForm
)
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate
from datetime import datetime, date

nis2_bp = Blueprint("nis2", __name__)


def _log_audit_action(details, resource_type="NIS2"):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "CREATE" if "Created" in details else "UPDATE",
            resource_type=resource_type,
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass


def _log_audit(details, resource_type="NIS2"):
    _log_audit_action(details, resource_type)


@nis2_bp.route("/")
@login_required
def dashboard():
    entity = Nis2EntityRegistration.query.first()
    total_compliance = Nis2ComplianceCheck.query.count()
    implemented_compliance = Nis2ComplianceCheck.query.filter_by(status="implemented").count()
    pending_notifications = Nis2IncidentNotification.query.filter(
        Nis2IncidentNotification.notification_status.notin_(["completed", "final_report_submitted"])
    ).count()
    active_continuity = Nis2ContinuityPlan.query.filter_by(status="active").count()
    total_supply_chain = Nis2SupplyChainAssessment.query.count()
    critical_supply_chain = Nis2SupplyChainAssessment.query.filter_by(supply_chain_risk_level="critical").count()
    overdue_reviews = Nis2SupplyChainAssessment.query.filter(
        Nis2SupplyChainAssessment.next_assessment_date < date.today()
    ).count()

    compliance_checks = Nis2ComplianceCheck.query.order_by(Nis2ComplianceCheck.measure).all()
    recent_notifications = Nis2IncidentNotification.query.order_by(Nis2IncidentNotification.created_at.desc()).limit(5).all()
    recent_continuity = Nis2ContinuityPlan.query.order_by(Nis2ContinuityPlan.updated_at.desc()).limit(5).all()

    return render_template("nis2/dashboard.html",
        entity=entity,
        total_compliance=total_compliance,
        implemented_compliance=implemented_compliance,
        pending_notifications=pending_notifications,
        active_continuity=active_continuity,
        total_supply_chain=total_supply_chain,
        critical_supply_chain=critical_supply_chain,
        overdue_reviews=overdue_reviews,
        compliance_checks=compliance_checks,
        recent_notifications=recent_notifications,
        recent_continuity=recent_continuity,
    )


@nis2_bp.route("/entity", methods=["GET", "POST"])
@login_required
@permission_required("nis2_edit")
def edit_entity():
    entity = Nis2EntityRegistration.query.first()
    form = Nis2EntityForm(obj=entity)
    if form.validate_on_submit():
        if not entity:
            entity = Nis2EntityRegistration()
        form.populate_obj(entity)
        db.session.add(entity)
        db.session.commit()
        _log_audit("Updated NIS2 entity registration", "Nis2EntityRegistration")
        flash(_("NIS2 entity registration saved."), "success")
        return redirect(url_for("nis2.dashboard"))
    return render_template("nis2/entity_form.html", form=form, entity=entity)


@nis2_bp.route("/incidents")
@login_required
def list_notifications():
    status = request.args.get("notification_status")
    search = request.args.get("search", "")
    query = Nis2IncidentNotification.query
    if status:
        query = query.filter_by(notification_status=status)
    if search:
        query = query.filter(Nis2IncidentNotification.incident_title.ilike(f"%{search}%"))
    notifications = paginate(query.order_by(Nis2IncidentNotification.created_at.desc()))
    return render_template("nis2/notifications_list.html", notifications=notifications)


@nis2_bp.route("/incidents/new", methods=["GET", "POST"])
@login_required
@permission_required("incident_create")
def new_notification():
    form = Nis2NotificationForm()
    form.incident_id.choices = [(0, _("None"))] + [(i.id, i.title) for i in Incident.query.order_by(Incident.created_at.desc()).all()]
    form.submitted_by_id = current_user.id
    if form.validate_on_submit():
        notification = Nis2IncidentNotification()
        form.populate_obj(notification)
        if form.incident_id.data == 0:
            notification.incident_id = None
        notification.submitted_by_id = current_user.id
        db.session.add(notification)
        db.session.commit()
        _log_audit(f"Created NIS2 notification: {notification.incident_title}", "Nis2IncidentNotification")
        flash(_("NIS2 incident notification created."), "success")
        return redirect(url_for("nis2.view_notification", notification_id=notification.id))
    return render_template("nis2/notification_form.html", form=form, title=_("New NIS2 Incident Notification"))


@nis2_bp.route("/incidents/<int:notification_id>")
@login_required
def view_notification(notification_id):
    notification = Nis2IncidentNotification.query.get_or_404(notification_id)
    return render_template("nis2/notification_view.html", notification=notification)


@nis2_bp.route("/incidents/<int:notification_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("incident_edit")
def edit_notification(notification_id):
    notification = Nis2IncidentNotification.query.get_or_404(notification_id)
    form = Nis2NotificationForm(obj=notification)
    form.incident_id.choices = [(0, _("None"))] + [(i.id, i.title) for i in Incident.query.order_by(Incident.created_at.desc()).all()]
    if form.validate_on_submit():
        form.populate_obj(notification)
        if form.incident_id.data == 0:
            notification.incident_id = None
        notification.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated NIS2 notification: {notification.incident_title}", "Nis2IncidentNotification")
        flash(_("NIS2 incident notification updated."), "success")
        return redirect(url_for("nis2.view_notification", notification_id=notification.id))
    form.incident_id.data = notification.incident_id or 0
    return render_template("nis2/notification_form.html", form=form, title=_("Edit NIS2 Incident Notification"), notification=notification)


@nis2_bp.route("/incidents/<int:notification_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_notification(notification_id):
    notification = Nis2IncidentNotification.query.get_or_404(notification_id)
    title = notification.incident_title
    db.session.delete(notification)
    db.session.commit()
    _log_audit_action(f"Deleted NIS2 notification: {title}", "Nis2IncidentNotification")
    flash(_("NIS2 incident notification deleted."), "success")
    return redirect(url_for("nis2.list_notifications"))


@nis2_bp.route("/supply-chain")
@login_required
def list_supply_chain():
    risk = request.args.get("supply_chain_risk_level")
    status = request.args.get("status")
    search = request.args.get("search", "")
    query = Nis2SupplyChainAssessment.query
    if risk:
        query = query.filter_by(supply_chain_risk_level=risk)
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(Nis2SupplyChainAssessment.supplier_name.ilike(f"%{search}%"))
    assessments = paginate(query.order_by(Nis2SupplyChainAssessment.supplier_name))
    return render_template("nis2/supply_chain_list.html", assessments=assessments)


@nis2_bp.route("/supply-chain/new", methods=["GET", "POST"])
@login_required
@permission_required("supplier_create")
def new_supply_chain():
    form = Nis2SupplyChainForm()
    form.supplier_id.choices = [(0, _("None"))] + [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()]
    if form.validate_on_submit():
        assessment = Nis2SupplyChainAssessment()
        form.populate_obj(assessment)
        if form.supplier_id.data == 0:
            assessment.supplier_id = None
        assessment.assessed_by_id = current_user.id
        db.session.add(assessment)
        db.session.commit()
        _log_audit(f"Created NIS2 supply chain assessment: {assessment.supplier_name}", "Nis2SupplyChainAssessment")
        flash(_("Supply chain assessment created."), "success")
        return redirect(url_for("nis2.view_supply_chain", assessment_id=assessment.id))
    return render_template("nis2/supply_chain_form.html", form=form, title=_("New Supply Chain Assessment"))


@nis2_bp.route("/supply-chain/<int:assessment_id>")
@login_required
def view_supply_chain(assessment_id):
    assessment = Nis2SupplyChainAssessment.query.get_or_404(assessment_id)
    return render_template("nis2/supply_chain_view.html", assessment=assessment)


@nis2_bp.route("/supply-chain/<int:assessment_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("supplier_edit")
def edit_supply_chain(assessment_id):
    assessment = Nis2SupplyChainAssessment.query.get_or_404(assessment_id)
    form = Nis2SupplyChainForm(obj=assessment)
    form.supplier_id.choices = [(0, _("None"))] + [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()]
    if form.validate_on_submit():
        form.populate_obj(assessment)
        if form.supplier_id.data == 0:
            assessment.supplier_id = None
        assessment.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated supply chain assessment: {assessment.supplier_name}", "Nis2SupplyChainAssessment")
        flash(_("Supply chain assessment updated."), "success")
        return redirect(url_for("nis2.view_supply_chain", assessment_id=assessment.id))
    form.supplier_id.data = assessment.supplier_id or 0
    return render_template("nis2/supply_chain_form.html", form=form, title=_("Edit Supply Chain Assessment"), assessment=assessment)


@nis2_bp.route("/supply-chain/<int:assessment_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_supply_chain(assessment_id):
    assessment = Nis2SupplyChainAssessment.query.get_or_404(assessment_id)
    name = assessment.supplier_name
    db.session.delete(assessment)
    db.session.commit()
    _log_audit_action(f"Deleted supply chain assessment: {name}", "Nis2SupplyChainAssessment")
    flash(_("Supply chain assessment deleted."), "success")
    return redirect(url_for("nis2.list_supply_chain"))


@nis2_bp.route("/continuity")
@login_required
def list_continuity():
    status = request.args.get("status")
    plan_type = request.args.get("plan_type")
    search = request.args.get("search", "")
    query = Nis2ContinuityPlan.query
    if status:
        query = query.filter_by(status=status)
    if plan_type:
        query = query.filter_by(plan_type=plan_type)
    if search:
        query = query.filter(Nis2ContinuityPlan.title.ilike(f"%{search}%"))
    plans = paginate(query.order_by(Nis2ContinuityPlan.title))
    return render_template("nis2/continuity_list.html", plans=plans)


@nis2_bp.route("/continuity/new", methods=["GET", "POST"])
@login_required
@permission_required("audit_create")
def new_continuity():
    form = Nis2ContinuityForm()
    if form.validate_on_submit():
        plan = Nis2ContinuityPlan()
        form.populate_obj(plan)
        plan.approved_by_id = current_user.id
        db.session.add(plan)
        db.session.commit()
        _log_audit(f"Created continuity plan: {plan.title}", "Nis2ContinuityPlan")
        flash(_("Continuity plan created."), "success")
        return redirect(url_for("nis2.view_continuity", plan_id=plan.id))
    return render_template("nis2/continuity_form.html", form=form, title=_("New Continuity Plan"))


@nis2_bp.route("/continuity/<int:plan_id>")
@login_required
def view_continuity(plan_id):
    plan = Nis2ContinuityPlan.query.get_or_404(plan_id)
    return render_template("nis2/continuity_view.html", plan=plan)


@nis2_bp.route("/continuity/<int:plan_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("audit_edit")
def edit_continuity(plan_id):
    plan = Nis2ContinuityPlan.query.get_or_404(plan_id)
    form = Nis2ContinuityForm(obj=plan)
    if form.validate_on_submit():
        form.populate_obj(plan)
        plan.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated continuity plan: {plan.title}", "Nis2ContinuityPlan")
        flash(_("Continuity plan updated."), "success")
        return redirect(url_for("nis2.view_continuity", plan_id=plan.id))
    return render_template("nis2/continuity_form.html", form=form, title=_("Edit Continuity Plan"), plan=plan)


@nis2_bp.route("/continuity/<int:plan_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_continuity(plan_id):
    plan = Nis2ContinuityPlan.query.get_or_404(plan_id)
    title = plan.title
    db.session.delete(plan)
    db.session.commit()
    _log_audit_action(f"Deleted continuity plan: {title}", "Nis2ContinuityPlan")
    flash(_("Continuity plan deleted."), "success")
    return redirect(url_for("nis2.list_continuity"))


@nis2_bp.route("/compliance")
@login_required
def list_compliance():
    measure = request.args.get("measure")
    status = request.args.get("status")
    query = Nis2ComplianceCheck.query
    if measure:
        query = query.filter_by(measure=measure)
    if status:
        query = query.filter_by(status=status)
    checks = paginate(query.order_by(Nis2ComplianceCheck.measure))
    return render_template("nis2/compliance_list.html", checks=checks)


@nis2_bp.route("/compliance/new", methods=["GET", "POST"])
@login_required
@permission_required("risk_edit")
def new_compliance():
    form = Nis2ComplianceForm()
    form.responsible_person_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        check = Nis2ComplianceCheck()
        form.populate_obj(check)
        if form.responsible_person_id.data == 0:
            check.responsible_person_id = None
        db.session.add(check)
        db.session.commit()
        _log_audit(f"Created compliance check: {check.measure_display}", "Nis2ComplianceCheck")
        flash(_("Compliance check created."), "success")
        return redirect(url_for("nis2.view_compliance", check_id=check.id))
    return render_template("nis2/compliance_form.html", form=form, title=_("New Compliance Check"))


@nis2_bp.route("/compliance/<int:check_id>")
@login_required
def view_compliance(check_id):
    check = Nis2ComplianceCheck.query.get_or_404(check_id)
    return render_template("nis2/compliance_view.html", check=check)


@nis2_bp.route("/compliance/<int:check_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("risk_edit")
def edit_compliance(check_id):
    check = Nis2ComplianceCheck.query.get_or_404(check_id)
    form = Nis2ComplianceForm(obj=check)
    form.responsible_person_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        form.populate_obj(check)
        if form.responsible_person_id.data == 0:
            check.responsible_person_id = None
        check.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated compliance check: {check.measure_display}", "Nis2ComplianceCheck")
        flash(_("Compliance check updated."), "success")
        return redirect(url_for("nis2.view_compliance", check_id=check.id))
    form.responsible_person_id.data = check.responsible_person_id or 0
    return render_template("nis2/compliance_form.html", form=form, title=_("Edit Compliance Check"), check=check)


@nis2_bp.route("/compliance/<int:check_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_compliance(check_id):
    check = Nis2ComplianceCheck.query.get_or_404(check_id)
    name = check.measure_display
    db.session.delete(check)
    db.session.commit()
    _log_audit_action(f"Deleted compliance check: {name}", "Nis2ComplianceCheck")
    flash(_("Compliance check deleted."), "success")
    return redirect(url_for("nis2.list_compliance"))
