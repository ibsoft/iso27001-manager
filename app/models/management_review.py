from datetime import datetime, date
from app.extensions import db


class ManagementReview(db.Model):
    __tablename__ = "management_review"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    review_date = db.Column(db.Date, nullable=False, default=date.today)
    conducted_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    agenda = db.Column(db.Text, nullable=True)
    minutes = db.Column(db.Text, nullable=True)
    attendees = db.Column(db.Text, nullable=True,
                          comment="Comma-separated list of attendee names")
    status = db.Column(db.String(32), default="planned",
                       comment="planned|in_progress|completed")
    recommendations = db.Column(db.Text, nullable=True)
    next_review_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conducted_by = db.relationship("User", backref="conducted_reviews",
                                   foreign_keys=[conducted_by_id])
    action_items = db.relationship("ReviewActionItem", backref="review",
                                   lazy="dynamic", cascade="all, delete-orphan",
                                   order_by="ReviewActionItem.deadline")

    @property
    def open_action_count(self):
        return self.action_items.filter(
            ReviewActionItem.status.in_(["open", "in_progress"])
        ).count()

    @property
    def completed_action_count(self):
        return self.action_items.filter_by(status="completed").count()

    def __repr__(self):
        return f"<ManagementReview {self.title}>"


class ReviewActionItem(db.Model):
    __tablename__ = "review_action_item"

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey("management_review.id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(32), default="open",
                       comment="open|in_progress|completed|closed")
    completed_at = db.Column(db.DateTime, nullable=True)
    closure_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", backref="review_actions", foreign_keys=[owner_id])

    def __repr__(self):
        return f"<ReviewActionItem {self.id}: {self.status}>"
