import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, Response, send_file
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
from app.models.audit_log import AuditLog
from app.utils.decorators import permission_required
from sqlalchemy import func

reports_bp = Blueprint("reports", __name__)


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
