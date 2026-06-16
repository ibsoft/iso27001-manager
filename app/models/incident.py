from datetime import datetime
from app.extensions import db


class Incident(db.Model):
    __tablename__ = "incident"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(16), default="medium", comment="low|medium|high|critical")
    category = db.Column(db.String(64), nullable=True, comment="malware|unauthorized_access|data_breach|phishing|physical|other")
    status = db.Column(db.String(32), default="reported", comment="reported|investigating|contained|resolved|closed")
    reported_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    contained_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    root_cause = db.Column(db.Text, nullable=True)
    impact_description = db.Column(db.Text, nullable=True)
    lessons_learned = db.Column(db.Text, nullable=True)
    nis2_reportable = db.Column(db.Boolean, default=False, comment="Whether this incident is NIS2-reportable")
    nis2_early_warning_deadline = db.Column(db.DateTime, nullable=True)
    nis2_early_warning_submitted_at = db.Column(db.DateTime, nullable=True)
    nis2_notification_deadline = db.Column(db.DateTime, nullable=True)
    nis2_notification_submitted_at = db.Column(db.DateTime, nullable=True)
    nis2_final_report_deadline = db.Column(db.DateTime, nullable=True)
    nis2_final_report_submitted_at = db.Column(db.DateTime, nullable=True)
    nis2_csirt_reference = db.Column(db.String(128), nullable=True)
    nis2_status = db.Column(db.String(32), default="not_applicable",
                            comment="not_applicable|pending_early_warning|pending_notification|pending_final_report|completed")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reported_by = db.relationship("User", backref="reported_incidents", foreign_keys=[reported_by_id])
    assigned_to = db.relationship("User", backref="assigned_incidents", foreign_keys=[assigned_to_id])

    def __repr__(self):
        return f"<Incident {self.title}>"
