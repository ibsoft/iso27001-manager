from datetime import datetime
from app.extensions import db


class ISMSRole(db.Model):
    __tablename__ = "isms_role"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    parent_role_id = db.Column(db.Integer, db.ForeignKey("isms_role.id"), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_management = db.Column(db.Boolean, default=False, comment="Top management position")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = db.relationship("Department", backref=db.backref("isms_roles", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("isms_roles", lazy="dynamic"))
    children = db.relationship("ISMSRole", backref=db.backref("parent", remote_side=[id]), lazy="dynamic")

    def __repr__(self):
        return f"<ISMSRole {self.title}>"
