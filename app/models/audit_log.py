from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False, comment="CREATE|READ|UPDATE|DELETE|LOGIN|LOGOUT|FAILED_LOGIN")
    resource_type = db.Column(db.String(64), nullable=False)
    resource_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", backref="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.resource_type}#{self.resource_id}>"
