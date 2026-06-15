from datetime import datetime
from app.extensions import db


class DataControllerProcessor(db.Model):
    __tablename__ = "data_controller_processor"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False)
    contact_person = db.Column(db.String(128))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(32))
    address = db.Column(db.Text)
    representative_name = db.Column(db.String(128))
    representative_contact = db.Column(db.Text)
    dpo_name = db.Column(db.String(128))
    dpo_email = db.Column(db.String(120))
    registration_number = db.Column(db.String(64))
    country = db.Column(db.String(64))
    status = db.Column(db.String(16), default="active")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by = db.relationship("User", backref=db.backref("data_controllers", lazy="dynamic"))

    def __repr__(self):
        return f"<DataControllerProcessor {self.name} ({self.role})>"
