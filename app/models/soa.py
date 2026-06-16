from datetime import datetime
from app.extensions import db


class SoAEntry(db.Model):
    __tablename__ = "soa_entry"

    id = db.Column(db.Integer, primary_key=True)
    control_id = db.Column(db.Integer, db.ForeignKey("control.id"), nullable=False)
    applicable = db.Column(db.Boolean, default=True)
    justification = db.Column(db.Text, nullable=True,
                              comment="Reason if not applicable or justification for control selection")
    justification_el = db.Column(db.Text, nullable=True)
    implementation_status = db.Column(
        db.String(32), default="not_started",
        comment="not_started|in_progress|implemented|not_applicable",
    )
    selected_control_description = db.Column(db.Text, nullable=True)
    selected_control_description_el = db.Column(db.Text, nullable=True)
    responsible_person_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    version = db.Column(db.String(16), default="1.0")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    control = db.relationship("Control", backref="soa_entries")
    responsible_person = db.relationship("User", backref="soa_responsibilities")

    def localized_justification(self, lang="en"):
        return self.justification_el if lang == "el" and self.justification_el else self.justification

    def localized_description(self, lang="en"):
        return self.selected_control_description_el if lang == "el" and self.selected_control_description_el else self.selected_control_description

    def __repr__(self):
        return f"<SoAEntry {self.control_id}: applicable={self.applicable}>"
