import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.control import Control
from app.models.domain import Domain
from app.models.risk import Risk
from app.models.incident import Incident
from app.models.asset import Asset
from app.models.policy import Policy
from app.models.audit import InternalAudit, NonConformity, CorrectiveAction
from app.models.soa import SoAEntry
from app.models.supplier import Supplier
from app.models.audit_log import AuditLog
from app.models.asset_assignment import AssetAssignment
from app.models.management_review import ManagementReview
from app.models.capa import CapaRequest
from app.models.training import TrainingCourse, TrainingSession, TrainingRecord
from app.models.nis2 import Nis2EntityRegistration, Nis2IncidentNotification, Nis2SupplyChainAssessment, Nis2ContinuityPlan, Nis2ComplianceCheck
from app.models.processing import ProcessingActivity
from app.models.dpia import Dpia
from app.models.data_subject_request import DataSubjectRequest
from app.models.data_breach import DataBreach
from app.models.consent import ConsentRecord
from app.utils.decorators import permission_required
from app.utils.pdf import render_pdf
from sqlalchemy import func

reports_bp = Blueprint("reports", __name__)


def now():
    return datetime.now()


@reports_bp.route("/")
@login_required
def index():
    return render_template("reports/index.html")


@reports_bp.route("/controls-status")
@login_required
def controls_status():
    domains = Domain.query.all()
    data = {}
    for d in domains:
        total = Control.query.filter_by(domain_id=d.id).count()
        implemented = Control.query.filter_by(domain_id=d.id, implementation_status="implemented").count()
        in_progress = Control.query.filter_by(domain_id=d.id, implementation_status="in_progress").count()
        not_started = Control.query.filter_by(domain_id=d.id, implementation_status="not_started").count()
        na = Control.query.filter_by(domain_id=d.id, implementation_status="not_applicable").count()
        data[d.name] = {
            "total": total, "implemented": implemented,
            "in_progress": in_progress, "not_started": not_started,
            "na": na,
        }
    return render_template("reports/controls_status.html", data=data)


@reports_bp.route("/risk-summary")
@login_required
def risk_summary():
    risks = Risk.query.all()
    by_level = db.session.query(Risk.risk_level, func.count(Risk.id)).group_by(Risk.risk_level).all()
    by_status = db.session.query(Risk.status, func.count(Risk.id)).group_by(Risk.status).all()
    by_treatment = db.session.query(Risk.treatment_option, func.count(Risk.id)).group_by(Risk.treatment_option).all()
    return render_template("reports/risk_summary.html", risks=risks, by_level=by_level,
                           by_status=by_status, by_treatment=by_treatment)


@reports_bp.route("/incident-trends")
@login_required
def incident_trends():
    incidents = Incident.query.order_by(Incident.detected_at).all()
    by_severity = db.session.query(Incident.severity, func.count(Incident.id)).group_by(Incident.severity).all()
    by_status = db.session.query(Incident.status, func.count(Incident.id)).group_by(Incident.status).all()
    by_category = db.session.query(Incident.category, func.count(Incident.id)).group_by(Incident.category).all()
    return render_template("reports/incident_trends.html", incidents=incidents,
                           by_severity=by_severity, by_status=by_status, by_category=by_category)


@reports_bp.route("/audit-log")
@login_required
@permission_required("audit_log_view")
def view_audit_log():
    page = request.args.get("page", 1, type=int)
    per_page = 50
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template("reports/audit_log.html", logs=logs)


@reports_bp.route("/export/csv/<resource>")
@login_required
@permission_required("report_export")
def export_csv(resource):
    si = io.StringIO()
    writer = csv.writer(si)

    if resource == "controls":
        writer.writerow([_("Code"), _("Title"), _("Domain"), _("Status"), _("Owner"), _("Target Date")])
        for c in Control.query.order_by(Control.code).all():
            writer.writerow([c.code, c.title, c.domain.name if c.domain else "",
                           c.implementation_status, c.owner.first_name if c.owner else "",
                           c.target_date])
    elif resource == "risks":
        writer.writerow([_("Title"), _("Likelihood"), _("Impact"), _("Risk Level"), _("Treatment"), _("Status")])
        for r in Risk.query.all():
            writer.writerow([r.title, r.likelihood, r.impact, r.risk_level,
                           r.treatment_option, r.status])
    elif resource == "incidents":
        writer.writerow([_("Title"), _("Severity"), _("Status"), _("Category"), _("Reported"), _("Resolved")])
        for i in Incident.query.all():
            writer.writerow([i.title, i.severity, i.status, i.category,
                           i.detected_at, i.resolved_at])
    elif resource == "assets":
        writer.writerow([_("Name"), _("Type"), _("Classification"), _("Criticality"), _("Status")])
        for a in Asset.query.all():
            writer.writerow([a.name, a.asset_type, a.classification, a.criticality, a.status])
    elif resource == "soa":
        writer.writerow([_("Control"), _("Applicable"), _("Status"), _("Justification")])
        for e in SoAEntry.query.join(Control).order_by(Control.code).all():
            writer.writerow([e.control.code + " - " + e.control.title,
                           _("Yes") if e.applicable else _("No"),
                           e.implementation_status, e.justification])
    else:
        return _("Unknown resource"), 404

    output = si.getvalue()
    si.close()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={resource}_{datetime.now().strftime('%Y%m%d')}.csv"},
    )


