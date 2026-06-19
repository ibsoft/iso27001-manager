================================================================================
ISO 27001 / 2022 ISMS Manager (with NIS2 & GDPR)
================================================================================

A web-based Information Security Management System (ISMS) manager built with
Flask.  Covers ISO 27001:2022 Annex A controls, NIS2 compliance, GDPR (DPA,
DSAR, RoPA), risk management, asset management, incident management, audit
management, policy management, business continuity, supplier/third-party risk,
training & competence, KPI dashboard, AI assistant, and AD/LDAP authentication.


Table of Contents
--------------------------------------------------------------------------------
1.  Requirements
2.  Quick Start (SQLite – Development)
3.  Production Deployment (PostgreSQL)
4.  Environment Variables
5.  Database Migrations
6.  Seed Data
7.  Translations
8.  AD / LDAP Authentication
9.  SSO Configuration (Placeholder)
10. AI Assistant
11. Backup & Restore
12. Directory Structure
13. Troubleshooting


1. Requirements
--------------------------------------------------------------------------------

  * Python >= 3.10
  * pip / virtualenv (recommended)
  * SQLite (development) or PostgreSQL 14+ (production)
  * Optional: Redis (for session storage)
  * Optional: SMTP server (for email notifications)


2. Quick Start (SQLite – Development)
--------------------------------------------------------------------------------

  1. Clone the repository and enter the directory:

       cd iso27001-manager

  2. Create a virtual environment and activate it:

       python3 -m venv .venv
       source .venv/bin/activate      # Linux / macOS
       .venv\Scripts\activate          # Windows

  3. Install dependencies:

       pip install -r requirements.txt

  4. Run the application:

       .venv/bin/python run.py

     The server starts at http://127.0.0.1:5000.
     On first run the database is created automatically and seed data is loaded.

  5. Default admin credentials:

       Username:  admin
       Password:  Admin@ISO27001!2024

     Additional pre-seeded users: manager / auditor / user (same password
     convention with respective role name).


