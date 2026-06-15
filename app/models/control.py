from datetime import datetime
from app.extensions import db


class Control(db.Model):
    __tablename__ = "control"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False, index=True, comment="e.g. 5.1, 5.2, ... 8.34")
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    detailed_description = db.Column(db.Text, nullable=True)
    purpose = db.Column(db.Text, nullable=True)
    guidance = db.Column(db.Text, nullable=True)
    domain_id = db.Column(db.Integer, db.ForeignKey("domain.id"), nullable=False)
    implementation_status = db.Column(
        db.String(32),
        default="not_started",
        comment="not_started|in_progress|implemented|not_applicable",
    )
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    review_date = db.Column(db.Date, nullable=True)
    evidence_notes = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_new_2022 = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("User", backref="owned_controls", foreign_keys=[owner_id])

    def __repr__(self):
        return f"<Control {self.code}: {self.title}>"

    @property
    def status_badge_class(self):
        mapping = {
            "not_started": "badge bg-secondary",
            "in_progress": "badge bg-warning text-dark",
            "implemented": "badge bg-success",
            "not_applicable": "badge bg-info",
        }
        return mapping.get(self.implementation_status, "badge bg-secondary")