@reports_bp.route("/export/pdf/controls")
@login_required
@permission_required("report_export")
def export_pdf_controls():
    domains = Domain.query.order_by(Domain.code).all()
    for d in domains:
        d.controls = Control.query.filter_by(domain_id=d.id).order_by(Control.code).all()
    pdf = render_pdf("reports/pdf/controls.html", domains=domains, title=_("Controls Status Report"),
                      now=now, filename="controls_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/risks")
@login_required
@permission_required("report_export")
def export_pdf_risks():
    risks = Risk.query.order_by(Risk.risk_level.desc()).all()
    stats = {
        "total": len(risks),
        "critical": sum(1 for r in risks if r.risk_level == "critical"),
        "high": sum(1 for r in risks if r.risk_level == "high"),
        "mitigated": sum(1 for r in risks if r.status == "closed"),
    }
    pdf = render_pdf("reports/pdf/risks.html", risks=risks, stats=stats,
                      title=_("Risk Assessment Report"), now=now, filename="risks_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/incidents")
@login_required
@permission_required("report_export")
def export_pdf_incidents():
    incidents = Incident.query.order_by(Incident.detected_at.desc()).all()
    stats = {
        "total": len(incidents),
        "open": sum(1 for i in incidents if i.status in ("reported", "investigating")),
        "critical": sum(1 for i in incidents if i.severity == "critical"),
        "this_month": sum(1 for i in incidents if i.detected_at and i.detected_at.month == datetime.now().month),
    }
    pdf = render_pdf("reports/pdf/incidents.html", incidents=incidents, stats=stats,
                      title=_("Incident Management Report"), now=now, filename="incidents_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/assets")
@login_required
@permission_required("report_export")
def export_pdf_assets():
    assets = Asset.query.all()
    stats = {
        "total": len(assets),
        "active": sum(1 for a in assets if a.status == "active"),
        "critical": sum(1 for a in assets if a.criticality == "critical"),
    }
    pdf = render_pdf("reports/pdf/assets.html", assets=assets, stats=stats,
                      title=_("Asset Inventory Report"), now=now, filename="assets_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/policies")
@login_required
@permission_required("report_export")
def export_pdf_policies():
    policies = Policy.query.order_by(Policy.status).all()
    stats = {
        "total": len(policies),
        "approved": sum(1 for p in policies if p.status == "published"),
        "review_needed": sum(1 for p in policies if p.review_date and p.review_date <= datetime.now().date()),
    }
    pdf = render_pdf("reports/pdf/policies.html", policies=policies, stats=stats,
                      title=_("Policy Management Report"), now=now, filename="policies_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/audits")
@login_required
@permission_required("report_export")
def export_pdf_audits():
    audits = InternalAudit.query.order_by(InternalAudit.audit_date.desc()).all()
    non_conformities = NonConformity.query.order_by(NonConformity.severity.desc()).all()
    corrective_actions = CorrectiveAction.query.order_by(CorrectiveAction.target_date).all()
    stats = {
        "total": len(audits),
        "completed": sum(1 for a in audits if a.status == "completed"),
        "nc_open": sum(1 for nc in non_conformities if nc.status in ("open", "in_progress")),
        "ca_open": sum(1 for ca in corrective_actions if ca.status in ("open", "in_progress")),
    }
    pdf = render_pdf("reports/pdf/audits.html", audits=audits, non_conformities=non_conformities,
                      corrective_actions=corrective_actions, stats=stats,
                      title=_("Audit & Compliance Report"), now=now, filename="audits_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/soa")
@login_required
@permission_required("report_export")
def export_pdf_soa():
    domains = Domain.query.order_by(Domain.code).all()
    domain_entries = {}
    total = SoAEntry.query.count()
    applicable = SoAEntry.query.filter_by(applicable=True).count()
    implemented = SoAEntry.query.filter_by(implementation_status="implemented").count()
    not_applicable = SoAEntry.query.filter_by(applicable=False).count()
    stats = {"total": total, "applicable": applicable, "implemented": implemented, "not_applicable": not_applicable}
    for d in domains:
        entries = SoAEntry.query.join(Control).filter(Control.domain_id == d.id).order_by(Control.code).all()
        domain_entries[d.id] = entries
    pdf = render_pdf("reports/pdf/soa.html", domains=domains, domain_entries=domain_entries,
                      stats=stats, title=_("Statement of Applicability Report"),
                      now=now, filename="soa_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/suppliers")
