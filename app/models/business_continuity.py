from datetime import datetime, date
from app.extensions import db


class BusinessImpactAnalysis(db.Model):
    __tablename__ = "business_impact_analysis"

    id = db.Column(db.Integer, primary_key=True)
    process_name = db.Column(db.String(256), nullable=False)
    process_owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    department = db.Column(db.String(128), nullable=True)
    description = db.Column(db.Text, nullable=True)
    dependencies = db.Column(db.Text, nullable=True)
    criticality = db.Column(db.String(16), default="medium", comment="low|medium|high|critical")
    impact_financial = db.Column(db.Text, nullable=True)
    impact_operational = db.Column(db.Text, nullable=True)
    impact_legal = db.Column(db.Text, nullable=True)
    impact_reputation = db.Column(db.Text, nullable=True)
    mtpd = db.Column(db.String(32), nullable=True)
    rto = db.Column(db.String(32), nullable=True)
    rpo = db.Column(db.String(32), nullable=True)
    minimum_resources = db.Column(db.Text, nullable=True)
    workaround = db.Column(db.Text, nullable=True)
    assessment_date = db.Column(db.Date, nullable=False, default=date.today)
    next_review_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(32), default="draft", comment="draft|reviewed|approved|archived")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    process_owner = db.relationship("User", backref="owned_bia_records", foreign_keys=[process_owner_id])
    plans = db.relationship("BusinessContinuityPlan", backref="bia", lazy="dynamic")

    def __repr__(self):
        return f"<BusinessImpactAnalysis {self.process_name}>"


class BusinessContinuityPlan(db.Model):
    __tablename__ = "business_continuity_plan"

    id = db.Column(db.Integer, primary_key=True)
    bia_id = db.Column(db.Integer, db.ForeignKey("business_impact_analysis.id"), nullable=True)
    title = db.Column(db.String(256), nullable=False)
    plan_type = db.Column(db.String(32), default="business_continuity", comment="business_continuity|disaster_recovery|crisis_management|combined")
    scope = db.Column(db.Text, nullable=True)
    objectives = db.Column(db.Text, nullable=True)
    activation_criteria = db.Column(db.Text, nullable=True)
    critical_processes = db.Column(db.Text, nullable=True)
    recovery_strategy = db.Column(db.Text, nullable=True)
    communication_plan = db.Column(db.Text, nullable=True)
    responsible_team = db.Column(db.String(256), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    rto = db.Column(db.String(32), nullable=True)
    rpo = db.Column(db.String(32), nullable=True)
    version = db.Column(db.String(16), default="1.0")
    lifecycle_stage = db.Column(db.String(32), default="draft", comment="draft|review|approved|active|test_due|improvement|retired")
    approved_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    review_date = db.Column(db.Date, nullable=True)
    next_test_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("User", backref="owned_bc_plans", foreign_keys=[owner_id])
    approved_by = db.relationship("User", backref="approved_bc_plans", foreign_keys=[approved_by_id])
    tests = db.relationship("BusinessContinuityTest", backref="plan", lazy="dynamic", cascade="all, delete-orphan")
    actions = db.relationship("BusinessContinuityAction", backref="plan", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def open_action_count(self):
        return self.actions.filter(BusinessContinuityAction.status.in_(["open", "in_progress"])).count()

    @property
    def completed_action_count(self):
        return self.actions.filter_by(status="completed").count()

    def __repr__(self):
        return f"<BusinessContinuityPlan {self.title}>"


class BusinessContinuityTest(db.Model):
    __tablename__ = "business_continuity_test"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("business_continuity_plan.id"), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    test_type = db.Column(db.String(32), default="tabletop", comment="tabletop|walkthrough|technical|full_interruption|drp")
    scheduled_date = db.Column(db.Date, nullable=True)
    performed_date = db.Column(db.Date, nullable=True)
    facilitator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    participants = db.Column(db.Text, nullable=True)
    objectives = db.Column(db.Text, nullable=True)
    scenario = db.Column(db.Text, nullable=True)
    results = db.Column(db.Text, nullable=True)
    issues_found = db.Column(db.Text, nullable=True)
    rto_met = db.Column(db.Boolean, default=False)
    rpo_met = db.Column(db.Boolean, default=False)
    outcome = db.Column(db.String(32), default="planned", comment="planned|passed|partial|failed|cancelled")
    next_test_date = db.Column(db.Date, nullable=True)
    evidence_reference = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    facilitator = db.relationship("User", backref="facilitated_bc_tests", foreign_keys=[facilitator_id])

    def __repr__(self):
        return f"<BusinessContinuityTest {self.title}>"


class BusinessContinuityAction(db.Model):
    __tablename__ = "business_continuity_action"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("business_continuity_plan.id"), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey("business_continuity_test.id"), nullable=True)
    description = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(32), default="open", comment="open|in_progress|completed|closed")
    completed_at = db.Column(db.DateTime, nullable=True)
    closure_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", backref="business_continuity_actions", foreign_keys=[owner_id])
    test = db.relationship("BusinessContinuityTest", backref="actions", foreign_keys=[test_id])

    def __repr__(self):
        return f"<BusinessContinuityAction {self.id}: {self.status}>"
