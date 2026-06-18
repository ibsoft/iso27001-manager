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


def update_control_guidance():
    """Update control guidance fields from seed JSON on every startup."""
    import json
    import os
    from app.models.control import Control

    seed_dir = os.path.join(os.path.dirname(__file__), "..", "..", "seed_data")
    json_path = os.path.join(seed_dir, "annex_a_controls.json")
    if not os.path.exists(json_path):
        return

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    lookup = {}
    for domain in data["domains"]:
        for ctrl in domain["controls"]:
            lookup[ctrl["code"]] = ctrl

    updated = 0
    for control in Control.query.all():
        jc = lookup.get(control.code)
        if not jc:
            continue
        changed = False
        for field in ("guidance", "guidance_el"):
            val = jc.get(field)
            if val and val != getattr(control, field):
                setattr(control, field, val)
                changed = True
        if changed:
            updated += 1

    db.session.commit()


def ensure_control_columns():
    """Add guidance_el column to control table if missing (PostgreSQL migration)."""
    inspector = inspect(db.engine)
    if inspector.has_table("control"):
        existing = {c["name"] for c in inspector.get_columns("control")}
        if "guidance_el" not in existing:
            db.session.execute(text("ALTER TABLE control ADD COLUMN guidance_el TEXT"))
            db.session.commit()
