from datetime import datetime
from app.extensions import db


class Dpia(db.Model):
    __tablename__ = "dpia"

    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(256), nullable=False)
    project_description = db.Column(db.Text, nullable=False)
    processing_description = db.Column(db.Text, nullable=False)
    necessity_assessment = db.Column(db.Text)
    proportionality_assessment = db.Column(db.Text)
    data_subject_categories = db.Column(db.Text)
    personal_data_categories = db.Column(db.Text)
    special_category_data = db.Column(db.Boolean, default=False)
    risks_to_rights = db.Column(db.Text)
    mitigation_measures = db.Column(db.Text)
    residual_risk_level = db.Column(db.String(16), default="medium")
    dpo_review = db.Column(db.Text)
    dpo_reviewed_at = db.Column(db.DateTime)
    dpo_reviewed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    dpo_reviewed_by = db.relationship("User", foreign_keys=[dpo_reviewed_by_id])
    status = db.Column(db.String(16), default="draft")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<Dpia {self.project_name}>"
