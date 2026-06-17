#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════
#  ISO 27001 · NIS2 · GDPR Manager — Production Setup Script
#  Installs to /opt/iso27001-manager with systemd + nginx + SSL
#  Supports: fresh install, app update, Docker or bare-metal
# ═══════════════════════════════════════════════════════════════════════════

# ── Config ─────────────────────────────────────────────────────────────────
APP_NAME="ISO 27001 · NIS2 · GDPR Manager"
INSTALL_DIR="/opt/iso27001-manager"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_MIN="3.12"
GUNICORN_PORT="8000"
GUNICORN_WORKERS="4"
NGINX_UPSTREAM="127.0.0.1:${GUNICORN_PORT}"
SERVICE_USER="www-data"
SERVICE_NAME="iso27001-manager"
DOMAIN=""  # Will prompt later
USE_DOCKER="n"
IS_UPDATE="n"

# ── Colors / Effects ───────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BLUE='\033[0;34m'; MAGENTA='\033[0;35m'; BOLD='\033[1m'; DIM='\033[2m'
NC='\033[0m'

log()    { echo -e "  ${CYAN}◆${NC}  $*"; }
ok()     { echo -e "  ${GREEN}✔${NC}  $*"; }
warn()   { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()    { echo -e "  ${RED}✘${NC}  $*"; }
header() { echo -e "\n${BOLD}${BLUE}━━━ $* ━━━${NC}\n"; }
prompt() { echo -e -n "  ${MAGENTA}›${NC}  $* "; }

# ── Spinner ────────────────────────────────────────────────────────────────
spinner() {
  local pid=$1; local msg=$2; local delay=0.15
  local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
  echo -e -n "  ${DIM}${msg}${NC}  "
  while kill -0 "$pid" 2>/dev/null; do
    for ((i=0; i<${#spin}; i++)); do
      echo -e -n "\b${CYAN}${spin:$i:1}${NC}"
      sleep $delay
    done
  done
  wait "$pid" || { echo -e "\b${RED}✘${NC}"; return 1; }
  echo -e "\b${GREEN}✔${NC}"
}

# ── Banner ─────────────────────────────────────────────────────────────────
banner() {
  echo -e ""
  echo -e "${BOLD}${BLUE}  ╔══════════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}${BLUE}  ║${NC}  ${CYAN}██╗███████╗ ██████╗     ██████╗ ███████╗${BLUE}        ║${NC}"
  echo -e "${BOLD}${BLUE}  ║${NC}  ${CYAN}██║██╔════╝██╔═══██╗    ██╔══██╗██╔════╝${BLUE}        ║${NC}"
  echo -e "${BOLD}${BLUE}  ║${NC}  ${CYAN}██║███████╗██║   ██║    ██║  ██║█████╗  ${BLUE}        ║${NC}"
  echo -e "${BOLD}${BLUE}  ║${NC}  ${CYAN}██║╚════██║██║   ██║    ██║  ██║██╔══╝  ${BLUE}        ║${NC}"
  echo -e "${BOLD}${BLUE}  ║${NC}  ${CYAN}██║███████║╚██████╔╝    ██████╔╝███████╗${BLUE}        ║${NC}"
  echo -e "${BOLD}${BLUE}  ║${NC}  ${CYAN}╚═╝╚══════╝ ╚═════╝     ╚═════╝ ╚══════╝${BLUE}        ║${NC}"
  echo -e "${BOLD}${BLUE}  ║${NC}  ${YELLOW}──────────  N I S 2  ·  G D P R  ──────────${BLUE}  ║${NC}"
  echo -e "${BOLD}${BLUE}  ║${NC}                                              ${BLUE}║${NC}"
  echo -e "${BOLD}${BLUE}  ║  ${NC}${GREEN}${BOLD}  Production Setup Script${NC}                ${BLUE}║${NC}"
  echo -e "${BOLD}${BLUE}  ╚══════════════════════════════════════════════════════╝${NC}"
  echo ""
}

# ── Error handler ──────────────────────────────────────────────────────────
cleanup() {
  echo -e "\n${RED}${BOLD}  ⚡ Setup interrupted or failed.${NC}"
  echo -e "  ${DIM}Fix the issue and re-run the script to continue.${NC}\n"
  exit 1
}
trap cleanup ERR INT TERM

# ── Root check ─────────────────────────────────────────────────────────────
check_root() {
  if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (sudo)."
    echo "  Please re-run: sudo bash setup.sh"
    exit 1
  fi
}

# ── Detect package manager ─────────────────────────────────────────────────
detect_pkg_mgr() {
  if command -v apt-get &>/dev/null; then
    PKG_MGR="apt-get"; PKG_INST="sudo apt-get install -y -qq"
    PKG_UPDATE="sudo apt-get update -qq"
  elif command -v dnf &>/dev/null; then
    PKG_MGR="dnf"; PKG_INST="sudo dnf install -y -q"
    PKG_UPDATE=""
  elif command -v yum &>/dev/null; then
    PKG_MGR="yum"; PKG_INST="sudo yum install -y -q"
    PKG_UPDATE=""
  else
    err "No supported package manager found (apt, dnf, yum)."
    exit 1
  fi
}

# ── Check command exists ───────────────────────────────────────────────────
check_cmd() {
  command -v "$1" &>/dev/null
}

# ── Generate random string ─────────────────────────────────────────────────
gen_secret() {
  openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))"
}

gen_password() {
  openssl rand -base64 12 2>/dev/null | tr -d '+/=' | head -c16 || python3 -c "import secrets; print(secrets.token_urlsafe(12))"
}

# ═══════════════════════════════════════════════════════════════════════════
#  UPDATE MODE
# ═══════════════════════════════════════════════════════════════════════════
do_update() {
  header "UPDATE MODE"

  if [[ ! -d "$INSTALL_DIR" ]]; then
    err "Installation directory $INSTALL_DIR not found."
    echo "  Run setup without --update for a fresh install."
    exit 1
  fi

  cd "$INSTALL_DIR"

  log "Pulling latest code from git…"
  git pull --rebase 2>/dev/null || warn "Git pull failed — check manually"

  log "Upgrading Python packages…"
  source venv/bin/activate
  pip install --upgrade -r requirements.txt -q

  log "Running database migrations…"
  export FLASK_APP=wsgi.py
  flask db upgrade 2>/dev/null || warn "Flask db upgrade skipped (may not need it)"

  log "Ensuring upload directories exist…"
  mkdir -p "$INSTALL_DIR/logs" "$INSTALL_DIR/instance" "$INSTALL_DIR/app/static/uploads/avatars"

  log "Recompiling translations…"
  pybabel compile -d app/translations 2>/dev/null || true

  deactivate

  log "Restarting services…"
  systemctl daemon-reload 2>/dev/null || true
  systemctl restart "$SERVICE_NAME" 2>/dev/null || warn "Could not restart $SERVICE_NAME"
  systemctl reload nginx 2>/dev/null || warn "Could not reload nginx"

  echo ""
  ok "${BOLD}Update complete!${NC} ${DIM}$APP_NAME${NC}"
  echo ""
  exit 0
}

# ═══════════════════════════════════════════════════════════════════════════
#  INSTALL MODE
# ═══════════════════════════════════════════════════════════════════════════

# ── 1. System dependency checks ───────────────────────────────────────────
check_system_deps() {
  header "Checking System Dependencies"

  local missing=0

  log "Python ≥ $PYTHON_MIN…"
  if check_cmd python3; then
    pyver=$(python3 --version 2>&1 | awk '{print $2}')
    if [[ "$(printf '%s\n' "$PYTHON_MIN" "$pyver" | sort -V | head -1)" != "$PYTHON_MIN" ]]; then
      err "Python $PYTHON_MIN+ required, found $pyver"
      missing=1
    else
      ok "Python $pyver"
    fi
  else
    err "Python 3 not found"; missing=1
  fi

  log "python3-venv…"
  if python3 -c "import venv" &>/dev/null; then
    ok "python3-venv available"
  else
    err "python3-venv not available"
    warn "  Install: sudo apt install python3-venv"
    missing=1
  fi

  if [[ "$USE_DOCKER" == "y" ]]; then
    log "Docker…"
    if check_cmd docker; then
      ok "Docker $(docker --version 2>/dev/null | awk '{print $3}' | tr -d ',')"
    else
      err "Docker not found — install Docker first"
      missing=1
    fi

    log "docker compose…"
    if docker compose version &>/dev/null || docker-compose --version &>/dev/null; then
      ok "docker compose available"
    else
      err "docker compose plugin not available"
      missing=1
    fi
  fi

  if [[ "$USE_DOCKER" != "y" ]]; then
    log "PostgreSQL client…"
    if check_cmd psql; then
      ok "psql found"
    else
      warn "PostgreSQL client not found — install postgresql or use SQLite"
    fi

    log "Redis server…"
    if check_cmd redis-server; then
      ok "redis-server found"
    else
      warn "Redis not found — session will use filesystem"
    fi

    log "Nginx…"
    if check_cmd nginx; then
      ok "Nginx found"
    else
      warn "Nginx not found — will install"
    fi
  fi

  if [[ "$missing" == "1" ]]; then
    err "Resolve missing dependencies above, then re-run."
    exit 1
  fi
}

# ── 2. Install missing packages ────────────────────────────────────────────
install_system_packages() {
  header "Installing System Packages"

  if [[ -z "$PKG_MGR" ]]; then
    detect_pkg_mgr
  fi

  local pkgs=()

  case "$PKG_MGR" in
    apt-get)
      pkgs+=(build-essential libpq-dev python3-dev libffi-dev libssl-dev nginx)
      if check_cmd redis-server; then :; else pkgs+=(redis-server); fi
      if check_cmd psql; then :; else pkgs+=(postgresql postgresql-contrib); fi
      pkgs+=(openssl)
      ;;
    dnf|yum)
      pkgs+=(gcc libpq-devel python3-devel openssl-devel nginx postgresql-server postgresql-contrib redis openssl)
      ;;
  esac

  log "Installing: ${pkgs[*]}"
  $PKG_UPDATE 2>/dev/null || true
  $PKG_INST "${pkgs[@]}" &
  spinner $! "Installing system packages…"
  ok "System packages installed"
}

