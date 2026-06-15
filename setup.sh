#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="ISO 27001 Manager"
PYTHON_MIN="3.12"

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Pre-checks ──────────────────────────────────────────────────────────────
check_python() {
    if command -v python3 &>/dev/null; then
        PY=$(python3 --version 2>&1 | awk '{print $2}')
    else
        err "Python 3 not found. Install Python $PYTHON_MIN+ first."
        exit 1
    fi
    if [[ "$(printf '%s\n' "$PYTHON_MIN" "$PY" | sort -V | head -1)" != "$PYTHON_MIN" ]]; then
        err "Python $PYTHON_MIN+ required, found $PY."
        exit 1
    fi
    ok "Python $PY found"
}

check_distro() {
    if command -v apt-get &>/dev/null; then
        PKG_MGR="apt-get"
        DPKG_OPTS="-qq"
    elif command -v dnf &>/dev/null; then
        PKG_MGR="dnf"
        DPKG_OPTS="-q"
    elif command -v yum &>/dev/null; then
        PKG_MGR="yum"
        DPKG_OPTS="-q"
    else
        warn "No known package manager found; you may need to install dependencies manually."
        PKG_MGR=""
    fi
}

# ── Install system deps ─────────────────────────────────────────────────────
install_system_deps() {
    log "Installing system dependencies …"
    case "$PKG_MGR" in
        apt-get)
            sudo apt-get update $DPKG_OPTS
            sudo apt-get install -y $DPKG_OPTS \
                build-essential libpq-dev python3-dev libffi-dev libssl-dev
            ;;
        dnf|yum)
            sudo "$PKG_MGR" install -y $DPKG_OPTS \
                gcc libpq-devel python3-devel openssl-devel
            ;;
    esac
    ok "System dependencies installed"
}

# ── Python virtual env ──────────────────────────────────────────────────────
setup_venv() {
    if [[ -d "$APP_DIR/venv" ]]; then
        warn "Virtual environment already exists at $APP_DIR/venv"
        read -rp "Recreate it? [y/N] " yn
        if [[ "$yn" =~ ^[Yy] ]]; then
            rm -rf "$APP_DIR/venv"
        else
            log "Skipping venv creation"
            return
        fi
    fi
    python3 -m venv "$APP_DIR/venv"
    ok "Virtual environment created at $APP_DIR/venv"
}

install_python_deps() {
    log "Installing Python dependencies …"
    "$APP_DIR/venv/bin/pip" install --upgrade pip wheel setuptools
    "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
    ok "Python dependencies installed"
}

# ── PostgreSQL setup (optional) ─────────────────────────────────────────────
setup_postgres() {
    if ! command -v psql &>/dev/null; then
        warn "PostgreSQL client (psql) not found. Skipping database setup."
        warn "The app will use SQLite by default — fine for development."
        return
    fi
    log "Configuring PostgreSQL database …"
    read -rp "PostgreSQL database name [iso27001]: " DB_NAME
    DB_NAME="${DB_NAME:-iso27001}"
    read -rp "PostgreSQL username [iso27001]: " DB_USER
    DB_USER="${DB_USER:-iso27001}"
    read -rsp "PostgreSQL password [iso27001]: " DB_PASS
    echo
    DB_PASS="${DB_PASS:-iso27001}"

    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || warn "Database '$DB_NAME' already exists"
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || warn "User '$DB_USER' already exists"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;"

    sed -i "s|^# DATABASE_URL=postgresql://.*|DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME|" "$APP_DIR/.env"
    ok "PostgreSQL configured"
}

# ── Redis setup (optional) ──────────────────────────────────────────────────
setup_redis() {
    if ! command -v redis-server &>/dev/null; then
        warn "Redis not found. Session storage will use filesystem (fine for dev)."
        return
    fi
    log "Enabling Redis session storage …"
    sed -i 's|^SESSION_TYPE=.*|SESSION_TYPE=redis|' "$APP_DIR/.env"
    sed -i 's|^# SESSION_REDIS=.*|SESSION_REDIS=redis://localhost:6379/0|' "$APP_DIR/.env"
    ok "Redis session storage configured"
}

# ── Environment configuration ───────────────────────────────────────────────
configure_env() {
    if [[ ! -f "$APP_DIR/.env" ]]; then
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        log "Created .env from .env.example"
    else
        warn ".env already exists — keeping existing values"
    fi

    if grep -q "change-this-to-a-random-secret" "$APP_DIR/.env" 2>/dev/null; then
        SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" "$APP_DIR/.env"
        ok "Generated random SECRET_KEY"
    fi
}

# ── Database initialization & seeding ───────────────────────────────────────
init_db() {
    log "Initializing database …"
    "$APP_DIR/venv/bin/python" -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Tables created')
"
    ok "Database tables created"
}

seed_db() {
    log "Seeding database with initial data …"
    "$APP_DIR/venv/bin/python" -c "
from app import create_app, db
from seed_data.seed import seed_all
app = create_app()
with app.app_context():
    seed_all()
    print('Seed data loaded')
"
    ok "Seed data loaded"
}

# ── Babel / translations ────────────────────────────────────────────────────
compile_translations() {
    if [[ -d "$APP_DIR/translations" ]]; then
        log "Compiling translations …"
        "$APP_DIR/venv/bin/pybabel" compile -d "$APP_DIR/translations" 2>/dev/null || true
        ok "Translations compiled"
    fi
}

# ── Run application ─────────────────────────────────────────────────────────
start_app() {
    echo
    echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║   $APP_NAME setup complete!        ║${NC}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "  Start the development server:"
    echo -e "    ${CYAN}source venv/bin/activate${NC}"
    echo -e "    ${CYAN}flask run${NC}"
    echo
    echo -e "  Or with gunicorn (production):"
    echo -e "    ${CYAN}venv/bin/gunicorn wsgi:app --bind 0.0.0.0:8000 --workers 4${NC}"
    echo
    echo -e "  Default admin credentials (after seeding):"
    echo -e "    ${YELLOW}Email:    admin@example.com${NC}"
    echo -e "    ${YELLOW}Password: Admin123!${NC}"
    echo
    echo -e "  Make sure to ${BOLD}change the admin password${NC} on first login!"
    echo
}

# ── Main ────────────────────────────────────────────────────────────────────
main() {
    echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   $APP_NAME — Setup Script       ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
    echo

    check_python
    check_distro

    echo
    echo -e "${YELLOW}This script will:${NC}"
    echo "  1. Install system build dependencies"
    echo "  2. Create a Python virtual environment"
    echo "  3. Install Python packages"
    echo "  4. Configure .env (optional: PostgreSQL, Redis)"
    echo "  5. Create database tables"
    echo "  6. Seed initial data"
    echo "  7. Compile translations"
    echo
    read -rp "Continue? [Y/n] " yn
    [[ "$yn" =~ ^[Nn] ]] && { echo "Aborted."; exit 0; }

    install_system_deps
    setup_venv
    install_python_deps
    configure_env

    echo
    read -rp "Set up PostgreSQL? [y/N] " yn
    [[ "$yn" =~ ^[Yy] ]] && setup_postgres

    read -rp "Set up Redis? [y/N] " yn
    [[ "$yn" =~ ^[Yy] ]] && setup_redis

    init_db
    seed_db
    compile_translations
    start_app
}

main "$@"
