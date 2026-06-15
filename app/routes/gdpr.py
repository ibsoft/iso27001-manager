from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.utils.decorators import admin_required
from app.extensions import db
from app.models.processing import ProcessingActivity
from app.models.dpia import Dpia
from app.models.data_subject_request import DataSubjectRequest
from app.models.consent import ConsentRecord
from app.models.data_controller import DataControllerProcessor
from app.models.privacy_notice import PrivacyNotice
from app.models.data_breach import DataBreach
from app.models.incident import Incident
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import (
    ProcessingActivityForm, DpiaForm, DataSubjectRequestForm,
    ConsentRecordForm, DataControllerForm, PrivacyNoticeForm, DataBreachForm,
)
from datetime import datetime, timedelta

gdpr_bp = Blueprint("gdpr", __name__)


def _set_assignee_choices(form):
    if hasattr(form, "assigned_to_id"):
        form.assigned_to_id.choices = [(0, _("Unassigned"))] + [
            (u.id, f"{u.first_name} {u.last_name}")
            for u in User.query.filter_by(is_active=True).all()
        ]


def _log_audit(details, resource_type="GDPR"):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="CREATE" if "Created" in details else "UPDATE",
            resource_type=resource_type,
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass


# ─── ROPA: Processing Activities ───────────────────────────────────

@gdpr_bp.route("/processing")
@login_required
def list_processing():
    status = request.args.get("status")
    search = request.args.get("search", "")
    query = ProcessingActivity.query
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(ProcessingActivity.name.ilike(f"%{search}%"))
    activities = query.order_by(ProcessingActivity.name).all()
    return render_template("gdpr/processing/list.html", activities=activities)


@gdpr_bp.route("/processing/new", methods=["GET", "POST"])
@login_required
def new_processing():
    form = ProcessingActivityForm()
    if form.validate_on_submit():
        activity = ProcessingActivity()
        form.populate_obj(activity)
        activity.created_by_id = current_user.id
        db.session.add(activity)
        db.session.commit()
        _log_audit(f"Created processing activity: {activity.name}", "ProcessingActivity")
        flash(_("Processing activity created."), "success")
        return redirect(url_for("gdpr.view_processing", activity_id=activity.id))
    return render_template("gdpr/processing/form.html", form=form, title=_("New Processing Activity"))


@gdpr_bp.route("/processing/<int:activity_id>")
@login_required
def view_processing(activity_id):
    activity = ProcessingActivity.query.get_or_404(activity_id)
    return render_template("gdpr/processing/view.html", activity=activity)


@gdpr_bp.route("/processing/<int:activity_id>/edit", methods=["GET", "POST"])
@login_required
def edit_processing(activity_id):
    activity = ProcessingActivity.query.get_or_404(activity_id)
    form = ProcessingActivityForm(obj=activity)
    if form.validate_on_submit():
        form.populate_obj(activity)
        activity.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated processing activity: {activity.name}", "ProcessingActivity")
        flash(_("Processing activity updated."), "success")
        return redirect(url_for("gdpr.view_processing", activity_id=activity.id))
    return render_template("gdpr/processing/form.html", form=form, title=_("Edit Processing Activity"), activity=activity)


