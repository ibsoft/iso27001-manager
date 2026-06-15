from datetime import datetime
from app.extensions import db


class SoAEntry(db.Model):
    __tablename__ = "soa_entry"

    id = db.Column(db.Integer, primary_key=True)
    control_id = db.Column(db.Integer, db.ForeignKey("control.id"), nullable=False)
    applicable = db.Column(db.Boolean, default=True)
    justification = db.Column(db.Text, nullable=True,
                              comment="Reason if not applicable or justification for control selection")
    implementation_status = db.Column(
        db.String(32), default="not_started",
        comment="not_started|in_progress|implemented|not_applicable",
    )
    selected_control_description = db.Column(db.Text, nullable=True)
    responsible_person_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    version = db.Column(db.String(16), default="1.0")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    control = db.relationship("Control", backref="soa_entries")
    responsible_person = db.relationship("User", backref="soa_responsibilities")

    def __repr__(self):
        return f"<SoAEntry {self.control_id}: applicable={self.applicable}>"
