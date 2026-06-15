from datetime import datetime
from app.extensions import db


class Domain(db.Model):
    __tablename__ = "domain"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Integer, unique=True, nullable=False, comment="5=Organizational, 6=People, 7=Physical, 8=Technological")
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    controls = db.relationship("Control", backref="domain", lazy="dynamic",
                               order_by="Control.code")

    def __repr__(self):
        return f"<Domain {self.code}: {self.name}>"
