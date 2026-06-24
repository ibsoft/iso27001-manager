from sqlalchemy import inspect, text

from app.extensions import db
from app.paths import app_root


def _q(table):
    """Quote identifier for PostgreSQL & SQLite compatibility."""
    return f'"{table}"'


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
            db.session.execute(text(f"ALTER TABLE {_q('supplier')} ADD COLUMN {name} {sql_type}"))
    db.session.commit()


def update_control_guidance():
    """Update control guidance fields from seed JSON on every startup."""
    import json
    import os
    from app.models.control import Control

    seed_dir = os.path.join(app_root(), "seed_data")
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
            db.session.execute(text(f"ALTER TABLE {_q('control')} ADD COLUMN guidance_el TEXT"))
            db.session.commit()


def ensure_nis2_columns():
    """Add guidance/guidance_el columns to nis2_compliance_check if missing."""
    inspector = inspect(db.engine)
    if not inspector.has_table("nis2_compliance_check"):
        return
    existing = {c["name"] for c in inspector.get_columns("nis2_compliance_check")}
    for col in ("guidance", "guidance_el"):
        if col not in existing:
            db.session.execute(text(f"ALTER TABLE nis2_compliance_check ADD COLUMN {col} TEXT"))
    db.session.commit()


def ensure_auth_columns():
    """Add auth_source column to user table if missing."""
    inspector = inspect(db.engine)
    if inspector.has_table("user"):
        existing = {c["name"] for c in inspector.get_columns("user")}
        if "auth_source" not in existing:
            db.session.execute(text(
                f"ALTER TABLE {_q('user')} ADD COLUMN auth_source VARCHAR(16) NOT NULL DEFAULT 'local'"
            ))
            db.session.commit()


def update_nis2_guidance():
    """Update NIS2 compliance check guidance fields from seed JSON on every startup."""
    import json
    import os
    from app.models.nis2 import Nis2ComplianceCheck

    seed_dir = os.path.join(app_root(), "seed_data")
    json_path = os.path.join(seed_dir, "nis2_controls.json")
    if not os.path.exists(json_path):
        return

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    lookup = {item["measure"]: item for item in data.get("measures", [])}

    updated = 0
    for check in Nis2ComplianceCheck.query.all():
        jc = lookup.get(check.measure)
        if not jc:
            continue
        changed = False
        for field in ("guidance", "guidance_el"):
            val = jc.get(field)
            if val and val != getattr(check, field):
                setattr(check, field, val)
                changed = True
        if changed:
            updated += 1

    db.session.commit()
