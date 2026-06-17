import os
from datetime import datetime
from app.extensions import db


class FilledForm(db.Model):
    __tablename__ = "filled_form"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False, index=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(256), nullable=False)
    original_filename = db.Column(db.String(256), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="filled_forms", foreign_keys=[user_id])

    @property
    def file_extension(self):
        if self.original_filename:
            return os.path.splitext(self.original_filename)[1].lstrip(".").upper()
        return None

    @property
    def file_size_display(self):
        if self.file_size is None:
            return None
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        return f"{self.file_size / (1024 * 1024):.1f} MB"

    def __repr__(self):
        return f"<FilledForm {self.title} ({self.year})>"
