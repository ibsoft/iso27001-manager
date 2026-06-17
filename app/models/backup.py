from datetime import datetime
from app.extensions import db


class BackupRecord(db.Model):
    __tablename__ = "backup_record"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer, nullable=True, comment="Size in bytes")
    db_type = db.Column(db.String(16), nullable=True, comment="postgresql|sqlite")
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship("User", backref="backups", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<BackupRecord {self.filename}>"
