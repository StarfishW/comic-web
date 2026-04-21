#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

APP_USER="comicweb"
DOMAIN="_"
API_PORT="8000"
DATA_DIR=""
DEPRECATED_SITE_PASSWORD=""
SERVICE_NAME="comic-backend"
NGINX_SITE_NAME="comic-web"

usage() {
  cat <<EOF
Usage:
  sudo bash scripts/deploy_ubuntu.sh [options]

Options:
  --domain <value>     Domain or server IP for Nginx server_name. Default: _
  --app-user <value>   Linux user for the backend service. Default: comicweb
  --api-port <value>   Local backend port. Default: 8000
  --repo-dir <value>   Repository path on the server. Default: script parent dir
  --data-dir <value>   Persistent backend data directory inside the repo.
                       Default: <repo-dir>/backend/data
  --password <value>   Deprecated. Ignored. Auth now uses SQLite user accounts.
  --help               Show this message

Examples:
  sudo bash scripts/deploy_ubuntu.sh --domain comic.example.com
  sudo bash scripts/deploy_ubuntu.sh --domain 203.0.113.10
  sudo bash scripts/deploy_ubuntu.sh --domain comic.example.com --data-dir backend/data
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="${2:-}"
      shift 2
      ;;
    --app-user)
      APP_USER="${2:-}"
      shift 2
      ;;
    --api-port)
      API_PORT="${2:-}"
      shift 2
      ;;
    --repo-dir)
      REPO_DIR="${2:-}"
      shift 2
      ;;
    --data-dir)
      DATA_DIR="${2:-}"
      shift 2
      ;;
    --password)
      DEPRECATED_SITE_PASSWORD="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run this script with sudo or as root." >&2
  exit 1
fi

REPO_DIR="$(realpath -m "${REPO_DIR}")"

if [[ -z "${DATA_DIR}" ]]; then
  DATA_DIR="${REPO_DIR}/backend/data"
