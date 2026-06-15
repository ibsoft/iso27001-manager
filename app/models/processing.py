from datetime import datetime
from app.extensions import db

LEGAL_BASIS_CHOICES = [
    ("consent", "Consent (Art 6(1)(a))"),
    ("contract", "Contract (Art 6(1)(b))"),
    ("legal_obligation", "Legal Obligation (Art 6(1)(c))"),
    ("vital_interests", "Vital Interests (Art 6(1)(d))"),
    ("public_task", "Public Task (Art 6(1)(e))"),
    ("legitimate_interest", "Legitimate Interest (Art 6(1)(f))"),
]


class ProcessingActivity(db.Model):
    __tablename__ = "processing_activity"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    controller_name = db.Column(db.String(256), nullable=False)
    controller_contact = db.Column(db.String(256))
    controller_email = db.Column(db.String(120))
    representative = db.Column(db.String(256))
    dpo_name = db.Column(db.String(128))
    dpo_contact = db.Column(db.String(256))
    processing_purpose = db.Column(db.Text, nullable=False)
    legal_basis = db.Column(db.String(32), nullable=False)
    legal_basis_details = db.Column(db.Text)
    data_subject_categories = db.Column(db.Text, nullable=False)
    personal_data_categories = db.Column(db.Text, nullable=False)
    special_category_data = db.Column(db.Boolean, default=False)
    special_category_details = db.Column(db.Text)
    criminal_data = db.Column(db.Boolean, default=False)
    recipients = db.Column(db.Text)
    data_retention = db.Column(db.Text, nullable=False)
    tech_org_measures = db.Column(db.Text)
    cross_border_transfer = db.Column(db.Boolean, default=False)
    transfer_countries = db.Column(db.Text)
    transfer_safeguards = db.Column(db.Text)
    status = db.Column(db.String(16), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by = db.relationship("User", backref=db.backref("processing_activities", lazy="dynamic"))

    def __repr__(self):
        return f"<ProcessingActivity {self.name}>"
