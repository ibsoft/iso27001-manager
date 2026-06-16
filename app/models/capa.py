from datetime import datetime
from app.extensions import db


class CapaRequest(db.Model):
    __tablename__ = "capa_request"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=False)
    source_type = db.Column(db.String(32), default="internal",
                            comment="audit|incident|complaint|supplier|internal|regulatory|other")
    source_reference = db.Column(db.String(128), nullable=True,
                                 comment="Reference to source document/ID")
    severity = db.Column(db.String(16), default="medium",
                         comment="minor|major|critical")
    status = db.Column(db.String(32), default="open",
                       comment="open|under_review|action_planned|in_progress|verified|closed")
    root_cause = db.Column(db.Text, nullable=True)
    root_cause_category = db.Column(db.String(64), nullable=True,
                                    comment="People|Process|Technology|External|Other")
    proposed_action = db.Column(db.Text, nullable=True)
    action_owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.DateTime, nullable=True)
    effectiveness_review = db.Column(db.Text, nullable=True)
    effectiveness_rating = db.Column(db.String(16), nullable=True,
                                     comment="effective|partially_effective|ineffective")
    closure_notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    action_owner = db.relationship("User", backref="capa_actions",
                                   foreign_keys=[action_owner_id])
    created_by = db.relationship("User", backref="created_capas",
                                 foreign_keys=[created_by_id])
    assigned_to = db.relationship("User", backref="assigned_capas",
                                  foreign_keys=[assigned_to_id])

    @property
    def severity_class(self):
        return {"minor": "secondary", "major": "warning", "critical": "danger"}.get(self.severity, "primary")

    @property
    def status_class(self):
        return {
            "open": "danger", "under_review": "info", "action_planned": "primary",
            "in_progress": "warning", "verified": "success", "closed": "secondary",
        }.get(self.status, "secondary")

    def __repr__(self):
        return f"<CapaRequest {self.id}: {self.title}>"
