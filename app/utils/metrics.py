"""Automated KPI calculation engine.

Maps formula strings stored on KpiDefinition to live database queries.
Each formula key is resolved to a function that returns a numeric value
by querying the relevant model's status/progress fields.
"""

from datetime import datetime, timedelta
from sqlalchemy import func


def recalculate_kpi(kpi):
    """Compute the current value for a KpiDefinition based on its formula.
    Creates and returns a new KpiMeasurement, or None if formula is unknown."""
    from app.extensions import db
    from app.models.metric import KpiMeasurement

    value = _resolve_formula(kpi.formula)
    if value is None:
        return None

    measurement = KpiMeasurement(
        kpi_id=kpi.id,
        value=round(value, 2),
        measured_at=datetime.utcnow(),
        notes=_formula_label(kpi.formula),
    )
    db.session.add(measurement)
    db.session.commit()
    return measurement


def _resolve_formula(formula):
    """Return a computed numeric value for the given formula string, or None."""
    if not formula:
        return None
    formula = formula.strip()

    # ── Controls Implementation ────────────────────────────
    if formula in ("implemented_controls/total_controls*100",):
        from app.models.control import Control
        total = Control.query.count()
        if total == 0:
            return 0.0
        implemented = Control.query.filter(
            Control.implementation_status == "implemented"
        ).count()
        return implemented / total * 100

    # ── Risk Treatment Progress ────────────────────────────
    if formula in ("treated_risks/total_risks*100",):
        from app.models.risk import Risk
        total = Risk.query.count()
        if total == 0:
            return 0.0
        treated = Risk.query.filter(
            Risk.treatment_option.isnot(None),
            Risk.status.in_(["residual_accepted", "closed"]),
        ).count()
        return treated / total * 100

    # ── Incident Resolution Time (avg hours) ───────────────
    if formula in ("avg_resolution_time",):
        from app.models.incident import Incident
        resolved = (
            Incident.query
            .filter(Incident.resolved_at.isnot(None), Incident.detected_at.isnot(None))
            .all()
        )
        if not resolved:
            return 0.0
        total_hours = sum(
            (r.resolved_at - r.detected_at).total_seconds() / 3600
            for r in resolved
        )
        return total_hours / len(resolved)

    # ── Audit Finding Closure ──────────────────────────────
    if formula in ("closed_findings/total_findings*100",):
        from app.models.audit import NonConformity
        total = NonConformity.query.count()
        if total == 0:
            return 0.0
        closed = NonConformity.query.filter(
            NonConformity.status.in_(["resolved", "closed"])
        ).count()
        return closed / total * 100

    # ── Policy Review Currency ─────────────────────────────
    if formula in ("reviewed_policies/total_policies*100",):
        from app.models.policy import Policy
        from sqlalchemy import func as _func
        total = Policy.query.count()
        if total == 0:
            return 0.0
        # Policies with a review_date in the future or no review_date needed
        reviewed = Policy.query.filter(
            Policy.review_date.isnot(None),
            Policy.review_date >= datetime.utcnow().date(),
        ).count()
        return reviewed / total * 100

    # ── NIS2 Compliance % ──────────────────────────────────
    if formula in ("nis2_compliance_percent",):
        from app.models.nis2 import Nis2ComplianceCheck
        total = Nis2ComplianceCheck.query.count()
        if total == 0:
            return 0.0
        implemented = Nis2ComplianceCheck.query.filter(
            Nis2ComplianceCheck.status == "implemented"
        ).count()
        return implemented / total * 100

    # ── Security Training Completion % ─────────────────────
    if formula in ("training_completion_percent",):
        from app.models.training import TrainingRecord
        total = TrainingRecord.query.count()
        if total == 0:
            return 0.0
        completed = TrainingRecord.query.filter(
            TrainingRecord.status == "completed"
        ).count()
        return completed / total * 100

    # ── Asset Inventory (active / total) % ─────────────────
    if formula in ("active_assets/total_assets*100",):
        from app.models.asset import Asset
        total = Asset.query.count()
        if total == 0:
            return 0.0
        active = Asset.query.filter(Asset.status == "active").count()
        return active / total * 100

    # ── Open Non-Conformities (count) ──────────────────────
    if formula in ("open_non_conformities",):
        from app.models.audit import NonConformity
        return NonConformity.query.filter(
            NonConformity.status.in_(["open", "in_progress"])
        ).count()

    # ── Overdue Risk Treatments (count) ────────────────────
    if formula in ("overdue_risk_treatments",):
        from app.models.risk import RiskTreatment
        return RiskTreatment.query.filter(
            RiskTreatment.status == "overdue"
        ).count()

    return None


def _formula_label(formula):
    """Human-readable label for a formula string."""
    labels = {
        "implemented_controls/total_controls*100": "Auto-calculated from controls implementation status",
        "treated_risks/total_risks*100": "Auto-calculated from risk treatment status",
        "avg_resolution_time": "Auto-calculated from incident resolution times",
        "closed_findings/total_findings*100": "Auto-calculated from non-conformity status",
        "reviewed_policies/total_policies*100": "Auto-calculated from policy review dates",
        "nis2_compliance_percent": "Auto-calculated from NIS2 compliance status",
        "training_completion_percent": "Auto-calculated from training records",
        "active_assets/total_assets*100": "Auto-calculated from asset status",
        "open_non_conformities": "Auto-calculated from non-conformity status",
        "overdue_risk_treatments": "Auto-calculated from risk treatment status",
    }
    return labels.get(formula, f"Auto-calculated from formula: {formula}")
