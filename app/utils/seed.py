import json
import os
from app.extensions import db


def seed_database():
    from app.models.user import User, Role, Permission
    from app.models.domain import Domain
    from app.models.control import Control
    from app.models.clause import Clause
    from app.models.metric import KpiDefinition

    seed_dir = os.path.join(os.path.dirname(__file__), "..", "..", "seed_data")

    # ── Roles & Permissions ────────────────────────────────────
    with open(os.path.join(seed_dir, "roles.json")) as f:
        roles_data = json.load(f)

    all_perms = {}
    for rd in roles_data["roles"]:
        for pcode in rd["permissions"]:
            if pcode not in all_perms:
                perm = Permission.query.filter_by(codename=pcode).first()
                if not perm:
                    perm = Permission(name=pcode.replace("_", " ").title(), codename=pcode)
                    db.session.add(perm)
                all_perms[pcode] = perm

    db.session.flush()

    for rd in roles_data["roles"]:
        role = Role.query.filter_by(name=rd["name"]).first()
        if not role:
            role = Role(name=rd["name"], description=rd["description"])
            db.session.add(role)
            db.session.flush()
        existing_codenames = {p.codename for p in role.permissions}
        for pcode in rd["permissions"]:
            if pcode not in existing_codenames:
                perm = all_perms.get(pcode) or Permission.query.filter_by(codename=pcode).first()
                if perm:
                    role.permissions.append(perm)

    db.session.flush()

    # ── Default Users (only on first run) ──────────────────────
    if User.query.first() is None:
        from app.extensions import bcrypt
        admin = User(
            username="admin",
            email="admin@iso27001-manager.com",
            first_name="System",
            last_name="Administrator",
            is_active=True,
        )
        admin.password = "Admin@ISO27001!2024"
        admin.roles.append(Role.query.filter_by(name="admin").first())
        db.session.add(admin)

        default_users = [
            ("manager", "Manager", "User", "manager@iso27001-manager.com", "Manager@ISO27001!2024", "manager"),
            ("auditor", "Internal", "Auditor", "auditor@iso27001-manager.com", "Auditor@ISO27001!2024", "auditor"),
            ("user", "Regular", "User", "user@iso27001-manager.com", "User@ISO27001!2024", "user"),
        ]
        for uname, fn, ln, email, pw, rname in default_users:
            u = User(username=uname, email=email, first_name=fn, last_name=ln, is_active=True)
            u.password = pw
            u.roles.append(Role.query.filter_by(name=rname).first())
            db.session.add(u)

    # ── Annex A Controls (only on first run) ───────────────────
    if Domain.query.first() is None:
        with open(os.path.join(seed_dir, "annex_a_controls.json")) as f:
            annex_data = json.load(f)

        for dd in annex_data["domains"]:
            domain = Domain(code=dd["code"], name=dd["name"], description=dd["description"],
                            sort_order=dd["sort_order"])
            db.session.add(domain)
            db.session.flush()
            for cd in dd["controls"]:
                control = Control(
                    code=cd["code"],
                    title=cd["title"],
                    description=cd.get("description"),
                    detailed_description=cd.get("detailed_description"),
                    purpose=cd["purpose"],
                    guidance=cd.get("guidance"),
                    domain_id=domain.id,
                    sort_order=int(cd["code"].split(".")[1]),
                    is_new_2022=cd.get("is_new_2022", False),
                )
                db.session.add(control)

    # ── Clauses (only on first run) ────────────────────────────
    if Clause.query.first() is None:
        with open(os.path.join(seed_dir, "clauses.json")) as f:
            clauses_data = json.load(f)

        for cd in clauses_data:
            clause = Clause(
                number=cd["number"],
                title=cd["title"],
                title_el=cd.get("title_el"),
                description=cd["description"],
                description_el=cd.get("description_el"),
                sort_order=cd["sort_order"],
            )
            db.session.add(clause)

    # ── Default KPIs (only on first run) ───────────────────────
    if KpiDefinition.query.first() is None:
        default_kpis = [
            ("Controls Implementation", "Percentage of controls implemented", "implemented_controls/total_controls*100", 80, "percent", "monthly", "Implementation"),
            ("Risk Treatment Progress", "Percentage of risks with treatment plans completed", "treated_risks/total_risks*100", 90, "percent", "monthly", "Risk Management"),
            ("Incident Resolution Time", "Average time to resolve incidents", "avg_resolution_time", 48, "hours", "monthly", "Incident Management"),
            ("Audit Finding Closure", "Percentage of audit findings closed within target", "closed_findings/total_findings*100", 90, "percent", "quarterly", "Audit"),
            ("Policy Review Currency", "Percentage of policies reviewed on time", "reviewed_policies/total_policies*100", 95, "percent", "monthly", "Governance"),
        ]
        for name, desc, formula, target, unit, freq, cat in default_kpis:
            kpi = KpiDefinition(
                name=name, description=desc, formula=formula,
                target=target, unit=unit, frequency=freq, category=cat,
            )
            db.session.add(kpi)

    # ── NIS2 Compliance Checks (only on first run) ─────────────
    from app.models.nis2 import Nis2ComplianceCheck

    if Nis2ComplianceCheck.query.first() is None:
        nis2_measures = [
            ("risk_analysis", "Risk Analysis & IS Policies", "Art 21(2)(a)"),
            ("incident_handling", "Incident Handling", "Art 21(2)(b)"),
            ("business_continuity", "Business Continuity", "Art 21(2)(g)"),
            ("supply_chain_security", "Supply Chain Security", "Art 21(2)(d)"),
            ("network_security", "Network & Information Security", "Art 21(2)(c)"),
            ("access_control", "Access Control", "Art 21(2)(e)"),
            ("cryptography", "Cryptography", "Art 21(2)(f)"),
            ("hr_security", "HR Security", "Art 21(2)(h)"),
            ("mfa", "Multi-Factor Authentication", "Art 21(2)(i)"),
            ("security_training", "Security Training", "Art 21(2)(j)"),
        ]
        for measure, display, article in nis2_measures:
            check = Nis2ComplianceCheck(
                measure=measure,
                measure_display=display,
                article_ref=article,
                status="not_started",
            )
            db.session.add(check)

    db.session.commit()
