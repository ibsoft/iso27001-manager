import os
from datetime import datetime
from app.extensions import db


class Policy(db.Model):
    __tablename__ = "policy"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(64), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    current_version = db.Column(db.String(16), default="1.0")
    status = db.Column(db.String(32), default="draft",
                       comment="draft|reviewed|approved|published|retired")
    effective_date = db.Column(db.Date, nullable=True)
    review_date = db.Column(db.Date, nullable=True)
    content = db.Column(db.Text, nullable=True)
    is_document = db.Column(db.Boolean, default=False, comment="True=uploaded file, False=WYSIWYG content")
    filename = db.Column(db.String(256), nullable=True, comment="Current uploaded file path")
    original_filename = db.Column(db.String(256), nullable=True, comment="Original uploaded file name")
    file_size = db.Column(db.Integer, nullable=True, comment="File size in bytes")
    is_template = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("User", backref="owned_policies", foreign_keys=[owner_id])
    versions = db.relationship("PolicyVersion", backref="policy", lazy="dynamic",
                                order_by="PolicyVersion.version_number.desc()",
                                cascade="all, delete-orphan")

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
        return f"<Policy {self.title} v{self.current_version}>"


class PolicyVersion(db.Model):
    __tablename__ = "policy_version"

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey("policy.id"), nullable=False)
    version_number = db.Column(db.String(16), nullable=False)
    content = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(256), nullable=True, comment="Uploaded file path for this version")
    original_filename = db.Column(db.String(256), nullable=True, comment="Original uploaded file name")
    file_size = db.Column(db.Integer, nullable=True, comment="File size in bytes")
    change_summary = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship("User", backref="policy_versions", foreign_keys=[created_by_id])

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
        return f"<PolicyVersion v{self.version_number} of Policy {self.policy_id}>"