# ── 3. Create install directory and copy files ─────────────────────────────
setup_install_dir() {
  header "Setting Up Installation Directory"

  if [[ -d "$INSTALL_DIR" ]]; then
    warn "Directory $INSTALL_DIR already exists."
    prompt "Overwrite? (existing .env will be kept) [y/N]"
    read -r yn
    if [[ ! "$yn" =~ ^[Yy] ]]; then
      err "Aborted."
      exit 1
    fi
    # Keep .env and venv if they exist
    local keep_env=""
    local keep_venv=""
    [[ -f "$INSTALL_DIR/.env" ]] && keep_env="y" && cp "$INSTALL_DIR/.env" /tmp/_setup_env_backup
    [[ -d "$INSTALL_DIR/venv" ]] && keep_venv="y"
    rm -rf "$INSTALL_DIR"
  fi

  mkdir -p "$INSTALL_DIR"
  log "Copying project files…"
  if command -v rsync &>/dev/null; then
    rsync -a --exclude='venv' --exclude='__pycache__' --exclude='.git' \
          --exclude='*.pyc' --exclude='.env' --exclude='flask_session' \
          "$SRC_DIR/" "$INSTALL_DIR/" &
  else
    cp -a "$SRC_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true
    cp -a "$SRC_DIR"/.[!.]* "$INSTALL_DIR/" 2>/dev/null || true
    rm -rf "$INSTALL_DIR/venv" "$INSTALL_DIR/__pycache__" "$INSTALL_DIR/.git" "$INSTALL_DIR/flask_session" 2>/dev/null || true
  fi
  spinner $! "Copying files to $INSTALL_DIR…"

  mkdir -p "$INSTALL_DIR/logs" "$INSTALL_DIR/instance" "$INSTALL_DIR/app/static/uploads/avatars"
  ok "Files installed to $INSTALL_DIR"

  if [[ "$keep_env" == "y" ]] && [[ -f /tmp/_setup_env_backup ]]; then
    mv /tmp/_setup_env_backup "$INSTALL_DIR/.env"
    log "Kept existing .env"
  fi

  if [[ "$keep_venv" == "y" ]]; then
    # Temporarily move venv back
    warn "Will recreate venv (Python version may differ)"
  fi
}

