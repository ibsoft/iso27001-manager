from datetime import datetime
from app.extensions import db


class ApprovalRequest(db.Model):
    __tablename__ = "approval_request"

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    target_type = db.Column(db.String(64), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(16), default="pending", comment="pending|approved|rejected|cancelled")
    reason = db.Column(db.Text, nullable=True, comment="Approver's comment or rejection reason")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)
    responded_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    requester = db.relationship("User", backref=db.backref("approval_requests", lazy="dynamic"),
                                foreign_keys=[requester_id])
    approver = db.relationship("User", backref=db.backref("approvals_pending", lazy="dynamic"),
                               foreign_keys=[approver_id])
    responded_by = db.relationship("User", backref=db.backref("approvals_responded", lazy="dynamic"),
                                   foreign_keys=[responded_by_id])

    _target_models = {}

    @classmethod
    def register_target_model(cls, target_type, model_class):
        cls._target_models[target_type] = model_class

    @property
    def target(self):
        model = self._target_models.get(self.target_type)
        if model:
            return model.query.get(self.target_id)
        return None

    @property
    def target_title(self):
        obj = self.target
        if obj is None:
            return f"{self.target_type}#{self.target_id}"
        if hasattr(obj, "title"):
            return obj.title
        if hasattr(obj, "name"):
            return obj.name
        return str(obj)

    STATUS_TRANSITIONS = {
        "policy": {"approved": "approved", "rejected": "draft"},
        "capa": {"approved": "under_review", "rejected": "open"},
        "supplier": {"approved": "approved", "rejected": "rejected"},
        "dpia": {"approved": "approved", "rejected": "draft"},
        "business_impact_analysis": {"approved": "approved", "rejected": "draft"},
        "business_continuity_plan": {"approved": "approved", "rejected": "draft"},
        "general_request": {"approved": "approved", "rejected": "rejected"},
    }

    def apply_transition(self):
        transitions = self.STATUS_TRANSITIONS.get(self.target_type)
        if transitions and self.status in transitions:
            new_status = transitions[self.status]
            obj = self.target
            if obj is None:
                return
            if hasattr(obj, "status"):
                obj.status = new_status
            elif hasattr(obj, "assessment_status"):
                obj.assessment_status = new_status

    @property
    def status_class(self):
        return {
            "pending": "badge bg-warning text-dark",
            "approved": "badge bg-success",
            "rejected": "badge bg-danger",
            "cancelled": "badge bg-secondary",
        }.get(self.status, "badge bg-secondary")

    def __repr__(self):
        return f"<ApprovalRequest {self.id}: {self.target_type}#{self.target_id} -> {self.status}>"
