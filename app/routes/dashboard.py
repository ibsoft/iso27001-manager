from flask import Blueprint, render_template
from flask_login import login_required
from flask_babel import gettext as _
from app.extensions import db
from app.models.control import Control
from app.models.risk import Risk
from app.models.incident import Incident
from app.models.policy import Policy
from app.models.audit import NonConformity
from app.models.processing import ProcessingActivity
from app.models.dpia import Dpia
from app.models.data_subject_request import DataSubjectRequest
from app.models.consent import ConsentRecord
from app.models.data_breach import DataBreach
from app.models.nis2 import (
    Nis2ComplianceCheck, Nis2IncidentNotification,
    Nis2SupplyChainAssessment, Nis2ContinuityPlan,
    Nis2EntityRegistration,
)
from app.models.management_review import ManagementReview
from app.models.capa import CapaRequest
from datetime import datetime, date
from sqlalchemy import func

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    now = datetime.utcnow()

    # ISMS
    total_controls = Control.query.count()
    implemented_controls = Control.query.filter_by(implementation_status="implemented").count()
    in_progress_controls = Control.query.filter_by(implementation_status="in_progress").count()
    not_started_controls = Control.query.filter_by(implementation_status="not_started").count()

    total_risks = Risk.query.count()
    critical_risks = Risk.query.filter_by(risk_level="critical").count()
    high_risks = Risk.query.filter_by(risk_level="high").count()

    total_incidents = Incident.query.count()
    open_incidents = Incident.query.filter(
        Incident.status.in_(["reported", "investigating", "contained"])
    ).count()

    total_policies = Policy.query.count()
    policies_needing_review = Policy.query.filter(
        Policy.review_date.isnot(None),
        Policy.review_date < func.current_date()
    ).count()

    open_non_conformities = NonConformity.query.filter(
        NonConformity.status.in_(["open", "in_progress"])
    ).count()

    recent_incidents = Incident.query.order_by(Incident.created_at.desc()).limit(5).all()

    # Training
    from app.models.training import TrainingCourse, TrainingSession, TrainingRecord as TrainingRec
    total_courses = TrainingCourse.query.filter_by(status="active").count()
    upcoming_sessions = TrainingSession.query.filter(
        TrainingSession.session_date >= date.today(),
        TrainingSession.status == "scheduled",
    ).count()
    completed_training = TrainingRec.query.filter_by(status="completed").count()

    # Management Reviews
    from app.models.management_review import ReviewActionItem
    total_reviews = ManagementReview.query.count()
    overdue_reviews = ManagementReview.query.filter(
        ManagementReview.status.in_(["planned", "in_progress"]),
        ManagementReview.review_date < date.today(),
    ).count()
    open_review_actions = ReviewActionItem.query.filter(
        ReviewActionItem.status.in_(["open", "in_progress"])
    ).count()

    # CAPA
    open_capas = CapaRequest.query.filter(
        CapaRequest.status.in_(["open", "under_review", "action_planned", "in_progress"])
    ).count()
    critical_capas = CapaRequest.query.filter_by(severity="critical").filter(
        CapaRequest.status.in_(["open", "under_review", "action_planned", "in_progress"])
    ).count()

    # GDPR
    total_activities = ProcessingActivity.query.count()
    active_activities = ProcessingActivity.query.filter_by(status="active").count()
    total_dpias = Dpia.query.count()
    approved_dpias = Dpia.query.filter_by(status="approved").count()
    open_dsars = DataSubjectRequest.query.filter(
        DataSubjectRequest.status.in_(["open", "in_progress", "awaiting_info"])
    ).count()
    overdue_dsars = DataSubjectRequest.query.filter(
        DataSubjectRequest.deadline_date < now,
        DataSubjectRequest.status.in_(["open", "in_progress", "awaiting_info"]),
    ).count()
    active_consents = ConsentRecord.query.filter_by(granted=True).filter(
        ConsentRecord.withdrawn_at.is_(None)
    ).count()
    data_breaches = DataBreach.query.count()
    notified_sa = DataBreach.query.filter_by(notified_supervisory_authority=True).count()

    # NIS2
    entity = Nis2EntityRegistration.query.first()
    total_compliance = Nis2ComplianceCheck.query.count()
    implemented_compliance = Nis2ComplianceCheck.query.filter_by(status="implemented").count()
    compliance_pct = round((implemented_compliance / total_compliance * 100)) if total_compliance else 0
    pending_notifications = Nis2IncidentNotification.query.filter(
        Nis2IncidentNotification.notification_status.notin_(["completed", "final_report_submitted"])
    ).count()
    active_continuity = Nis2ContinuityPlan.query.filter_by(status="active").count()
    critical_supply_chain = Nis2SupplyChainAssessment.query.filter_by(supply_chain_risk_level="critical").count()

    context = {
        "total_controls": total_controls,
        "implemented_controls": implemented_controls,
        "in_progress_controls": in_progress_controls,
        "not_started_controls": not_started_controls,
        "implementation_pct": round((implemented_controls / total_controls * 100)) if total_controls else 0,
        "total_risks": total_risks,
        "critical_risks": critical_risks,
        "high_risks": high_risks,
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "total_policies": total_policies,
        "policies_needing_review": policies_needing_review,
        "open_non_conformities": open_non_conformities,
        "recent_incidents": recent_incidents,
        "total_activities": total_activities,
        "active_activities": active_activities,
        "total_dpias": total_dpias,
        "approved_dpias": approved_dpias,
        "open_dsars": open_dsars,
        "overdue_dsars": overdue_dsars,
        "active_consents": active_consents,
        "data_breaches": data_breaches,
        "notified_sa": notified_sa,
        "entity": entity,
        "total_compliance": total_compliance,
        "implemented_compliance": implemented_compliance,
        "compliance_pct": compliance_pct,
        "pending_notifications": pending_notifications,
        "active_continuity": active_continuity,
        "critical_supply_chain": critical_supply_chain,
        "total_reviews": total_reviews,
        "overdue_reviews": overdue_reviews,
        "open_review_actions": open_review_actions,
        "open_capas": open_capas,
        "critical_capas": critical_capas,
        "total_courses": total_courses,
        "upcoming_sessions": upcoming_sessions,
        "completed_training": completed_training,
    }

    return render_template("dashboard/index.html", **context)
