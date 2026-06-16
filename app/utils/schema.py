from sqlalchemy import inspect, text

from app.extensions import db


def ensure_supplier_risk_columns():
    inspector = inspect(db.engine)
    if not inspector.has_table("supplier"):
        return

    existing = {column["name"] for column in inspector.get_columns("supplier")}
    columns = {
        "vendor_type": "VARCHAR(32)",
        "lifecycle_stage": "VARCHAR(32)",
        "data_access_level": "VARCHAR(32)",
        "inherent_risk": "VARCHAR(16)",
        "residual_risk": "VARCHAR(16)",
        "risk_score": "INTEGER",
        "risk_treatment": "VARCHAR(32)",
        "risk_owner": "VARCHAR(128)",
        "next_review_date": "DATE",
        "monitoring_frequency": "VARCHAR(32)",
        "due_diligence_completed": "BOOLEAN",
        "contract_security_clauses": "BOOLEAN",
        "audit_rights": "BOOLEAN",
        "subcontractors_allowed": "BOOLEAN",
        "incident_notification_sla": "VARCHAR(64)",
        "sla_requirements": "TEXT",
        "risk_treatment_plan": "TEXT",
        "exit_strategy": "TEXT",
        "offboarding_date": "DATE",
    }

    for name, sql_type in columns.items():
        if name not in existing:
            db.session.execute(text(f"ALTER TABLE supplier ADD COLUMN {name} {sql_type}"))
    db.session.commit()