# ── 4. Configure .env ──────────────────────────────────────────────────────
configure_env() {
  header "Configuring Environment"

  if [[ -f "$INSTALL_DIR/.env" ]] && [[ "$IS_UPDATE" == "y" ]]; then
    log ".env already exists — keeping as-is"
    return
  fi

  cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
  local envfile="$INSTALL_DIR/.env"

  SECRET=$(gen_secret)
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" "$envfile"
  ok "SECRET_KEY generated"

  sed -i "s|^FLASK_ENV=.*|FLASK_ENV=production|" "$envfile"

  if [[ "$USE_DOCKER" == "y" ]]; then
    # Docker mode — use docker-compose defaults
    sed -i "s|^DATABASE_URL=.*|# DATABASE_URL set by docker-compose|" "$envfile"
    sed -i "s|^SESSION_TYPE=.*|SESSION_TYPE=redis|" "$envfile"
    sed -i "s|^# SESSION_REDIS=.*|SESSION_REDIS=redis://redis:6379/0|" "$envfile"
    sed -i "s|^SESSION_TYPE=filesystem|SESSION_TYPE=redis|" "$envfile"
    ok "Configured for Docker (PostgreSQL + Redis from compose)"
  else
    prompt "Database: Use PostgreSQL? [Y/n] "
    read -r use_pg; use_pg="${use_pg:-Y}"

    if [[ "$use_pg" =~ ^[Yy] ]]; then
      prompt "PostgreSQL database name [iso27001]: "
      read -r db_name; db_name="${db_name:-iso27001}"
      prompt "PostgreSQL username [iso27001]: "
      read -r db_user; db_user="${db_user:-iso27001}"
      prompt "PostgreSQL password [auto-generate]: "
      read -r db_pass; db_pass="${db_pass:-$(gen_password)}"

      # Create DB + user
      log "Creating PostgreSQL database and user…"
      sudo -u postgres psql -c "CREATE DATABASE $db_name;" 2>/dev/null || warn "Database '$db_name' already exists"
      sudo -u postgres psql -c "CREATE USER $db_user WITH PASSWORD '$db_pass';" 2>/dev/null || warn "User '$db_user' already exists"
      sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;"
      sudo -u postgres psql -d "$db_name" -c "GRANT ALL ON SCHEMA public TO $db_user;"

      if [[ "$db_pass" == "auto-generate" ]]; then
        # regenerate because the previous one was consumed
        db_pass=$(gen_password)
      fi

      sed -i "s|^# DATABASE_URL=postgresql://.*|DATABASE_URL=postgresql://$db_user:$db_pass@localhost:5432/$db_name|" "$envfile"
      sed -i "s|^DATABASE_URL=sqlite:.*|# DATABASE_URL=sqlite:///../instance/isms.db|" "$envfile"
      ok "PostgreSQL configured"

      # Use Redis if available
      if check_cmd redis-server; then
        prompt "Use Redis for sessions? [Y/n] "
        read -r use_redis; use_redis="${use_redis:-Y}"
        if [[ "$use_redis" =~ ^[Yy] ]]; then
          sed -i "s|^SESSION_TYPE=filesystem|SESSION_TYPE=redis|" "$envfile"
          sed -i "s|^# SESSION_REDIS=.*|SESSION_REDIS=redis://localhost:6379/0|" "$envfile"
          ok "Redis session storage configured"
        fi
      fi
    else
      log "Using SQLite (development mode)"
    fi
  fi

  # Email config
  echo ""
  prompt "Configure SMTP for email notifications? [y/N] "
  read -r use_mail
  if [[ "$use_mail" =~ ^[Yy] ]]; then
    prompt "SMTP server [smtp.gmail.com]: "
    read -r mail_srv; mail_srv="${mail_srv:-smtp.gmail.com}"
    prompt "SMTP port [587]: "
    read -r mail_port; mail_port="${mail_port:-587}"
    prompt "SMTP username: "
    read -r mail_user
    prompt "SMTP password: "
    read -r -s mail_pass; echo ""
    prompt "Default sender [noreply@example.com]: "
    read -r mail_from; mail_from="${mail_from:-noreply@example.com}"

    sed -i "s|^MAIL_SERVER=.*|MAIL_SERVER=$mail_srv|" "$envfile"
    sed -i "s|^MAIL_PORT=.*|MAIL_PORT=$mail_port|" "$envfile"
    sed -i "s|^MAIL_USERNAME=.*|MAIL_USERNAME=$mail_user|" "$envfile"
    sed -i "s|^MAIL_PASSWORD=.*|MAIL_PASSWORD=$mail_pass|" "$envfile"
    sed -i "s|^MAIL_DEFAULT_SENDER=.*|MAIL_DEFAULT_SENDER=$mail_from|" "$envfile"
    ok "SMTP configured"
  fi

  prompt "Admin email [admin@example.com]: "
  read -r admin_email; admin_email="${admin_email:-admin@example.com}"
  sed -i "s|^ADMIN_EMAIL=.*|ADMIN_EMAIL=$admin_email|" "$envfile"
  ok "Admin email set to $admin_email"
}

