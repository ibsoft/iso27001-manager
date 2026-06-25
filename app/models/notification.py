from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    type = db.Column(db.String(32), default="info", comment="info|approval_requested|approved|rejected|comment")
    title = db.Column(db.String(256), nullable=False)
    message = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(512), nullable=True)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reference_type = db.Column(db.String(32), nullable=True, comment="approval_request|general_request|...")
    reference_id = db.Column(db.Integer, nullable=True)

    user = db.relationship("User", backref=db.backref("notifications", lazy="dynamic", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<Notification {self.id}: {self.title}>"
