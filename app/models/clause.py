from datetime import datetime
from app.extensions import db


class Clause(db.Model):
    __tablename__ = "clause"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False, comment="4-10")
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_mandatory = db.Column(db.Boolean, default=True)
    implementation_notes = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Clause {self.number}: {self.title}>"
