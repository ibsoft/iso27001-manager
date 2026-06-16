from datetime import datetime
from app.extensions import db


class Clause(db.Model):
    __tablename__ = "clause"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False, comment="4-10")
    title = db.Column(db.String(256), nullable=False)
    title_el = db.Column(db.String(256), nullable=True)
    description = db.Column(db.Text, nullable=True)
    description_el = db.Column(db.Text, nullable=True)
    is_mandatory = db.Column(db.Boolean, default=True)
    implementation_notes = db.Column(db.Text, nullable=True)
    implementation_notes_el = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def localized_title(self, lang="en"):
        return self.title_el if lang == "el" and self.title_el else self.title

    def localized_description(self, lang="en"):
        return self.description_el if lang == "el" and self.description_el else self.description

    def __repr__(self):
        return f"<Clause {self.number}: {self.title}>"
