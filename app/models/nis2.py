from datetime import datetime
from app.extensions import db


class Nis2EntityRegistration(db.Model):
    __tablename__ = "nis2_entity_registration"

    id = db.Column(db.Integer, primary_key=True)
    entity_name = db.Column(db.String(256), nullable=False, default="")
    sector = db.Column(db.String(64), nullable=True, comment="energy|transport|banking|health|digital_infrastructure|ict_service|water|waste|manufacturing|food|postal|other")
    sub_sector = db.Column(db.String(128), nullable=True)
    entity_type = db.Column(db.String(32), default="essential", comment="essential|important")
    registration_number = db.Column(db.String(128), nullable=True)
    competent_authority = db.Column(db.String(256), nullable=True)
    csirt_name = db.Column(db.String(256), nullable=True)
    csirt_email = db.Column(db.String(128), nullable=True)
    csirt_phone = db.Column(db.String(64), nullable=True)
    headquarters_address = db.Column(db.Text, nullable=True)
    operates_in_eu = db.Column(db.Boolean, default=True)
    eu_member_states = db.Column(db.Text, nullable=True)
    employee_count = db.Column(db.Integer, nullable=True)
    annual_turnover = db.Column(db.String(64), nullable=True)
    registration_date = db.Column(db.Date, nullable=True)
    last_review_date = db.Column(db.Date, nullable=True)
    next_review_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(16), default="active", comment="active|inactive|suspended")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Nis2EntityRegistration {self.entity_name}>"


class Nis2IncidentNotification(db.Model):
    __tablename__ = "nis2_incident_notification"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), nullable=True)
    incident_title = db.Column(db.String(256), nullable=False)
    reportable_criteria = db.Column(db.Text, nullable=True)
    service_disruption = db.Column(db.Boolean, default=False)
    data_impact = db.Column(db.Boolean, default=False)
    financial_loss = db.Column(db.Boolean, default=False)
    affected_users_count = db.Column(db.Integer, nullable=True)
    incident_detected_at = db.Column(db.DateTime, nullable=True)
    early_warning_deadline = db.Column(db.DateTime, nullable=True)
    early_warning_submitted_at = db.Column(db.DateTime, nullable=True)
    early_warning_details = db.Column(db.Text, nullable=True)
    notification_deadline = db.Column(db.DateTime, nullable=True)
    notification_submitted_at = db.Column(db.DateTime, nullable=True)
    notification_details = db.Column(db.Text, nullable=True)
    final_report_deadline = db.Column(db.DateTime, nullable=True)
    final_report_submitted_at = db.Column(db.DateTime, nullable=True)
    final_report_details = db.Column(db.Text, nullable=True)
    csirt_reference = db.Column(db.String(128), nullable=True)
    csirt_name = db.Column(db.String(256), nullable=True)
    notification_status = db.Column(db.String(32), default="pending", comment="pending|early_warning_due|early_warning_submitted|notification_due|notification_submitted|final_report_due|final_report_submitted|completed")
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    incident = db.relationship("Incident", backref="nis2_notifications", foreign_keys=[incident_id])
    submitted_by = db.relationship("User", backref="nis2_notifications", foreign_keys=[submitted_by_id])

    def __repr__(self):
        return f"<Nis2IncidentNotification {self.incident_title}>"


class Nis2SupplyChainAssessment(db.Model):
    __tablename__ = "nis2_supply_chain_assessment"

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"), nullable=True)
    supplier_name = db.Column(db.String(256), nullable=False)
    ict_service_type = db.Column(db.String(64), nullable=True, comment="cloud|saas|network|hardware|software|managed_service|consulting|other")
    service_criticality = db.Column(db.String(16), default="medium", comment="low|medium|high|critical")
    dependency_tier = db.Column(db.String(8), default="3", comment="1|2|3")
    security_certifications = db.Column(db.String(256), nullable=True)
    nis2_in_scope = db.Column(db.Boolean, default=False)
    supply_chain_risk_level = db.Column(db.String(16), default="medium", comment="low|medium|high|critical")
    last_assessment_date = db.Column(db.Date, nullable=True)
    next_assessment_date = db.Column(db.Date, nullable=True)
    assessment_findings = db.Column(db.Text, nullable=True)
    mitigation_actions = db.Column(db.Text, nullable=True)
    subcontractors_known = db.Column(db.Boolean, default=False)
    subcontractor_details = db.Column(db.Text, nullable=True)
    sla_in_place = db.Column(db.Boolean, default=False)
    incident_reporting_defined = db.Column(db.Boolean, default=False)
    right_to_audit = db.Column(db.Boolean, default=False)
    data_processing_agreement = db.Column(db.Boolean, default=False)
    termination_notice_days = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(16), default="pending", comment="pending|assessed|approved|review_required|rejected")
    assessed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = db.relationship("Supplier", backref="nis2_assessments", foreign_keys=[supplier_id])
    assessed_by = db.relationship("User", backref="nis2_assessments", foreign_keys=[assessed_by_id])

    def __repr__(self):
        return f"<Nis2SupplyChainAssessment {self.supplier_name}>"


class Nis2ContinuityPlan(db.Model):
    __tablename__ = "nis2_continuity_plan"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    plan_type = db.Column(db.String(32), default="business_continuity", comment="business_continuity|disaster_recovery|crisis_management|combined")
    scope = db.Column(db.Text, nullable=True)
    objectives = db.Column(db.Text, nullable=True)
    critical_services = db.Column(db.Text, nullable=True)
    rto = db.Column(db.String(32), nullable=True)
    rpo = db.Column(db.String(32), nullable=True)
    recovery_procedures = db.Column(db.Text, nullable=True)
    responsible_team = db.Column(db.String(256), nullable=True)
    testing_frequency = db.Column(db.String(32), default="annual", comment="monthly|quarterly|semi_annual|annual|biannual")
    last_test_date = db.Column(db.Date, nullable=True)
    last_test_result = db.Column(db.Text, nullable=True)
    next_test_date = db.Column(db.Date, nullable=True)
    maintenance_schedule = db.Column(db.Text, nullable=True)
    version = db.Column(db.String(16), default="1.0")
    status = db.Column(db.String(16), default="draft", comment="draft|approved|active|review_required|archived")
    approved_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approved_by = db.relationship("User", backref="nis2_continuity_plans", foreign_keys=[approved_by_id])

    def __repr__(self):
        return f"<Nis2ContinuityPlan {self.title}>"


class Nis2ComplianceCheck(db.Model):
    __tablename__ = "nis2_compliance_check"

    id = db.Column(db.Integer, primary_key=True)
    measure = db.Column(db.String(64), nullable=False, comment="risk_analysis|incident_handling|business_continuity|supply_chain_security|network_security|access_control|cryptography|hr_security|mfa|security_training")
    measure_display = db.Column(db.String(256), nullable=False)
    article_ref = db.Column(db.String(16), nullable=True)
    status = db.Column(db.String(16), default="not_started", comment="not_started|in_progress|implemented|not_applicable|review_required")
    implementation_details = db.Column(db.Text, nullable=True)
    evidence_notes = db.Column(db.Text, nullable=True)
    control_references = db.Column(db.String(256), nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    completion_date = db.Column(db.Date, nullable=True)
    review_date = db.Column(db.Date, nullable=True)
    responsible_person_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    responsible_person = db.relationship("User", backref="nis2_compliance_checks", foreign_keys=[responsible_person_id])

    def __repr__(self):
        return f"<Nis2ComplianceCheck {self.measure}>"