# ── 5. Python virtual environment + deps ──────────────────────────────────
setup_python_env() {
  header "Python Environment"

  cd "$INSTALL_DIR"

  log "Creating virtual environment…"
  rm -rf venv
  python3 -m venv venv
  source venv/bin/activate

  log "Upgrading pip…"
  pip install --upgrade pip wheel setuptools -q

  log "Installing Python dependencies…"
  pip install -r requirements.txt -q &
  spinner $! "Installing Python packages…"

  ok "Python environment ready"
}

# ── 6. Initialize database + seed ─────────────────────────────────────────
init_database() {
  header "Initializing Database"

  cd "$INSTALL_DIR"
  source venv/bin/activate
  export FLASK_APP=wsgi.py
  export FLASK_ENV=production

  log "Creating database tables and seeding data…"
  # Run a one-off python script to create tables + seed
  python3 -c "
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    db.create_all()
    from app.utils.seed import seed_database
    seed_database()
    print('Database initialized and seeded')
" &
  spinner $! "Initializing and seeding database…"

  ok "Database ready"
}

# ── 7. Generate passwords and set in DB ───────────────────────────────────
generate_passwords() {
  header "Generating User Passwords"

  cd "$INSTALL_DIR"
  source venv/bin/activate
  export FLASK_APP=wsgi.py
  export FLASK_ENV=production

  # Generate unique passwords for each default user
  ADMIN_PW=$(gen_password)
  MANAGER_PW=$(gen_password)
  AUDITOR_PW=$(gen_password)
  USER_PW=$(gen_password)

  export SETUP_PW_admin="$ADMIN_PW"
  export SETUP_PW_manager="$MANAGER_PW"
  export SETUP_PW_auditor="$AUDITOR_PW"
  export SETUP_PW_user="$USER_PW"

  log "Setting passwords in database…"
  python3 -c "
import os
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()
with app.app_context():
    users = User.query.all()
    for u in users:
        env_key = f'SETUP_PW_{u.username}'
        if env_key in os.environ:
            u.password = os.environ[env_key]
            print(f'  Password set for: {u.username}')
    db.session.commit()
    print('All passwords updated')
" &
  spinner $! "Writing passwords to database…"

  ok "Passwords generated and stored (bcrypt hashed)"
}

