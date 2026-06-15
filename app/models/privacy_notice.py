from datetime import datetime
from app.extensions import db


class PrivacyNotice(db.Model):
    __tablename__ = "privacy_notice"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    version = db.Column(db.String(16), nullable=False, default="1.0")
    language = db.Column(db.String(8), default="en")
    content = db.Column(db.Text, nullable=False)
    effective_date = db.Column(db.Date)
    review_date = db.Column(db.Date)
    status = db.Column(db.String(16), default="draft")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by = db.relationship("User", backref=db.backref("privacy_notices", lazy="dynamic"))

    def __repr__(self):
        return f"<PrivacyNotice {self.title} v{self.version}>"
