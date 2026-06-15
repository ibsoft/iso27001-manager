from datetime import datetime
from app.extensions import db
from app.models.asset import Asset


class Risk(db.Model):
    __tablename__ = "risk"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    likelihood = db.Column(db.Integer, nullable=False, comment="1-5")
    impact = db.Column(db.Integer, nullable=False, comment="1-5")
    risk_level = db.Column(db.String(16), nullable=True, comment="low|medium|high|critical")
    treatment_option = db.Column(
        db.String(16), nullable=True,
        comment="accept|mitigate|transfer|avoid",
    )
    treatment_plan = db.Column(db.Text, nullable=True)
    residual_likelihood = db.Column(db.Integer, nullable=True)
    residual_impact = db.Column(db.Integer, nullable=True)
    residual_risk_level = db.Column(db.String(16), nullable=True)
    status = db.Column(db.String(32), default="identified", comment="identified|assessed|treatment_in_progress|residual_accepted|closed")
    target_date = db.Column(db.Date, nullable=True)
    closed_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("User", backref="assigned_risks", foreign_keys=[owner_id])
    treatments = db.relationship("RiskTreatment", backref="risk", lazy="dynamic", cascade="all, delete-orphan")
    controls = db.relationship("Control", secondary="risk_controls", lazy="subquery")

    def calculate_risk_level(self):
        score = self.likelihood * self.impact
        if score >= 20:
            self.risk_level = "critical"
        elif score >= 12:
            self.risk_level = "high"
        elif score >= 6:
            self.risk_level = "medium"
        else:
            self.risk_level = "low"

    def calculate_residual_risk(self):
        if self.residual_likelihood and self.residual_impact:
            score = self.residual_likelihood * self.residual_impact
            if score >= 20:
                self.residual_risk_level = "critical"
            elif score >= 12:
                self.residual_risk_level = "high"
            elif score >= 6:
                self.residual_risk_level = "medium"
            else:
                self.residual_risk_level = "low"

    def __repr__(self):
        return f"<Risk {self.title}>"


risk_controls = db.Table(
    "risk_controls",
    db.Column("risk_id", db.Integer, db.ForeignKey("risk.id"), primary_key=True),
    db.Column("control_id", db.Integer, db.ForeignKey("control.id"), primary_key=True),
)


class RiskTreatment(db.Model):
    __tablename__ = "risk_treatment"

    id = db.Column(db.Integer, primary_key=True)
    risk_id = db.Column(db.Integer, db.ForeignKey("risk.id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey("control.id"), nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(32), default="planned", comment="planned|in_progress|completed|overdue")
    completed_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    control = db.relationship("Control", backref="risk_treatments")

    def __repr__(self):
        return f"<RiskTreatment {self.id} for Risk {self.risk_id}>"