# ── 8. Compile translations ───────────────────────────────────────────────
compile_translations() {
  header "Compiling Translations"

  cd "$INSTALL_DIR"
  source venv/bin/activate

  if [[ -d "app/translations" ]]; then
    pybabel compile -d app/translations &
    spinner $! "Compiling .po → .mo…"
    ok "Translations compiled"
  fi
}

# ── 9. Create systemd service ─────────────────────────────────────────────
create_systemd_service() {
  header "Creating Systemd Service"

  local svc="/etc/systemd/system/${SERVICE_NAME}.service"

  log "Writing service file…"
  cat > "$svc" <<SERVICEEOF
[Unit]
Description=${APP_NAME}
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=${INSTALL_DIR}/venv/bin/gunicorn wsgi:app \\
    --bind 127.0.0.1:${GUNICORN_PORT} \\
    --workers ${GUNICORN_WORKERS} \\
    --timeout 120 \\
    --access-logfile ${INSTALL_DIR}/logs/access.log \\
    --error-logfile ${INSTALL_DIR}/logs/error.log \\
    --capture-output
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
NoNewPrivileges=true
ProtectSystem=full
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICEEOF

  # Ensure log directory is writable
  mkdir -p "$INSTALL_DIR/logs"
  chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/logs" "$INSTALL_DIR/instance" "$INSTALL_DIR/app/static/uploads"

  systemctl daemon-reload
  ok "Systemd service created at $svc"
}

