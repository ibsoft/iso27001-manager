from datetime import datetime
from app.extensions import db


class GeneralRequest(db.Model):
    __tablename__ = "general_request"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(255), nullable=True)
    original_filename = db.Column(db.String(255), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(16), default="pending", comment="pending|approved|rejected|cancelled")
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship("User", backref=db.backref("general_requests", lazy="dynamic"))

    @property
    def file_size_display(self):
        if not self.file_size:
            return None
        kb = self.file_size / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        return f"{kb / 1024:.1f} MB"

    def __repr__(self):
        return f"<GeneralRequest {self.id}: {self.title}>"
