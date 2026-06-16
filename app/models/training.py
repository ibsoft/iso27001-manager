from datetime import datetime, date
from app.extensions import db


class TrainingCourse(db.Model):
    __tablename__ = "training_course"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(32), default="awareness",
                         comment="awareness|technical|process|compliance|management|other")
    provider = db.Column(db.String(256), nullable=True)
    duration_hours = db.Column(db.Float, nullable=True)
    validity_days = db.Column(db.Integer, nullable=True,
                              comment="Days until retraining required")
    is_mandatory = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(16), default="active", comment="active|inactive|archived")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions = db.relationship("TrainingSession", backref="course",
                               lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TrainingCourse {self.title}>"


class TrainingSession(db.Model):
    __tablename__ = "training_session"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("training_course.id"), nullable=False)
    title = db.Column(db.String(256), nullable=True)
    session_date = db.Column(db.Date, nullable=False, default=date.today)
    trainer = db.Column(db.String(256), nullable=True)
    location = db.Column(db.String(256), nullable=True)
    max_attendees = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(16), default="scheduled",
                       comment="scheduled|in_progress|completed|cancelled")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    records = db.relationship("TrainingRecord", backref="session",
                              lazy="dynamic", cascade="all, delete-orphan")

    @property
    def enrolled_count(self):
        return self.records.count()

    def __repr__(self):
        return f"<TrainingSession {self.title or self.course.title} @ {self.session_date}>"


class TrainingRecord(db.Model):
    __tablename__ = "training_record"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("training_session.id"), nullable=False)
    status = db.Column(db.String(16), default="enrolled",
                       comment="enrolled|completed|no_show|expired")
    completed_date = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    certificate_ref = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="training_records", foreign_keys=[user_id])

    def __repr__(self):
        return f"<TrainingRecord user={self.user_id} session={self.session_id} status={self.status}>"


class CompetenceProfile(db.Model):
    __tablename__ = "competence_profile"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    skill_name = db.Column(db.String(128), nullable=False)
    skill_level = db.Column(db.String(16), default="beginner",
                            comment="beginner|intermediate|advanced|expert")
    category = db.Column(db.String(32), default="technical",
                         comment="technical|security|compliance|management|soft_skill|other")
    last_assessment_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="competence_profiles", foreign_keys=[user_id])

    def __repr__(self):
        return f"<CompetenceProfile {self.skill_name} [{self.skill_level}]>"