@login_required
@permission_required("report_export")
def export_pdf_suppliers():
    suppliers = Supplier.query.order_by(Supplier.criticality.desc()).all()
    stats = {
        "total": len(suppliers),
        "active": sum(1 for s in suppliers if s.status == "active"),
        "assessed": sum(1 for s in suppliers if s.assessment_status == "approved"),
        "nis2_scope": sum(1 for s in suppliers if s.nis2_in_scope),
    }
    pdf = render_pdf("reports/pdf/suppliers.html", suppliers=suppliers, stats=stats,
                      title=_("Supplier Security Report"), now=now, filename="suppliers_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/nis2")
@login_required
@permission_required("report_export")
def export_pdf_nis2():
    entity = Nis2EntityRegistration.query.first()
    compliance_checks = Nis2ComplianceCheck.query.all()
    notifications = Nis2IncidentNotification.query.all()
    supply_chain = Nis2SupplyChainAssessment.query.all()
    continuity_plans = Nis2ContinuityPlan.query.all()

    total_checks = len(compliance_checks)
    implemented = sum(1 for c in compliance_checks if c.status == "implemented")
    compliance_pct = round((implemented / total_checks * 100)) if total_checks else 0

    pdf = render_pdf("reports/pdf/nis2.html",
                      entity=entity,
                      compliance_checks=compliance_checks,
                      notifications=notifications,
                      supply_chain=supply_chain,
                      continuity_plans=continuity_plans,
                      compliance_pct=compliance_pct,
                      pending_notifications=sum(1 for n in notifications if not n.final_report_submitted_at),
                      active_continuity=sum(1 for p in continuity_plans if p.status == "active"),
                      critical_supply=sum(1 for a in supply_chain if a.supply_chain_risk_level == "critical"),
                      title=_("NIS2 Compliance Report"),
                      now=now, filename="nis2_compliance_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/gdpr")
@login_required
@permission_required("report_export")
def export_pdf_gdpr():
    activities = ProcessingActivity.query.order_by(ProcessingActivity.name).all()
    dpias = Dpia.query.order_by(Dpia.project_name).all()
    data_subject_requests = DataSubjectRequest.query.order_by(DataSubjectRequest.received_date.desc()).all()
    data_breaches = DataBreach.query.order_by(DataBreach.created_at.desc()).all()
    consents = ConsentRecord.query.order_by(ConsentRecord.granted_at.desc()).all()

    pdf = render_pdf("reports/pdf/gdpr.html",
                      activities=activities, dpias=dpias, dsars=data_subject_requests,
                      data_breaches=data_breaches, consents=consents,
                      title=_("GDPR Compliance Report"),
                      now=now, filename="gdpr_compliance_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/assignments")
@login_required
@permission_required("report_export")
def export_pdf_assignments():
    status_filter = request.args.get("status")
    query = AssetAssignment.query
    if status_filter:
        query = query.filter(AssetAssignment.status == status_filter)
    assignments = query.order_by(AssetAssignment.checkout_date.desc()).all()

    checked_out = sum(1 for a in assignments if a.status == "checked_out")
    returned = sum(1 for a in assignments if a.status == "returned")
    overdue = sum(1 for a in assignments if a.is_overdue)
    total = len(assignments)

    pdf = render_pdf("reports/pdf/assignments.html",
                      assignments=assignments, total=total,
                      checked_out=checked_out, returned=returned, overdue=overdue,
                      title=_("Asset Assignment Report"),
                      now=now, filename="asset_assignments_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/capas")
@login_required
@permission_required("report_export")
def export_pdf_capas():
    status = request.args.get("status")
    query = CapaRequest.query
    if status:
        query = query.filter_by(status=status)
    capas = query.order_by(CapaRequest.created_at.desc()).all()
    pdf = render_pdf("reports/pdf/capas.html",
                      capas=capas, now=now,
                      title=_("CAPA Report"),
                      filename="capa_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/training")
@login_required
@permission_required("report_export")
def export_pdf_training():
    courses = TrainingCourse.query.order_by(TrainingCourse.title).all()
    pdf = render_pdf("reports/pdf/training.html",
                      courses=courses, now=now,
                      title=_("Training Report"),
                      filename="training_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf


@reports_bp.route("/export/pdf/management-reviews")
@login_required
@permission_required("report_export")
def export_pdf_management_reviews():
    status = request.args.get("status")
    query = ManagementReview.query
    if status:
        query = query.filter_by(status=status)
    reviews = query.order_by(ManagementReview.review_date.desc()).all()
    pdf = render_pdf("reports/pdf/management_reviews.html",
                      reviews=reviews, now=now,
                      title=_("Management Review Report"),
                      filename="management_reviews_report")
    if pdf is None:
        return _("PDF generation failed"), 500
    return pdf
