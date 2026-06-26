from datetime import datetime
from app.extensions import db


class EmailAlert(db.Model):
    __tablename__ = "email_alert"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    event_type = db.Column(db.String(64), nullable=False, comment="audit_log|approval_requested|approved|rejected|failed_login|account_locked|user_created")
    recipient_type = db.Column(db.String(16), nullable=False, default="role", comment="role|user")
    recipient_id = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    created_by = db.relationship("User", backref="email_alerts", foreign_keys=[created_by_id])

    @property
    def recipient_display(self):
        if self.recipient_type == "role":
            from app.models.user import Role
            role = Role.query.get(self.recipient_id)
            return f"Role: {role.name}" if role else f"Role #{self.recipient_id}"
        else:
            from app.models.user import User
            user = User.query.get(self.recipient_id)
            return f"User: {user.username}" if user else f"User #{self.recipient_id}"