# ── 10. SSL certificate setup ─────────────────────────────────────────────
setup_ssl() {
  header "SSL / TLS Configuration"

  local ssl_dir="${INSTALL_DIR}/ssl"
  mkdir -p "$ssl_dir"

  if [[ -z "$DOMAIN" ]]; then
    prompt "Enter your domain name (e.g., isms.example.com) or leave empty for IP-address: "
    read -r DOMAIN
  fi

  if [[ -n "$DOMAIN" ]]; then
    echo ""
    log "Domain: $DOMAIN"
    prompt "Do you have SSL certificates? [y/N] "
    read -r has_cert
    if [[ "$has_cert" =~ ^[Yy] ]]; then
      prompt "Path to certificate file (e.g., /path/to/fullchain.pem): "
      read -r cert_path
      prompt "Path to private key file (e.g., /path/to/privkey.pem): "
      read -r key_path

      if [[ -f "$cert_path" ]] && [[ -f "$key_path" ]]; then
        cp "$cert_path" "$ssl_dir/cert.pem"
        cp "$key_path" "$ssl_dir/key.pem"
        chmod 600 "$ssl_dir/key.pem"
        ok "SSL certificates installed"
      else
        warn "Certificate file(s) not found — generating self-signed instead"
        generate_self_signed "$ssl_dir"
      fi
    else
      prompt "Get Let's Encrypt certificate? [y/N] "
      read -r use_le
      if [[ "$use_le" =~ ^[Yy] ]]; then
        if ! check_cmd certbot; then
          log "Installing certbot…"
          case "$PKG_MGR" in
            apt-get) sudo apt-get install -y -qq certbot python3-certbot-nginx ;;
            dnf|yum) sudo "$PKG_MGR" install -y -q certbot python3-certbot-nginx ;;
          esac
        fi
        log "Obtaining Let's Encrypt certificate for $DOMAIN…"
        systemctl start nginx 2>/dev/null || true
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@${DOMAIN}" --redirect &
        spinner $! "Obtaining Let's Encrypt certificate…"
        ok "Let's Encrypt certificate obtained"
        # Certbot already updated nginx config
        if [[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
          cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$ssl_dir/cert.pem"
          cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$ssl_dir/key.pem"
          chmod 600 "$ssl_dir/key.pem"
        fi
      else
        generate_self_signed "$ssl_dir"
      fi
    fi
  else
    generate_self_signed "$ssl_dir"
  fi
}

generate_self_signed() {
  local dir="$1"
  log "Generating self-signed SSL certificate…"
  openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout "$dir/key.pem" \
    -out "$dir/cert.pem" \
    -subj "/C=GR/ST=Attica/L=Athens/O=ISMS/CN=${DOMAIN:-localhost}" 2>/dev/null &
  spinner $! "Generating self-signed certificate…"
  chmod 600 "$dir/key.pem"
  warn "Self-signed certificate generated — browsers will show a warning."
  warn "Replace with a proper certificate for production."
  ok "SSL certificate ready"
}

# ── 11. Create nginx config ───────────────────────────────────────────────
create_nginx_config() {
  header "Configuring Nginx"

  local nginx_conf="/etc/nginx/sites-available/${SERVICE_NAME}.conf"
  local nginx_enabled="/etc/nginx/sites-enabled/${SERVICE_NAME}.conf"

  log "Writing nginx configuration…"

  cat > "$nginx_conf" <<NGINXEOF
# ${APP_NAME} — Nginx Configuration
# Do not edit manually — managed by setup.sh

upstream iso27001-app {
    server ${NGINX_UPSTREAM};
    keepalive 32;
}

# ── HTTP → HTTPS redirect ─────────────────────────────────────────────
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN:-_};

    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}