3. Production Deployment (PostgreSQL)
--------------------------------------------------------------------------------

  1. Create a PostgreSQL database:

       CREATE DATABASE isms;
       CREATE USER isms_user WITH PASSWORD 'strong_password';
       GRANT ALL PRIVILEGES ON DATABASE isms TO isms_user;

  2. Set the DATABASE_URL environment variable:

       export DATABASE_URL=postgresql://isms_user:strong_password@localhost:5432/isms

  3. Install dependencies (including the PostgreSQL adapter):

       pip install -r requirements.txt

  4. Run with Gunicorn:

       gunicorn -w 4 -b 0.0.0.0:8000 'app:create_app()'

     Tables are created and seed data loaded automatically on first startup.

  NOTE:  "user" and "control" are reserved words in PostgreSQL.  The schema
  migration functions quote them with double-quotes (") for compatibility.
  If you encounter ALTER TABLE errors, verify your PostgreSQL version is 14+.


4. Environment Variables
--------------------------------------------------------------------------------

  Variable                    Default                          Description
  ─────────────────────────────────────────────────────────────────────────────
  FLASK_ENV                   development                     Environment name
  SECRET_KEY                  dev-secret-…                     Flask secret key
  DATABASE_URL                sqlite:///…/isms.db              Database URI
  SESSION_TYPE                filesystem                       Session backend
  SESSION_REDIS               (none)                           Redis URL
  MAIL_SERVER                 smtp.gmail.com                   SMTP server
  MAIL_PORT                   587                              SMTP port
  MAIL_USE_TLS                true                             SMTP TLS flag
  MAIL_USERNAME               (empty)                          SMTP username
  MAIL_PASSWORD               (empty)                          SMTP password
  MAIL_DEFAULT_SENDER         noreply@example.com              From address
  TOTP_ISSUER_NAME            ISO27001-Manager                 TOTP issuer
  ADMIN_EMAIL                 admin@example.com                Admin contact

  Create a .env file in the project root to set these values:

       SECRET_KEY=your-strong-secret-here
       DATABASE_URL=postgresql://user:pass@localhost:5432/isms

  The .env file is excluded from version control (see .gitignore).


5. Database Migrations
--------------------------------------------------------------------------------

  The application uses Flask-Migrate (Alembic) for schema migrations.

  Create a migration after model changes:

       .venv/bin/python run.py db migrate -m "Description of change"
       .venv/bin/python run.py db upgrade

  On startup, the application also runs several ensure_*() functions that add
  columns if they do not yet exist (supplier risk columns, guidance_el on
  controls, guidance/guidance_el on NIS2 checks, auth_source on user table).
  These provide a safety net for environments where Alembic migrations have
  not yet been applied.


6. Seed Data
--------------------------------------------------------------------------------

  Seed JSON files are located in seed_data/:

       roles.json                      Role definitions & permissions
       annex_a_controls.json           ISO 27001:2022 Annex A controls
       clauses.json                    ISO 27001:2022 clauses
       nis2_controls.json              NIS2 compliance measures & guidance

  The seed_database() function in app/utils/seed.py runs automatically on
  startup (idempotent – does not overwrite existing data).  It seeds:

    * Roles: admin, manager, auditor, user
    * Users: admin, manager, auditor, user (only when the user table is empty)
    * Domains and Annex A controls (only when domain table is empty)
    * Clauses (only when clause table is empty)
    * KPI definitions (10 default KPIs, only on first run)
    * NIS2 compliance checks (10 measures, only on first run)

  To re-seed specific tables, truncate them manually and restart the app.


7. Translations
--------------------------------------------------------------------------------

  Supported locales:  en (English)  /  el (Ελληνικά)

  Translation files are in app/translations/<locale>/LC_MESSAGES/messages.po.

  On every startup the application compiles .po → .mo automatically using
  pybabel compile.  You can also compile manually:

       pybabel compile -d app/translations

  To extract new translatable strings after code changes:

       pybabel extract -F babel.cfg -o messages.pot .

  To update an existing .po file:

       pybabel update -i messages.pot -d app/translations -l el

  To create a new locale:

       pybabel init -i messages.pot -d app/translations -l de

  The built-in language switcher is in the user menu (top-right).  An admin
  can force a language for all users via the Admin → AI Settings page
  (currently stored under AI Settings – to be moved to a dedicated
  Localization settings page.)


8. AD / LDAP Authentication
--------------------------------------------------------------------------------

  The application supports authenticating users against an LDAP directory
  (Active Directory, OpenLDAP, etc.).

  Configuration (Admin → LDAP Settings):

    * Enable LDAP Authentication        – Master on/off toggle
    * LDAP Server                        – e.g. ldap://dc01.example.com
    * Port                               – 389 (LDAP) or 636 (LDAPS)
    * Use TLS                            – Enable STARTTLS
    * Base DN                            – e.g. DC=example,DC=com
    * Bind DN                            – Service account DN (optional)
    * Bind Password                      – Service account password
    * User Filter                        – LDAP filter string, use {username}
                                           as placeholder, e.g.
                                           (sAMAccountName={username})
    * Attribute Mapping (JSON)           – Maps local fields to LDAP
                                           attributes:
      {
        "email":      "mail",
        "first_name": "givenName",
        "last_name":  "sn"
      }

  How it works:

    1. User submits username + password on the login page.
    2. The application checks if LDAP is enabled and the username does not
       already exist as a local-only (auth_source='local') user.
    3. If LDAP conditions are met, it binds to the LDAP server using the
       configured service account, searches for the user, and attempts to
       re-bind as that user to verify the password.
    4. On success, a local User record is created (or updated) with
       auth_source='ldap'.  The user is assigned the "user" role
       automatically.
    5. Subsequent logins continue through LDAP.  Local users (auth_source
       = 'local') are not affected and authenticate with their hashed
       password as before.

  NOTE:  The bind password and attribute mapping are stored in plain text
  in the SystemSetting table.  For production, consider using a vault or
  environment variables instead.


9. SSO Configuration (Placeholder)
--------------------------------------------------------------------------------

  Admin → SSO Settings provides a form to store SAML 2.0 / OIDC provider
  parameters (provider type, client ID, client secret, issuer URL, metadata
  URL).  These values are persisted in the SystemSetting table but the
  actual authentication flow (SAML assertion handling / OIDC callback) is
  NOT implemented yet and remains a future enhancement.


10. AI Assistant
--------------------------------------------------------------------------------

  An optional AI assistant powered by OpenAI GPT-4o-mini provides context-
  aware answers about the ISMS.  The assistant has read-only access to the
  database schema and can answer questions about compliance, risks,
  controls, and system usage.

  Admin configuration (Admin → AI Settings):

    1. Set your OpenAI API Key.
    2. Enable the assistant for all users.

  Once enabled, a floating chat button appears in the bottom-right corner.

  Chat history is limited to the last 7 messages per session.

  The assistant uses function calling with a single tool, query_db, that
  executes read-only SQL SELECT queries.  It never modifies data.


11. Backup & Restore
--------------------------------------------------------------------------------

  Admin → Backup & Restore

    * Create Backup   – Zips the SQLite database (or PostgreSQL dump) and
                        uploaded files into app/static/backups/.
    * Download        – Download a backup archive.
    * Restore         – Upload a backup archive and restore.
    * Delete          – Remove a backup archive.

  For PostgreSQL, backups are created by running pg_dump.  Ensure pg_dump
  is installed on the server.  The database connection string is read from
  the DATABASE_URL environment variable.


12. Directory Structure
--------------------------------------------------------------------------------

  iso27001-manager/
  ├── app/
  │   ├── __init__.py            Application factory
  │   ├── extensions.py          Flask extensions (db, login, bcrypt, etc.)
  │   ├── forms/                 WTForms form definitions
  │   ├── models/                SQLAlchemy models
  │   │   ├── user.py            User, Role, Permission, SystemSetting
  │   │   ├── control.py         Annex A controls
  │   │   ├── domain.py          Control domains
  │   │   ├── clause.py          ISO 27001 clauses
  │   │   ├── metric.py          KPI definitions
  │   │   ├── risk.py            Risk register
  │   │   ├── asset.py           Asset register
  │   │   ├── incident.py        Incident management
  │   │   ├── policy.py          Policy management
  │   │   ├── audit.py           Audit management
  │   │   ├── supplier.py        Supplier / third-party risk
  │   │   ├── nis2.py            NIS2 compliance checks
  │   │   ├── gdpr.py            GDPR data processing records
  │   │   ├── training.py        Training & competence
  │   │   ├── bc.py              Business continuity
  │   │   ├── capa.py            Corrective actions
  │   │   └── …                  Additional model files
  │   ├── routes/                Blueprint route definitions
  │   ├── templates/             Jinja2 templates
  │   ├── static/                CSS, JS, uploaded files
  │   ├── translations/          Babel .po / .mo files
  │   └── utils/                 Helper modules
  │       ├── seed.py            Seed data loader
  │       ├── schema.py          Schema migration helpers
  │       ├── metrics.py         KPI auto-calculation engine
  │       ├── ldap_auth.py       LDAP / AD authentication
  │       ├── ai_helper.py       AI assistant orchestration
  │       ├── decorators.py      Route decorators (admin_required, etc.)
  │       └── pagination.py      Pagination utility
  ├── seed_data/                 JSON seed files
  │   ├── roles.json
  │   ├── annex_a_controls.json
  │   ├── clauses.json
  │   └── nis2_controls.json
  ├── config.py                  Configuration classes
  ├── requirements.txt           Python dependencies
  ├── run.py                     Entry point
  ├── README.md                  This file
  └── .gitignore


13. Troubleshooting
--------------------------------------------------------------------------------

  "TemplateNotFound: bootstrap5/form.html"
       → Remove the line  {% import "bootstrap5/form.html" as wtf %} from the
         template – this project uses plain HTML forms, not Flask-Bootstrap.

  "psycopg2.OperationalError" when using PostgreSQL
       → Verify DATABASE_URL is correct and the PostgreSQL server is running.
       → Ensure the user has been granted CONNECT and CREATE privileges.

  "pybabel: command not found"
       → Run  pip install -r requirements.txt  inside the virtual environment
         and use  .venv/bin/pybabel.

  "ldap3.core.exceptions.LDAPException" on login
       → Verify LDAP server address, port, and TLS settings in Admin → LDAP
         Settings.
       → Check that the Base DN and Bind DN are correct.
       → Ensure the firewall allows outbound connections to the LDAP port.

  Translations not appearing (texts show English on Greek locale)
       → Restart the application – translations are compiled on startup.
       → Run  .venv/bin/pybabel compile -d app/translations  manually.
       → Check that your browser language preference is set to Greek (el).

  "Disk quota exceeded" or "No space left" during upload
       → Check MAX_CONTENT_LENGTH in config.py (default 16 MB) and server
         disk space.

  "Failed to build wheel for pyasn1"
       → Ensure you have a C compiler installed (build-essential / xcode-select
         --install).  pyasn1 has a Rust dependency on some platforms; if the
         build fails, install the pre-compiled binary wheel:

             pip install pyasn1 --only-binary=:all:

         or use your system package manager:

             apt install python3-pyasn1          # Debian / Ubuntu
             dnf install python3-pyasn1          # Fedora

================================================================================
