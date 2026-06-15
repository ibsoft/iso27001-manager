from datetime import datetime
from app.extensions import db

REQUEST_TYPE_CHOICES = [
    "access", "rectification", "erasure", "portability",
    "restriction", "objection", "automated_decision",
]


class DataSubjectRequest(db.Model):
    __tablename__ = "data_subject_request"

    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(db.String(32), nullable=False)
    requester_name = db.Column(db.String(128), nullable=False)
    requester_email = db.Column(db.String(120), nullable=False)
    requester_phone = db.Column(db.String(32))
    requester_identity_verified = db.Column(db.Boolean, default=False)
    identity_verified_at = db.Column(db.DateTime)
    identity_verified_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    identity_verified_by = db.relationship("User", foreign_keys=[identity_verified_by_id])
    request_description = db.Column(db.Text)
    received_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deadline_date = db.Column(db.DateTime, nullable=False)
    response_date = db.Column(db.DateTime)
    response_summary = db.Column(db.Text)
    outcome = db.Column(db.String(32))
    denial_reason = db.Column(db.Text)
    extension_reason = db.Column(db.Text)
    extension_granted = db.Column(db.Boolean, default=False)
    extension_deadline = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    status = db.Column(db.String(16), default="open")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<DataSubjectRequest {self.request_type} - {self.requester_name}>"
