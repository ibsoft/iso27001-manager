from datetime import datetime
from app.extensions import db


class ConsentRecord(db.Model):
    __tablename__ = "consent_record"

    id = db.Column(db.Integer, primary_key=True)
    data_subject_identifier = db.Column(db.String(256), nullable=False)
    data_subject_email = db.Column(db.String(120))
    processing_purpose = db.Column(db.String(256), nullable=False)
    consent_given_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    consent_source = db.Column(db.String(64))
    consent_proof = db.Column(db.Text)
    consent_version = db.Column(db.String(16))
    granted = db.Column(db.Boolean, default=True)
    withdrawn_at = db.Column(db.DateTime)
    withdrawn_source = db.Column(db.String(64))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by = db.relationship("User", backref=db.backref("consent_records", lazy="dynamic"))

    def __repr__(self):
        return f"<ConsentRecord {self.data_subject_identifier} - {self.processing_purpose}>"
