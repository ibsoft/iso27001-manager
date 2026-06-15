from datetime import datetime
from app.extensions import db


class InternalAudit(db.Model):
    __tablename__ = "internal_audit"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    lead_auditor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    audit_date = db.Column(db.Date, nullable=False)
    scope = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="planned",
                       comment="planned|in_progress|completed|reported")
    findings_summary = db.Column(db.Text, nullable=True)
    conclusion = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead_auditor = db.relationship("User", backref="lead_audits", foreign_keys=[lead_auditor_id])
    findings = db.relationship("AuditFinding", backref="audit", lazy="dynamic",
                               cascade="all, delete-orphan")
    non_conformities = db.relationship("NonConformity", backref="audit", lazy="dynamic",
                                       cascade="all, delete-orphan")

    def __repr__(self):
        return f"<InternalAudit {self.title}>"


class AuditFinding(db.Model):
    __tablename__ = "audit_finding"

    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey("internal_audit.id"), nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey("control.id"), nullable=True)
    finding_type = db.Column(db.String(32), nullable=False,
                             comment="nonconformity|observation|opportunity_for_improvement")
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(16), default="medium", comment="low|medium|high|critical")
    reference = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    control = db.relationship("Control", backref="audit_findings")
    corrective_action = db.relationship("CorrectiveAction", backref="finding", uselist=False,
                                        cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AuditFinding {self.finding_type}:{self.id}>"


class NonConformity(db.Model):
    __tablename__ = "non_conformity"

    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey("internal_audit.id"), nullable=True)
    finding_id = db.Column(db.Integer, db.ForeignKey("audit_finding.id"), nullable=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=False)
    root_cause = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(16), default="medium", comment="minor|major|critical")
    status = db.Column(db.String(32), default="open", comment="open|in_progress|resolved|closed")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    corrective_action = db.relationship("CorrectiveAction", backref="non_conformity", uselist=False)

    def __repr__(self):
        return f"<NonConformity {self.title}>"


class CorrectiveAction(db.Model):
    __tablename__ = "corrective_action"

    id = db.Column(db.Integer, primary_key=True)
    finding_id = db.Column(db.Integer, db.ForeignKey("audit_finding.id"), nullable=True)
    non_conformity_id = db.Column(db.Integer, db.ForeignKey("non_conformity.id"), nullable=True)
    description = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(32), default="open", comment="open|in_progress|completed|verified_closed")
    closure_evidence = db.Column(db.Text, nullable=True)
    effectiveness_review = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("User", backref="assigned_actions", foreign_keys=[owner_id])

    def __repr__(self):
        return f"<CorrectiveAction {self.id}: {self.status}>"
