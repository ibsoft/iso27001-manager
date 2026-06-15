from datetime import datetime
from app.extensions import db


class Asset(db.Model):
    __tablename__ = "asset"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    serial_number = db.Column(db.String(128), nullable=True, comment="Manufacturer serial number or asset tag")
    description = db.Column(db.Text, nullable=True)
    asset_type = db.Column(db.String(64), nullable=True, comment="hardware|software|data|personnel|facility|other")
    classification = db.Column(
        db.String(32), default="internal",
        comment="public|internal|confidential|restricted",
    )
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    location = db.Column(db.String(256), nullable=True)
    status = db.Column(db.String(32), default="active", comment="active|inactive|disposed")
    criticality = db.Column(db.String(16), default="medium", comment="low|medium|high|critical")
    retention_period = db.Column(db.String(64), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("User", backref="owned_assets", foreign_keys=[owner_id])
    risks = db.relationship("Risk", backref="asset", lazy="dynamic")

    def __repr__(self):
        return f"<Asset {self.name}>"
