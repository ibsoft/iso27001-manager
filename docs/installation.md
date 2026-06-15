# Installation Guide

## Prerequisites

- **Python** 3.12+
- **PostgreSQL** 16+ (optional — SQLite works for development)
- **Redis** 7+ (optional — filesystem sessions work for development)
- **Node.js** 18+ with npm (optional, for frontend tooling)

## Quick Start (Development)

```bash
# 1. Clone the repository
git clone <repository-url> iso27001-manager
cd iso27001-manager

# 2. Run the automated setup script
chmod +x setup.sh
./setup.sh
```

The script will guide you through optional PostgreSQL and Redis configuration.

## Manual Installation (Development)

### 1. System Dependencies

**Debian / Ubuntu**

```bash
sudo apt-get update
sudo apt-get install -y build-essential libpq-dev python3-dev libffi-dev libssl-dev
```

**Fedora / RHEL**

```bash
sudo dnf install -y gcc libpq-devel python3-devel openssl-devel
```

### 2. Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

### 3. Configuration

```bash
cp .env.example .env
# Edit .env — at minimum, change SECRET_KEY to a random 64-character string:
#   SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

**Using PostgreSQL** (recommended for production):

```bash
# Create the database and user
sudo -u postgres psql
CREATE DATABASE iso27001;
CREATE USER iso27001 WITH PASSWORD 'your-strong-password';
GRANT ALL PRIVILEGES ON DATABASE iso27001 TO iso27001;
\c iso27001
GRANT ALL ON SCHEMA public TO iso27001;
\q

# Update .env
DATABASE_URL=postgresql://iso27001:your-strong-password@localhost:5432/iso27001
```

**Using Redis** (recommended for production session storage):

```bash
# Install Redis (Debian/Ubuntu)
sudo apt-get install -y redis-server
sudo systemctl enable --now redis-server

# Update .env
SESSION_TYPE=redis
SESSION_REDIS=redis://localhost:6379/0
```

### 4. Initialize the Database

```bash
source venv/bin/activate
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()
```

### 5. Seed Initial Data

```bash
source venv/bin/activate
flask shell
>>> from seed_data.seed import seed_all
>>> seed_all()
>>> exit()
```

### 6. Compile Translations

```bash
source venv/bin/activate
pybabel compile -d translations
```

### 7. Run

```bash
# Development (Flask built-in server)
flask run

# Production (Gunicorn)
gunicorn wsgi:app --bind 0.0.0.0:8000 --workers 4 --timeout 120 \
  --access-logfile - --error-logfile -
```

The app will be available at http://localhost:5000 (dev) or http://localhost:8000 (production).

Default credentials after seeding: `admin@example.com` / `Admin123!`

## Docker Deployment

### Prerequisites

- Docker 24+
- Docker Compose v2+

### Quick Start

```bash
# 1. Clone the repository
git clone <repository-url> iso27001-manager
cd iso27001-manager

# 2. Create .env with your secrets
cp .env.example .env
# Edit SECRET_KEY and DB_PASSWORD

# 3. Start the stack
export DB_PASSWORD=your-strong-password
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
docker compose up -d

# 4. Initialize and seed the database
docker compose exec app flask shell
>>> from app import db
>>> db.create_all()
>>> from seed_data.seed import seed_all
>>> seed_all()
>>> exit()

# 5. Compile translations
docker compose exec app pybabel compile -d translations
```

The app will be available at http://localhost:80 (HTTP redirects to HTTPS by default) and https://localhost:443.

### SSL Certificates

Place your SSL certificate and key at:

```
nginx/ssl/cert.pem
nginx/ssl/key.pem
```

For development, you can generate self-signed certificates:

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/CN=localhost"
```

### Production Docker

```bash
# Use a strong DB password and secure SECRET_KEY
export DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export MAIL_SERVER=smtp.your-provider.com
export MAIL_USERNAME=your-email@example.com
export MAIL_PASSWORD=your-mail-password
export MAIL_DEFAULT_SENDER=noreply@your-domain.com
export ADMIN_EMAIL=admin@your-domain.com

docker compose up -d
```

### Managing the Stack

```bash
# View logs
docker compose logs -f

# Stop
docker compose down

# Stop and remove volumes (destroys all data)
docker compose down -v

# Rebuild the app image after code changes
docker compose build app
docker compose up -d
```

## Architecture

```
┌──────────────┐      ┌───────────────┐      ┌──────────────┐
│   Nginx      │ ───► │  Gunicorn     │ ───► │  Flask App   │
│   (reverse   │      │  (WSGI)       │      │  (Python)    │
│    proxy)    │      │               │      │              │
└──────────────┘      └───────┬───────┘      └──────┬───────┘
                              │                     │
                              ▼                     ▼
                       ┌──────────────┐     ┌──────────────┐
                       │   Redis      │     │  PostgreSQL  │
                       │   (session)  │     │  (database)  │
                       └──────────────┘     └──────────────┘
```

## Directory Structure

```
iso27001-manager/
├── app/                  # Flask application package
│   ├── models/           # SQLAlchemy models
│   ├── routes/           # Route handlers (blueprints)
│   ├── templates/        # Jinja2 templates
│   ├── static/           # CSS, JS, images
│   └── forms/            # WTForms form classes
├── migrations/           # Alembic database migrations
├── seed_data/            # JSON seed files and loader
├── translations/         # Babel translation catalogs
├── nginx/                # Nginx configuration
├── docs/                 # Documentation
├── config.py             # Application configuration
├── wsgi.py               # WSGI entry point
├── run.py                # Development entry point
├── Dockerfile            # Docker image build
├── docker-compose.yml    # Docker Compose stack
└── setup.sh              # Bare-metal setup script
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | Flask secret key (set to a random 64+ char string) |
| `DATABASE_URL` | `sqlite:///instance/isms.db` | Database connection string |
| `SESSION_TYPE` | `filesystem` | Session backend (`filesystem`, `redis`) |
| `SESSION_REDIS` | — | Redis URL (required when `SESSION_TYPE=redis`) |
| `MAIL_SERVER` | `smtp.gmail.com` | SMTP server |
| `MAIL_PORT` | `587` | SMTP port |
| `MAIL_USE_TLS` | `true` | Enable TLS for SMTP |
| `MAIL_USERNAME` | — | SMTP username |
| `MAIL_PASSWORD` | — | SMTP password |
| `MAIL_DEFAULT_SENDER` | `noreply@example.com` | Default from address |
| `TOTP_ISSUER_NAME` | `ISO27001-Manager` | TOTP issuer label |
| `ADMIN_EMAIL` | `admin@example.com` | Admin email for notifications |
| `FLASK_ENV` | `development` | `development`, `production`, or `testing` |

## Default Credentials

After seeding, the following account is created:

- **Email:** `admin@example.com`
- **Password:** `Admin123!`

**Change this password immediately after first login.**
