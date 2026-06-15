from datetime import datetime
from app.extensions import db


class KpiDefinition(db.Model):
    __tablename__ = "kpi_definition"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    formula = db.Column(db.String(256), nullable=True)
    target = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(32), nullable=True, comment="percent|count|days|score")
    frequency = db.Column(db.String(32), default="monthly", comment="daily|weekly|monthly|quarterly|yearly")
    category = db.Column(db.String(64), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    measurements = db.relationship("KpiMeasurement", backref="kpi", lazy="dynamic",
                                   order_by="KpiMeasurement.measured_at.desc()",
                                   cascade="all, delete-orphan")

    def __repr__(self):
        return f"<KpiDefinition {self.name}>"


class KpiMeasurement(db.Model):
    __tablename__ = "kpi_measurement"

    id = db.Column(db.Integer, primary_key=True)
    kpi_id = db.Column(db.Integer, db.ForeignKey("kpi_definition.id"), nullable=False)
    value = db.Column(db.Float, nullable=False)
    measured_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<KpiMeasurement {self.kpi_id}: {self.value} at {self.measured_at}>"
