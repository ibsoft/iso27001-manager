from datetime import datetime
from app.extensions import db


class AssetAssignment(db.Model):
    __tablename__ = "asset_assignment"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    assignee_name = db.Column(db.String(256), nullable=True)
    assignee_type = db.Column(db.String(16), default="internal")
    department = db.Column(db.String(128), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(64), nullable=True)
    checkout_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expected_return_date = db.Column(db.DateTime, nullable=True)
    actual_return_date = db.Column(db.DateTime, nullable=True)
    purpose = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    condition_notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="checked_out", index=True)
    signature_data = db.Column(db.Text, nullable=True)
    signed_at = db.Column(db.DateTime, nullable=True)
    checkin_signature_data = db.Column(db.Text, nullable=True)
    checkin_signed_at = db.Column(db.DateTime, nullable=True)
    released_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    released_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset = db.relationship("Asset", backref=db.backref("assignments", lazy="dynamic", order_by="AssetAssignment.checkout_date.desc()"))
    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("asset_assignments", lazy="dynamic"))
    released_by = db.relationship("User", foreign_keys=[released_by_id], backref=db.backref("released_assignments", lazy="dynamic"))

    @property
    def is_overdue(self):
        if self.status == "returned":
            return False
        if self.expected_return_date and self.expected_return_date < datetime.utcnow():
            return True
        return False

    @property
    def duration_days(self):
        end = self.actual_return_date or datetime.utcnow()
        delta = end - self.checkout_date
        return max(0, delta.days)

    def __repr__(self):
        return f"<AssetAssignment {self.id}: {self.asset.name if self.asset else '?'} → {self.assignee_name or self.user}>"
