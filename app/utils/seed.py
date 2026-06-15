import json
import os
from app.extensions import db


def seed_database():
    from app.models.user import User, Role, Permission
    from app.models.domain import Domain
    from app.models.control import Control
    from app.models.clause import Clause
    from app.models.metric import KpiDefinition

    if Role.query.first() is not None:
        return

    seed_dir = os.path.join(os.path.dirname(__file__), "..", "..", "seed_data")

    with open(os.path.join(seed_dir, "roles.json")) as f:
        roles_data = json.load(f)

    all_perms = {}
    for rd in roles_data["roles"]:
        for pcode in rd["permissions"]:
            if pcode not in all_perms:
                all_perms[pcode] = Permission(name=pcode.replace("_", " ").title(), codename=pcode)
                db.session.add(all_perms[pcode])

    roles_map = {}
    for rd in roles_data["roles"]:
        role = Role(name=rd["name"], description=rd["description"])
        db.session.add(role)
        roles_map[rd["name"]] = role
        for pcode in rd["permissions"]:
            role.permissions.append(all_perms[pcode])

    from app.extensions import bcrypt
    admin = User(
        username="admin",
        email="admin@iso27001-manager.com",
        first_name="System",
        last_name="Administrator",
        is_active=True,
    )
    admin.password = "Admin@ISO27001!2024"
    admin.roles.append(roles_map["admin"])
    db.session.add(admin)

    default_users = [
        ("manager", "Manager", "User", "manager@iso27001-manager.com", "Manager@ISO27001!2024", "manager"),
        ("auditor", "Internal", "Auditor", "auditor@iso27001-manager.com", "Auditor@ISO27001!2024", "auditor"),
        ("user", "Regular", "User", "user@iso27001-manager.com", "User@ISO27001!2024", "user"),
    ]
    for uname, fn, ln, email, pw, rname in default_users:
        u = User(username=uname, email=email, first_name=fn, last_name=ln, is_active=True)
        u.password = pw
        u.roles.append(roles_map[rname])
        db.session.add(u)

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

    with open(os.path.join(seed_dir, "clauses.json")) as f:
        clauses_data = json.load(f)

    for cd in clauses_data:
        clause = Clause(
            number=cd["number"],
            title=cd["title"],
            description=cd["description"],
            sort_order=cd["sort_order"],
        )
        db.session.add(clause)

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

    db.session.commit()