elif [[ "${DATA_DIR}" != /* ]]; then
  DATA_DIR="${REPO_DIR}/${DATA_DIR}"
fi

DATA_DIR="$(realpath -m "${DATA_DIR}")"

if [[ ! -d "${REPO_DIR}" ]]; then
  echo "Repository directory does not exist: ${REPO_DIR}" >&2
  exit 1
fi

if [[ ! -f "${REPO_DIR}/backend/main.py" ]]; then
  echo "Repository directory looks wrong: ${REPO_DIR}" >&2
  exit 1
fi

case "${DATA_DIR}" in
  "${REPO_DIR}"/*) ;;
  *)
    echo "--data-dir must stay inside the repository: ${REPO_DIR}" >&2
    exit 1
    ;;
esac

SITE_DB_PATH="${DATA_DIR}/site_data.db"
LEGACY_DB_PATH="${REPO_DIR}/backend/site_data.db"
CACHE_DIR="${REPO_DIR}/backend/chapter_cache"
BACKUP_DIR="${DATA_DIR}/backups"

stop_existing_service() {
  if systemctl cat "${SERVICE_NAME}" >/dev/null 2>&1; then
    systemctl stop "${SERVICE_NAME}" || true
  else
    echo "No existing ${SERVICE_NAME} service found"
  fi
}

migrate_legacy_site_db() {
  if [[ -f "${SITE_DB_PATH}" ]]; then
    echo "Persistent SQLite database already exists at ${SITE_DB_PATH}"
    if [[ -f "${LEGACY_DB_PATH}" ]]; then
      echo "Warning: legacy SQLite database still exists at ${LEGACY_DB_PATH}"
      echo "Current service will keep using ${SITE_DB_PATH}; review the legacy copy manually."
    fi
    return
  fi

  if [[ -f "${LEGACY_DB_PATH}" ]]; then
    echo "Migrating legacy SQLite database to ${SITE_DB_PATH}"
    mv "${LEGACY_DB_PATH}" "${SITE_DB_PATH}"
    if [[ -f "${LEGACY_DB_PATH}-wal" ]]; then
      mv "${LEGACY_DB_PATH}-wal" "${SITE_DB_PATH}-wal"
    fi
    if [[ -f "${LEGACY_DB_PATH}-shm" ]]; then
      mv "${LEGACY_DB_PATH}-shm" "${SITE_DB_PATH}-shm"
    fi
  fi
}

if [[ -n "${DEPRECATED_SITE_PASSWORD}" ]]; then
  echo "Warning: --password is ignored. Auth now uses per-user SQLite accounts."
fi

echo "[1/10] Installing system packages"
apt-get update
apt-get install -y git nginx python3 python3-venv python3-pip curl ca-certificates

if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | sed 's/^v//; s/\..*$//')" != "22" ]]; then
  echo "[2/10] Installing Node.js 22"
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
else
  echo "[2/10] Node.js 22 already installed"
fi

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  echo "[3/10] Creating service user ${APP_USER}"
  useradd --system --create-home --shell /usr/sbin/nologin "${APP_USER}"
else
  echo "[3/10] Service user ${APP_USER} already exists"
fi

echo "[4/10] Syncing git submodules"
git -C "${REPO_DIR}" submodule update --init --recursive

echo "[5/10] Installing Python dependencies"
python3 -m venv "${REPO_DIR}/venv"
"${REPO_DIR}/venv/bin/pip" install --upgrade pip
"${REPO_DIR}/venv/bin/pip" install -e "${REPO_DIR}/jmcomic"
"${REPO_DIR}/venv/bin/pip" install -r "${REPO_DIR}/backend/requirements.txt"
"${REPO_DIR}/venv/bin/pip" install img2pdf

echo "[6/10] Building frontend"
npm --prefix "${REPO_DIR}/frontend" ci
npm --prefix "${REPO_DIR}/frontend" run build

echo "[7/10] Stopping existing backend service"
stop_existing_service

echo "[8/10] Preparing runtime directories"
mkdir -p "${CACHE_DIR}" "${DATA_DIR}" "${BACKUP_DIR}"
migrate_legacy_site_db
chown -R "${APP_USER}:${APP_USER}" "${CACHE_DIR}" "${DATA_DIR}"

cat >/etc/${SERVICE_NAME}.env <<EOF
SITE_DB_PATH=${SITE_DB_PATH}
PYTHONUNBUFFERED=1
EOF
chmod 600 /etc/${SERVICE_NAME}.env

echo "[9/10] Writing service and Nginx config"
cat >/etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Comic Web Backend
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${REPO_DIR}/backend
EnvironmentFile=/etc/${SERVICE_NAME}.env
ExecStart=${REPO_DIR}/venv/bin/uvicorn main:app --host 127.0.0.1 --port ${API_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/nginx/sites-available/${NGINX_SITE_NAME} <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    root ${REPO_DIR}/frontend/dist;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:${API_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

ln -sfn /etc/nginx/sites-available/${NGINX_SITE_NAME} /etc/nginx/sites-enabled/${NGINX_SITE_NAME}
rm -f /etc/nginx/sites-enabled/default

echo "[10/10] Starting services"
systemctl daemon-reload
systemctl enable --now ${SERVICE_NAME}
nginx -t
systemctl reload nginx
systemctl enable nginx

echo
echo "Deployment complete."
echo "Frontend: http://${DOMAIN}"
echo "API docs: http://${DOMAIN}/api/docs"
echo "SQLite DB: ${SITE_DB_PATH}"
echo "Backup directory: ${BACKUP_DIR}"
echo
echo "Auth notes:"
echo "  - This deployment uses per-user SQLite accounts, not a single SITE_PASSWORD."
echo "  - A brand-new database is seeded by the backend with admin / wyq666."
echo
echo "Useful commands:"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
echo "  sudo systemctl reload nginx"