@gdpr_bp.route("/processing/<int:activity_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_processing(activity_id):
    activity = ProcessingActivity.query.get_or_404(activity_id)
    db.session.delete(activity)
    db.session.commit()
    _log_audit(f"Deleted processing activity: {activity.name}", "ProcessingActivity")
    flash(_("Processing activity deleted."), "success")
    return redirect(url_for("gdpr.list_processing"))


# ─── DPIA ──────────────────────────────────────────────────────────

@gdpr_bp.route("/dpia")
@login_required
def list_dpia():
    status = request.args.get("status")
    query = Dpia.query
    if status:
        query = query.filter_by(status=status)
    dpias = query.order_by(Dpia.created_at.desc()).all()
    return render_template("gdpr/dpia/list.html", dpias=dpias)


@gdpr_bp.route("/dpia/new", methods=["GET", "POST"])
@login_required
def new_dpia():
    form = DpiaForm()
    if form.validate_on_submit():
        dpia = Dpia()
        form.populate_obj(dpia)
        dpia.created_by_id = current_user.id
        db.session.add(dpia)
        db.session.commit()
        _log_audit(f"Created DPIA: {dpia.project_name}", "DPIA")
        flash(_("DPIA created."), "success")
        return redirect(url_for("gdpr.view_dpia", dpia_id=dpia.id))
    return render_template("gdpr/dpia/form.html", form=form, title=_("New DPIA"))


@gdpr_bp.route("/dpia/<int:dpia_id>")
@login_required
def view_dpia(dpia_id):
    dpia = Dpia.query.get_or_404(dpia_id)
    return render_template("gdpr/dpia/view.html", dpia=dpia)


@gdpr_bp.route("/dpia/<int:dpia_id>/edit", methods=["GET", "POST"])
@login_required
def edit_dpia(dpia_id):
    dpia = Dpia.query.get_or_404(dpia_id)
    form = DpiaForm(obj=dpia)
    if form.validate_on_submit():
        form.populate_obj(dpia)
        dpia.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated DPIA: {dpia.project_name}", "DPIA")
        flash(_("DPIA updated."), "success")
        return redirect(url_for("gdpr.view_dpia", dpia_id=dpia.id))
    return render_template("gdpr/dpia/form.html", form=form, title=_("Edit DPIA"), dpia=dpia)


@gdpr_bp.route("/dpia/<int:dpia_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_dpia(dpia_id):
    dpia = Dpia.query.get_or_404(dpia_id)
    db.session.delete(dpia)
    db.session.commit()
    _log_audit(f"Deleted DPIA: {dpia.project_name}", "DPIA")
    flash(_("DPIA deleted."), "success")
    return redirect(url_for("gdpr.list_dpia"))


# ─── Data Subject Requests ─────────────────────────────────────────

@gdpr_bp.route("/dsar")
@login_required
def list_dsar():
    status = request.args.get("status")
    req_type = request.args.get("request_type")
    search = request.args.get("search", "")
    query = DataSubjectRequest.query
    if status:
        query = query.filter_by(status=status)
    if req_type:
        query = query.filter_by(request_type=req_type)
    if search:
        query = query.filter(
            db.or_(
                DataSubjectRequest.requester_name.ilike(f"%{search}%"),
                DataSubjectRequest.requester_email.ilike(f"%{search}%"),
            )
        )
    requests = query.order_by(DataSubjectRequest.received_date.desc()).all()
    return render_template("gdpr/dsar/list.html", requests=requests)


@gdpr_bp.route("/dsar/new", methods=["GET", "POST"])
@login_required
def new_dsar():
    form = DataSubjectRequestForm()
    _set_assignee_choices(form)
    if form.validate_on_submit():
        dsar = DataSubjectRequest()
        form.populate_obj(dsar)
        if form.assigned_to_id.data == 0:
            dsar.assigned_to_id = None
        dsar.received_date = datetime.utcnow()
        dsar.deadline_date = datetime.utcnow() + timedelta(days=30)
        dsar.created_by_id = current_user.id
        db.session.add(dsar)
        db.session.commit()
        _log_audit(f"Created DSAR: {dsar.requester_name} ({dsar.request_type})", "DSAR")
        flash(_("Data subject request created. Deadline: {}").format(dsar.deadline_date.strftime("%Y-%m-%d")), "success")
        return redirect(url_for("gdpr.view_dsar", dsar_id=dsar.id))
    return render_template("gdpr/dsar/form.html", form=form, title=_("New Data Subject Request"))


@gdpr_bp.route("/dsar/<int:dsar_id>")
@login_required
def view_dsar(dsar_id):
    dsar = DataSubjectRequest.query.get_or_404(dsar_id)
    return render_template("gdpr/dsar/view.html", dsar=dsar)


@gdpr_bp.route("/dsar/<int:dsar_id>/edit", methods=["GET", "POST"])
@login_required
def edit_dsar(dsar_id):
    dsar = DataSubjectRequest.query.get_or_404(dsar_id)
    form = DataSubjectRequestForm(obj=dsar)
    _set_assignee_choices(form)
    if form.validate_on_submit():
        form.populate_obj(dsar)
        if form.assigned_to_id.data == 0:
            dsar.assigned_to_id = None
        if form.outcome.data and not dsar.response_date:
            dsar.response_date = datetime.utcnow()
        if form.extension_granted.data and not dsar.extension_deadline.data:
            dsar.extension_deadline = (dsar.deadline_date or datetime.utcnow()) + timedelta(days=60)
        dsar.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated DSAR: {dsar.requester_name}", "DSAR")
        flash(_("Data subject request updated."), "success")
        return redirect(url_for("gdpr.view_dsar", dsar_id=dsar.id))
    form.assigned_to_id.data = dsar.assigned_to_id or 0
    return render_template("gdpr/dsar/form.html", form=form, title=_("Edit Data Subject Request"), dsar=dsar)


@gdpr_bp.route("/dsar/<int:dsar_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_dsar(dsar_id):
    dsar = DataSubjectRequest.query.get_or_404(dsar_id)
    db.session.delete(dsar)
    db.session.commit()
    _log_audit(f"Deleted DSAR: {dsar.requester_name}", "DSAR")
    flash(_("Data subject request deleted."), "success")
    return redirect(url_for("gdpr.list_dsar"))


# ─── Consent Records ───────────────────────────────────────────────

@gdpr_bp.route("/consent")
@login_required
def list_consent():
    search = request.args.get("search", "")
    status_filter = request.args.get("status")
    query = ConsentRecord.query
    if status_filter == "active":
        query = query.filter_by(granted=True).filter(ConsentRecord.withdrawn_at.is_(None))
    elif status_filter == "withdrawn":
        query = query.filter(ConsentRecord.withdrawn_at.isnot(None))
    if search:
        query = query.filter(
            db.or_(
                ConsentRecord.data_subject_identifier.ilike(f"%{search}%"),
                ConsentRecord.processing_purpose.ilike(f"%{search}%"),
            )
        )
    records = query.order_by(ConsentRecord.consent_given_at.desc()).all()
    return render_template("gdpr/consent/list.html", records=records)


@gdpr_bp.route("/consent/new", methods=["GET", "POST"])
@login_required
def new_consent():
    form = ConsentRecordForm()
    if form.validate_on_submit():
        record = ConsentRecord()
        form.populate_obj(record)
        record.created_by_id = current_user.id
        db.session.add(record)
        db.session.commit()
        _log_audit(f"Created consent record for {record.data_subject_identifier}", "Consent")
        flash(_("Consent record created."), "success")
        return redirect(url_for("gdpr.list_consent"))
    return render_template("gdpr/consent/form.html", form=form, title=_("New Consent Record"))


@gdpr_bp.route("/consent/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit_consent(record_id):
    record = ConsentRecord.query.get_or_404(record_id)
    form = ConsentRecordForm(obj=record)
    if form.validate_on_submit():
        form.populate_obj(record)
        record.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated consent record for {record.data_subject_identifier}", "Consent")
        flash(_("Consent record updated."), "success")
        return redirect(url_for("gdpr.list_consent"))
    return render_template("gdpr/consent/form.html", form=form, title=_("Edit Consent Record"), record=record)


@gdpr_bp.route("/consent/<int:record_id>/withdraw", methods=["POST"])
@login_required
def withdraw_consent(record_id):
    record = ConsentRecord.query.get_or_404(record_id)
    record.granted = False
    record.withdrawn_at = datetime.utcnow()
    record.withdrawn_source = "manual"
    db.session.commit()
    _log_audit(f"Withdrew consent for {record.data_subject_identifier}", "Consent")
    flash(_("Consent withdrawn."), "success")
    return redirect(url_for("gdpr.list_consent"))


@gdpr_bp.route("/consent/<int:record_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_consent(record_id):
    record = ConsentRecord.query.get_or_404(record_id)
    db.session.delete(record)
    db.session.commit()
    _log_audit(f"Deleted consent record for {record.data_subject_identifier}", "Consent")
    flash(_("Consent record deleted."), "success")
    return redirect(url_for("gdpr.list_consent"))


# ─── Data Controllers / Processors ─────────────────────────────────

@gdpr_bp.route("/controllers")
@login_required
def list_controllers():
    role_filter = request.args.get("role")
    search = request.args.get("search", "")
    query = DataControllerProcessor.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    if search:
        query = query.filter(DataControllerProcessor.name.ilike(f"%{search}%"))
    entities = query.order_by(DataControllerProcessor.name).all()
    return render_template("gdpr/controllers/list.html", entities=entities)


@gdpr_bp.route("/controllers/new", methods=["GET", "POST"])
@login_required
def new_controller():
    form = DataControllerForm()
    if form.validate_on_submit():
        entity = DataControllerProcessor()
        form.populate_obj(entity)
        entity.created_by_id = current_user.id
        db.session.add(entity)
        db.session.commit()
        _log_audit(f"Created {entity.role}: {entity.name}", "DataController")
        flash(_("Entity created."), "success")
        return redirect(url_for("gdpr.view_controller", entity_id=entity.id))
    return render_template("gdpr/controllers/form.html", form=form, title=_("New Data Controller / Processor"))


@gdpr_bp.route("/controllers/<int:entity_id>")
@login_required
def view_controller(entity_id):
    entity = DataControllerProcessor.query.get_or_404(entity_id)
    return render_template("gdpr/controllers/view.html", entity=entity)


@gdpr_bp.route("/controllers/<int:entity_id>/edit", methods=["GET", "POST"])
@login_required
def edit_controller(entity_id):
    entity = DataControllerProcessor.query.get_or_404(entity_id)
    form = DataControllerForm(obj=entity)
    if form.validate_on_submit():
        form.populate_obj(entity)
        entity.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated {entity.role}: {entity.name}", "DataController")
        flash(_("Entity updated."), "success")
        return redirect(url_for("gdpr.view_controller", entity_id=entity.id))
    return render_template("gdpr/controllers/form.html", form=form, title=_("Edit Data Controller / Processor"), entity=entity)


@gdpr_bp.route("/controllers/<int:entity_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_controller(entity_id):
    entity = DataControllerProcessor.query.get_or_404(entity_id)
    db.session.delete(entity)
    db.session.commit()
    _log_audit(f"Deleted {entity.role}: {entity.name}", "DataController")
    flash(_("Entity deleted."), "success")
    return redirect(url_for("gdpr.list_controllers"))


# ─── Privacy Notices ───────────────────────────────────────────────

@gdpr_bp.route("/notices")
@login_required
def list_notices():
    status = request.args.get("status")
    query = PrivacyNotice.query
    if status:
        query = query.filter_by(status=status)
    notices = query.order_by(PrivacyNotice.created_at.desc()).all()
    return render_template("gdpr/notices/list.html", notices=notices)


@gdpr_bp.route("/notices/new", methods=["GET", "POST"])
@login_required
def new_notice():
    form = PrivacyNoticeForm()
    if form.validate_on_submit():
        notice = PrivacyNotice()
        form.populate_obj(notice)
        notice.created_by_id = current_user.id
        db.session.add(notice)
        db.session.commit()
        _log_audit(f"Created privacy notice: {notice.title}", "PrivacyNotice")
        flash(_("Privacy notice created."), "success")
        return redirect(url_for("gdpr.view_notice", notice_id=notice.id))
    return render_template("gdpr/notices/form.html", form=form, title=_("New Privacy Notice"))


@gdpr_bp.route("/notices/<int:notice_id>")
@login_required
def view_notice(notice_id):
    notice = PrivacyNotice.query.get_or_404(notice_id)
    return render_template("gdpr/notices/view.html", notice=notice)


@gdpr_bp.route("/notices/<int:notice_id>/edit", methods=["GET", "POST"])
@login_required
def edit_notice(notice_id):
    notice = PrivacyNotice.query.get_or_404(notice_id)
    form = PrivacyNoticeForm(obj=notice)
    if form.validate_on_submit():
        form.populate_obj(notice)
        notice.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated privacy notice: {notice.title}", "PrivacyNotice")
        flash(_("Privacy notice updated."), "success")
        return redirect(url_for("gdpr.view_notice", notice_id=notice.id))
    return render_template("gdpr/notices/form.html", form=form, title=_("Edit Privacy Notice"), notice=notice)


@gdpr_bp.route("/notices/<int:notice_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_notice(notice_id):
    notice = PrivacyNotice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    _log_audit(f"Deleted privacy notice: {notice.title}", "PrivacyNotice")
    flash(_("Privacy notice deleted."), "success")
    return redirect(url_for("gdpr.list_notices"))


# ─── Data Breach (linked to incident) ──────────────────────────────

@gdpr_bp.route("/breach/<int:incident_id>", methods=["GET", "POST"])
@login_required
def edit_breach(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    breach = incident.data_breach
    if not breach:
        breach = DataBreach(incident_id=incident.id)
        db.session.add(breach)
        db.session.commit()

    form = DataBreachForm(obj=breach)
    if form.validate_on_submit():
        form.populate_obj(breach)
        breach.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated data breach for incident: {incident.title}", "DataBreach")
        flash(_("Data breach details updated."), "success")
        return redirect(url_for("incidents.view_incident", incident_id=incident.id))
    return render_template("gdpr/breach/form.html", form=form, incident=incident)


# ─── GDPR Dashboard ────────────────────────────────────────────────

@gdpr_bp.route("/dashboard")
@login_required
def gdpr_dashboard():
    total_activities = ProcessingActivity.query.count()
    active_activities = ProcessingActivity.query.filter_by(status="active").count()
    total_dpias = Dpia.query.count()
    approved_dpias = Dpia.query.filter_by(status="approved").count()
    open_dsars = DataSubjectRequest.query.filter(
        DataSubjectRequest.status.in_(["open", "in_progress", "awaiting_info"])
    ).count()
    overdue_dsars = DataSubjectRequest.query.filter(
        DataSubjectRequest.deadline_date < datetime.utcnow(),
        DataSubjectRequest.status.in_(["open", "in_progress", "awaiting_info"]),
    ).count()
    active_consents = ConsentRecord.query.filter_by(granted=True).filter(
        ConsentRecord.withdrawn_at.is_(None)
    ).count()
    data_breaches = DataBreach.query.count()
    notified_sa = DataBreach.query.filter_by(notified_supervisory_authority=True).count()
    return render_template("gdpr/dashboard.html",
        total_activities=total_activities,
        active_activities=active_activities,
        total_dpias=total_dpias,
        approved_dpias=approved_dpias,
        open_dsars=open_dsars,
        overdue_dsars=overdue_dsars,
        active_consents=active_consents,
        data_breaches=data_breaches,
        notified_sa=notified_sa,
    )
