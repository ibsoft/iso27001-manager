# ISO 27001 Manager — User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Default Accounts](#default-accounts)
3. [Dashboard](#dashboard)
4. [ISMS Framework](#isms-framework)
5. [Risk & Assets](#risk--assets)
6. [Operations](#operations)
7. [Reporting](#reporting)
8. [Administration](#administration)
9. [Language Support](#language-support)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Starting the Application

```bash
cd /path/to/iso27001-manager
source venv/bin/activate
python run.py
```

The app starts at `http://0.0.0.0:5000`. Open your browser and navigate there.

For production, use a WSGI server:

```bash
gunicorn wsgi:app
```

### First-Time Setup

On first launch, the application automatically:
1. Creates the SQLite database (`instance/isms.db`)
2. Seeds 4 default user accounts
3. Loads all 93 ISO 27001:2022 Annex A controls across 4 domains
4. Loads ISO 27001 Clauses 4–10
5. Creates 5 default KPI definitions

No manual setup is required.

---

## Default Accounts

The following accounts are created automatically. **Change these passwords immediately after first login.**

| Username | Role | Password |
|---|---|---|
| `admin` | Administrator | `Admin@ISO27001!2024` |
| `manager` | Manager | `Manager@ISO27001!2024` |
| `auditor` | Internal Auditor | `Auditor@ISO27001!2024` |
| `user` | Regular User | `User@ISO27001!2024` |

### Role Overview

| Role | Capabilities |
|---|---|
| **admin** | Full access: user management, all modules, system configuration, audit log |
| **manager** | Create and edit: controls, risks, assets, incidents, policies, audits, suppliers, SoA |
| **auditor** | Read-only access across all modules, can create audits and findings |
| **user** | Read-only access, can report incidents |

### Changing Your Password

1. Click your name in the top-right corner
2. Select **Change Password**
3. Enter your current password and the new password
4. New password must be at least 12 characters with uppercase, lowercase, digit, and special character

---

## Dashboard

The dashboard at `/` gives you a high-level overview of your ISMS:

- **Controls Implemented** — percentage and count of implemented Annex A controls
- **Critical/High Risks** — count of high-severity risks requiring attention
- **Open Incidents** — unreported/unresolved security incidents
- **Open Non-Conformities** — audit findings still needing corrective action
- **Controls Implementation Status** — visual breakdown by implementation status
- **Recent Incidents** — latest security incidents
- **ISMS Health** — policy review currency and other metrics
- **Quick Actions** — shortcuts to common tasks (browse controls, schedule audit, create policy, view SoA)

---

## ISMS Framework

### ISO Clauses 4–10 (`/clauses/`)

The mandatory requirements of ISO 27001:2022 organized into 7 clauses. Each clause displays its description. This is a reference section — no user editing is required.

### Annex A Controls (`/controls/`)

The 93 controls from ISO 27001:2022 Annex A, organized by domain:

| Domain | Controls | Focus |
|---|---|---|
| **5 — Organizational** | 37 controls | Governance, policy, roles, supplier security, incident management |
| **6 — People** | 8 controls | Screening, awareness, confidentiality agreements, remote work |
| **7 — Physical** | 14 controls | Perimeter security, equipment, cabling, clear desk |
| **8 — Technological** | 34 controls | Access control, cryptography, malware, backup, logging, networks |

Each control has a `code` (e.g. `5.1`, `8.9`), a `title`, `purpose`, `guidance`, and tracks:
- **Implementation Status** — Not Started / In Progress / Implemented / Not Applicable
- **Owner** — responsible person
- **Target Date** — planned completion date
- **Review Date** — next review date
- **Evidence Notes** — documentation proving implementation

To update a control's status, either:
1. Click the control → **Edit** → update fields → **Save**
2. Click the control → use the **Quick Status Update** dropdown directly on the view page

You can also **create custom controls** using the **New Control** button on the controls list page.

### Statement of Applicability (`/soa/`)

The SoA maps each Annex A control to your organization's applicability decision:

- **Applicable** — the control is relevant and implemented
- **Not Applicable** — you must provide a justification

Each SoA entry tracks:
- **Applicable** — yes/no decision
- **Justification** — reason if not applicable
- **Implementation Status** — same as control status
- **Control Description** — auto-populated from the control
- **Responsible Person** — who owns this control

The SoA summary page (`/soa/summary`) shows the full table. You can export it as a print-friendly page (`/soa/export`).

---

## Risk & Assets

### Risk Management (`/risks/`)

Track and manage information security risks. Each risk includes:

| Field | Description |
|---|---|
| Title | Risk description |
| Asset | Affected asset (optional) |
| Likelihood (1–5) | Probability of occurrence |
| Impact (1–5) | Severity if realized |
| Risk Score | Likelihood × Impact (displayed as heat map color) |
| Risk Level | Low / Medium / High / Critical |
| Treatment | Mitigation / Acceptance / Avoidance / Transfer |
| Treatment Plan | Detailed action plan |
| Residual Likelihood/Impact | Post-treatment assessment |
| Status | Identified / Assessed / Treatment In Progress / Residual Accepted |
| Risk Owner | Responsible person |

The **Risk Heat Map** at `/risks/risk-matrix` visualizes all risks on a 5×5 grid.

### Asset Register (`/assets/`)

Inventory of information assets. Each asset tracks:

| Field | Description |
|---|---|
| Name | Asset identifier |
| Serial Number | Manufacturer serial number or asset tag (optional) |
| Type | Hardware / Software / Data / Personnel / Facility / Other |
| Classification | Public / Internal / Confidential / Restricted |
| Criticality | Low / Medium / High / Critical |
| Status | Active / Inactive / Disposed |
| Owner | Responsible person |
| Location | Physical or logical location |
| Retention Period | How long to retain (optional) |
| Notes | Free-text notes |

Assets can be filtered by classification, type, and searched by name.

---

## Operations

### Incidents (`/incidents/`)

Report and track information security incidents. Each incident includes:

| Field | Description |
|---|---|
| Title | Incident summary |
| Description | Detailed description |
| Severity | Low / Medium / High / Critical |
| Category | Malware / Phishing / Unauthorized Access / Data Breach / Theft / Social Engineering / Physical / Other |
| Status | Reported / Investigating / Contained / Resolved |
| Assigned To | Investigator |
| Root Cause | Why it happened |
| Impact Description | Business impact |
| Lessons Learned | Post-incident review |
| Timeline | Reported → Contained → Resolved timestamps |

### Policies & Documents (`/policies/`)

Create and manage information security policies with version control. The editor uses **TinyMCE**, a WYSIWYG (What You See Is What You Get) rich text editor — no HTML knowledge required.

| Feature | Description |
|---|---|
| **WYSIWYG Editor** | Format text with bold, italic, headings, tables, lists, colors, and more |
| **Versioning** | Every change creates a version snapshot |
| **New Version** | Creates a new numbered version with change summary |
| **Status Workflow** | Draft → Reviewed → Approved → Published → Retired |
| **PDF Download** | Click **Download PDF** to export as a formatted PDF document |
| **Formatted View** | Content is rendered as formatted HTML on the view page |

**Creating a policy:**
1. Click **New Policy**
2. Enter title, description, category, status, owner
3. Write/edit content using the WYSIWYG toolbar
4. Set effective and review dates
5. Click **Save**

**Creating a new version:**
1. On the policy view page, click **New Version**
2. Enter a change summary describing what changed
3. Edit content in the WYSIWYG editor
4. The version number is auto-incremented

### Internal Audits (`/audits/`)

Plan and conduct internal audits. Each audit tracks:

| Field | Description |
|---|---|
| Title | Audit name |
| Lead Auditor | Responsible auditor |
| Audit Date | When conducted |
| Scope | What is being audited |
| Status | Planned / In Progress / Completed / Verified Closed |

**Audit Findings** document specific observations:
- **Non-Conformity** — requirement not met
- **Observation** — potential issue
- **Opportunity for Improvement** — suggestion

**Corrective Actions** track remediation:
- Each finding can have corrective actions
- Status: Open / In Progress / Completed / Verified Closed

### Non-Conformities (`/audits/non-conformities/`)

A consolidated view of all non-conformities across all audits, with their current corrective action status.

### Suppliers (`/suppliers/`)

Manage supplier relationships and their security posture. Each supplier tracks:

| Field | Description |
|---|---|
| Supplier Name | Organization name |
| Contact | Name, email, phone |
| Service Description | What they provide |
| Security Requirements | Contractual security obligations |
| Assessment Status | Pending / Approved / Review Required / Rejected |
| DPA in Place | Data Processing Agreement status |
| Contract Period | Start and end dates |

---

## Reporting

### Reports (`/reports/`)

The reporting center provides:

| Report | Description |
|---|---|
| **Controls Status** | Implementation progress by domain with counts |
| **Risk Summary** | Risk levels, treatments, and status breakdown |
| **Incident Trends** | Incidents grouped by severity, status, and category |
| **CSV Exports** | Export controls, risks, incidents, assets, and SoA data as CSV |
| **Audit Log** | Full audit trail of all user actions |

### Audit Trail

Admins can view the complete audit log at `/admin/audit-log/` or through the reports section. Every significant action (login, create, update, delete) is logged with timestamp, user, IP address, and details.

---

## Administration

### User Management (`/admin/users/`)

Admins can:
- **Create users** — set username, email, name, password, roles
- **Edit users** — update details, reset password (leave blank to keep current)
- **Activate/Deactivate** — prevent login without deleting the account
- **Manage Roles** — view available roles and their permissions

Users are organized by roles. Each role has a predefined set of permissions.

---

## Language Support

The application supports **English** and **Greek (Ελληνικά)**.

### Switching Languages

**From any page:**
1. Click the **globe icon** in the top-right navigation bar
2. Select **Ελληνικά** for Greek or **English** for English

**From the login page:**
Click the language link at the bottom of the login form.

### How it Works

- Your language choice is stored in your session and persists across pages
- The browser's `Accept-Language` header is used as fallback
- Untranslated strings gracefully fall back to English
- All user-facing text — navigation, buttons, labels, flash messages — is translated

---

## Troubleshooting

### Login Issues

| Symptom | Cause | Solution |
|---|---|---|
| "Invalid username or password" | Wrong credentials | Use the correct password or contact an admin. After 5 failed attempts, the account is locked for 15 minutes. |
| "Account is deactivated" | User disabled by admin | Contact an administrator. |
| "Account locked" | Too many failed attempts | Wait 15 minutes or contact an admin. |

### "Page not found" (404)

The URL may be incorrect. Use the sidebar navigation to find the correct page.

### "Permission denied"

Your role does not have the required permission. Contact an administrator to upgrade your role.

### Database Issues

If the database becomes corrupted or you need a fresh start:

```bash
rm instance/isms.db
python run.py
```

The database is recreated with seed data on next startup.

### Controls Not Loading

The 93 Annex A controls are loaded from `seed_data/annex_a_controls.json`. If the file is missing or malformed, delete the database and restart (see above).
