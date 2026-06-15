from datetime import datetime
from app.extensions import db


class DataBreach(db.Model):
    __tablename__ = "data_breach"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), unique=True, nullable=False)
    incident = db.relationship("Incident", backref=db.backref("data_breach", uselist=False))
    breach_type = db.Column(db.String(32))
    personal_data_breach = db.Column(db.Boolean, default=True)
    notified_supervisory_authority = db.Column(db.Boolean, default=False)
    sa_notification_date = db.Column(db.DateTime)
    sa_reference = db.Column(db.String(64))
    notified_data_subjects = db.Column(db.Boolean, default=False)
    ds_notification_date = db.Column(db.DateTime)
    ds_affected_count = db.Column(db.Integer)
    records_affected_count = db.Column(db.Integer)
    likelihood_of_risk = db.Column(db.Text)
    mitigation_measures = db.Column(db.Text)
    notification_delay_reason = db.Column(db.Text)
    notification_delay_justified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DataBreach for incident {self.incident_id}>"
