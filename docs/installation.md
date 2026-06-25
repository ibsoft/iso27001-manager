# Installation Guide

## Prerequisites

- **Python** 3.10+
- **PostgreSQL** 14+ (optional — SQLite works for development)
- **Redis** 7+ (optional — filesystem sessions work for development)

## Quick Start (Development with SQLite)

```bash
# 1. Clone and enter the directory
cd iso27001-manager

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
./run.py
```

The app starts at http://127.0.0.1:5000. The database and seed data are
created automatically on first startup.

Default admin credentials:

| Username | Password |
|----------|----------|
| admin    | `Admin@ISO27001!2024` |

Additional pre-seeded users: `manager` / `auditor` / `user` (password
follows the same pattern with the respective role name).

## Production (PostgreSQL)

### 1. System Dependencies

**Debian / Ubuntu**

```bash
sudo apt-get update
sudo apt-get install -y build-essential libpq-dev python3-dev libffi-dev libssl-dev
```

### 2. Create Database

```bash
sudo -u postgres psql
CREATE DATABASE isms;
CREATE USER isms_user WITH PASSWORD 'your-strong-password';
GRANT ALL PRIVILEGES ON DATABASE isms TO isms_user;
\c isms
GRANT ALL ON SCHEMA public TO isms_user;
\q
```

### 3. Configure

Create a `.env` file in the project root:

```ini
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DATABASE_URL=postgresql://isms_user:your-strong-password@localhost:5432/isms
```

### 4. Install & Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize Alembic migrations (first time only)
flask db init
flask db migrate -m "initial migration"
flask db upgrade

# Start with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 'app:create_app()'
```

> **Note:** `user` is a reserved word in PostgreSQL. Schema helpers
> quote it as `"user"`. Requires PostgreSQL 14+.

## Docker Deployment

```bash
sudo bash setup.sh --docker
```

This builds and starts all containers (app, PostgreSQL, Redis, Nginx)
via Docker Compose.

## Database Migrations

After modifying SQLAlchemy models:

```bash
source .venv/bin/activate
flask db migrate -m "description of your change"
flask db upgrade
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | Flask secret key (required in production) |
| `DATABASE_URL` | `sqlite:///instance/isms.db` | Database connection string |
| `SESSION_TYPE` | `filesystem` | Session backend |
| `SESSION_REDIS` | — | Redis URL |
| `MAIL_SERVER` | `smtp.gmail.com` | SMTP server |
| `MAIL_PORT` | `587` | SMTP port |
| `MAIL_USE_TLS` | `true` | SMTP TLS |
| `MAIL_USERNAME` | — | SMTP username |
| `MAIL_PASSWORD` | — | SMTP password |
| `MAIL_DEFAULT_SENDER` | `noreply@example.com` | From address |
| `FLASK_ENV` | `development` | `development`, `production`, `testing` |