# ── HTTPS server ───────────────────────────────────────────────────────
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN:-_};

    # SSL
    ssl_certificate     ${INSTALL_DIR}/ssl/cert.pem;
    ssl_certificate_key ${INSTALL_DIR}/ssl/key.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5:!DES:!3DES;
    ssl_prefer_server_ciphers on;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Limits
    client_max_body_size 16M;

    # Logs
    access_log /var/log/nginx/${SERVICE_NAME}_access.log;
    error_log  /var/log/nginx/${SERVICE_NAME}_error.log;

    # ── Static files ────────────────────────────────────────────────
    location /static/ {
        alias ${INSTALL_DIR}/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # ── Uploads ─────────────────────────────────────────────────────
    location /static/uploads/ {
        alias ${INSTALL_DIR}/app/static/uploads/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # ── Health check ────────────────────────────────────────────────
    location /health {
        proxy_pass http://iso27001-app/health;
        access_log off;
    }

    # ── Application proxy ───────────────────────────────────────────
    location / {
        proxy_pass http://iso27001-app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
NGINXEOF

  # Enable site
  rm -f "$nginx_enabled"
  ln -sf "$nginx_conf" "$nginx_enabled"

  # Remove default site if it exists
  [[ -f /etc/nginx/sites-enabled/default ]] && rm -f /etc/nginx/sites-enabled/default

  ok "Nginx configuration written to $nginx_conf"
}

# ── 12. Enable and start services ─────────────────────────────────────────
enable_services() {
  header "Starting Services"

  log "Enabling and starting $SERVICE_NAME…"
  systemctl enable "$SERVICE_NAME"
  systemctl start "$SERVICE_NAME" &
  spinner $! "Starting application service…"
  ok "$SERVICE_NAME service started"

  log "Testing nginx configuration…"
  nginx -t &
  spinner $! "Validating nginx config…"
  ok "Nginx configuration valid"

  log "Starting nginx…"
  systemctl enable nginx 2>/dev/null || true
  systemctl restart nginx &
  spinner $! "Starting nginx…"
  ok "Nginx started"
}

# ── 13. Docker setup ──────────────────────────────────────────────────────
do_docker_setup() {
  header "Docker Deployment"

  cd "$INSTALL_DIR"

  # Generate .env for docker-compose
  if [[ ! -f .env ]]; then
    cp .env.example .env
    SECRET=$(gen_secret)
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" .env
    sed -i "s|^ADMIN_EMAIL=.*|ADMIN_EMAIL=${ADMIN_EMAIL:-admin@example.com}|" .env
    DB_PASS=$(gen_password)
    sed -i "s|changeme|$DB_PASS|g" docker-compose.yml
    ok "Docker .env created with random secrets"
  fi

  # Generate SSL certs for nginx container
  if [[ ! -f nginx/ssl/cert.pem ]]; then
    mkdir -p nginx/ssl
    log "Generating SSL certificate for Docker nginx…"
    openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
      -keyout nginx/ssl/key.pem \
      -out nginx/ssl/cert.pem \
      -subj "/C=GR/ST=Attica/L=Athens/O=ISMS/CN=${DOMAIN:-localhost}" 2>/dev/null
    chmod 600 nginx/ssl/key.pem
    ok "Self-signed SSL certificate generated for Docker"
  fi

  log "Building and starting Docker containers…"
  docker compose up -d --build &
  spinner $! "Building containers (first build may take several minutes)…"
  ok "Docker containers running"

  # Wait for app to be healthy
  log "Waiting for app to be ready…"
  for i in {1..30}; do
    if curl -sf http://localhost:8000/health &>/dev/null; then
      ok "App is healthy"
      break
    fi
    sleep 2
  done

  # Generate passwords inside the Docker container
  log "Setting up admin passwords inside container…"
  ADMIN_PW=$(gen_password)
  MANAGER_PW=$(gen_password)
  AUDITOR_PW=$(gen_password)
  USER_PW=$(gen_password)

  docker compose exec -T app sh -c "
    export SETUP_PW_admin='$ADMIN_PW'
    export SETUP_PW_manager='$MANAGER_PW'
    export SETUP_PW_auditor='$AUDITOR_PW'
    export SETUP_PW_user='$USER_PW'
    python3 -c \"
import os
from app import create_app
from app.extensions import db
from app.models.user import User
app = create_app()
with app.app_context():
    for u in User.query.all():
        env_key = 'SETUP_PW_' + u.username
        if env_key in os.environ:
            u.password = os.environ[env_key]
    db.session.commit()
print('Passwords set in database')
\"
  " &
  spinner $! "Setting passwords in container…"
  ok "Passwords set in database"
}

# ═══════════════════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
show_summary() {
  header "Setup Complete!"

  if [[ "$USE_DOCKER" == "y" ]]; then
    local protocol="https"
    local base_url="${protocol}://${DOMAIN:-localhost}"

    echo -e "  ${GREEN}${BOLD}Application is running via Docker.${NC}"
    echo ""
    echo -e "  ${BOLD}URL:${NC}        ${CYAN}${base_url}${NC}"
    echo -e "  ${BOLD}Health:${NC}     ${CYAN}${base_url}/health${NC}"
    echo ""
    echo -e "  ${YELLOW}Manage containers:${NC}"
    echo -e "    cd ${INSTALL_DIR} && docker compose logs -f"
    echo -e "    docker compose restart app"
    echo -e "    docker compose down"
    echo ""
  else
    local protocol="https"
    local base_url="${protocol}://${DOMAIN:-localhost}"

    echo -e "  ${GREEN}${BOLD}Installation complete!${NC}"
    echo ""
    echo -e "  ${BOLD}Install directory:${NC}  ${INSTALL_DIR}"
    echo -e "  ${BOLD}Systemd service:${NC}   ${SERVICE_NAME}"
    echo -e "  ${BOLD}URL:${NC}              ${CYAN}${base_url}${NC}"
    echo -e "  ${BOLD}Health check:${NC}     ${CYAN}${base_url}/health${NC}"
    echo ""
    echo -e "  ${YELLOW}Useful commands:${NC}"
    echo -e "    sudo systemctl status ${SERVICE_NAME}"
    echo -e "    sudo journalctl -u ${SERVICE_NAME} -f"
    echo -e "    sudo systemctl restart ${SERVICE_NAME}"
    echo -e "    sudo nginx -t && sudo systemctl reload nginx"
    echo ""
  fi

  echo -e "  ${BOLD}${YELLOW}════════════════════════════════════════════════════${NC}"
  echo -e "  ${BOLD}${YELLOW}          DEFAULT USER CREDENTIALS                ${NC}"
  echo -e "  ${BOLD}${YELLOW}════════════════════════════════════════════════════${NC}"
  echo ""
  echo -e "  ${BOLD}Username      Password          Role${NC}"
  echo -e "  ─────────────────────────────────────────────"
  echo -e "  ${CYAN}admin${NC}       ${GREEN}${ADMIN_PW:-Admin@ISO27001!2024}${NC}        ${DIM}Administrator${NC}"
  echo -e "  ${CYAN}manager${NC}     ${GREEN}${MANAGER_PW:-Manager@ISO27001!2024}${NC}        ${DIM}Manager${NC}"
  echo -e "  ${CYAN}auditor${NC}     ${GREEN}${AUDITOR_PW:-Auditor@ISO27001!2024}${NC}        ${DIM}Auditor${NC}"
  echo -e "  ${CYAN}user${NC}        ${GREEN}${USER_PW:-User@ISO27001!2024}${NC}           ${DIM}Regular User${NC}"
  echo ""
  echo -e "  ${RED}${BOLD}⚠  SAVE THESE PASSWORDS — they won't be shown again.${NC}"
  echo ""
  echo -e "  ${DIM}Passwords are hashed with bcrypt and stored in the database.${NC}"
  echo -e "  ${DIM}Change them after first login via Profile → Change Password.${NC}"
  echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
main() {
  banner
  check_root

  # Parse args
  for arg in "$@"; do
    case "$arg" in
      --update|-u) IS_UPDATE="y" ;;
      --docker|-d) USE_DOCKER="y" ;;
      --domain=*) DOMAIN="${arg#*=}" ;;
    esac
  done

  # ―――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
  #  UPDATE PATH
  # ―――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
  if [[ "$IS_UPDATE" == "y" ]]; then
    do_update
    return
  fi

  # ―――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
  #  MODE SELECTION
  # ―――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
  if [[ "$USE_DOCKER" != "y" ]]; then
    echo -e "  ${BOLD}Select deployment mode:${NC}"
    echo -e "    ${CYAN}1${NC})  Local (bare-metal) — PostgreSQL, Redis, Nginx, systemd"
    echo -e "    ${CYAN}2${NC})  Docker Compose — containers for all services"
    echo ""
    prompt "Choice [1/2]: "
    read -r mode_choice

    case "$mode_choice" in
      2|Docker|docker) USE_DOCKER="y" ;;
      *) USE_DOCKER="n" ;;
    esac
  fi

  echo ""
  prompt "Domain name (e.g., isms.example.com) or leave blank for IP: "
  read -r DOMAIN

  echo ""
  prompt "Proceed with installation? [Y/n] "
  read -r proceed; proceed="${proceed:-Y}"
  [[ ! "$proceed" =~ ^[Yy] ]] && { echo -e "  ${YELLOW}Aborted.${NC}"; exit 0; }

  # ―――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
  #  EXECUTION
  # ―――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
  detect_pkg_mgr

  if [[ "$USE_DOCKER" == "y" ]]; then
    check_system_deps
    setup_install_dir
    configure_env
    do_docker_setup
  else
    check_system_deps
    install_system_packages
    setup_install_dir
    configure_env
    setup_python_env
    init_database
    generate_passwords
    compile_translations
    create_systemd_service
    setup_ssl
    create_nginx_config
    enable_services
  fi

  show_summary

  echo -e "  ${GREEN}${BOLD}  ✦  ${APP_NAME} is now running  ✦${NC}"
  echo ""
}

main "$@"
