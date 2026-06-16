from datetime import datetime
from app.extensions import db


class Supplier(db.Model):
    __tablename__ = "supplier"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    contact_name = db.Column(db.String(128), nullable=True)
    contact_email = db.Column(db.String(128), nullable=True)
    contact_phone = db.Column(db.String(64), nullable=True)
    service_description = db.Column(db.Text, nullable=True)
    security_requirements = db.Column(db.Text, nullable=True)
    assessment_date = db.Column(db.Date, nullable=True)
    assessment_status = db.Column(db.String(32), default="pending",
                                  comment="pending|assessed|approved|rejected|review_required")
    assessment_notes = db.Column(db.Text, nullable=True)
    contract_start_date = db.Column(db.Date, nullable=True)
    contract_end_date = db.Column(db.Date, nullable=True)
    data_processing_agreement = db.Column(db.Boolean, default=False)
    criticality = db.Column(db.String(16), default="medium", comment="low|medium|high|critical")
    status = db.Column(db.String(16), default="active", comment="active|inactive|terminated")
    ict_service_type = db.Column(db.String(64), nullable=True, comment="cloud|saas|network|hardware|software|managed_service|consulting|other")
    security_certification = db.Column(db.String(256), nullable=True)
    dependency_tier = db.Column(db.String(8), default="3", comment="1|2|3")
    nis2_in_scope = db.Column(db.Boolean, default=False)
    last_supply_chain_review = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Supplier {self.name}>"
