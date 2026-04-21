# Server Deployment

This repository includes a one-command Ubuntu deployment script for a non-Docker setup.
The server auth model now matches local development: site users, sessions, favorites,
history, and reading progress are stored in a SQLite database instead of a single shared
site password.

## What The Script Does

The script at `scripts/deploy_ubuntu.sh` will:

- install `nginx`, `python3`, `python3-venv`, `pip`, `git`, `curl`, and Node.js 22
- initialize the `jmcomic` submodule
- create a Python virtual environment and install backend dependencies
- build the Vue frontend
- prepare repo-local runtime directories:
  - `backend/data` for persistent SQLite data
  - `backend/data/backups` for manual backups
  - `backend/chapter_cache` for cached chapter files
- migrate a legacy `backend/site_data.db` database into `backend/data/site_data.db`
  on the first rerun after upgrading the script
- write `/etc/comic-backend.env` with `SITE_DB_PATH`
- create a systemd service for the FastAPI backend
- write an Nginx site config that serves the frontend and proxies `/api` to the backend

## Usage

Run this on the Ubuntu server from the repository root:

```bash
sudo bash scripts/deploy_ubuntu.sh --domain comic.example.com
```

If you only have a public IP for now:

```bash
sudo bash scripts/deploy_ubuntu.sh --domain 203.0.113.10
```

## Arguments

- `--domain`: optional, Nginx `server_name`, default `_`
- `--app-user`: optional, Linux user for the backend service, default `comicweb`
- `--api-port`: optional, backend bind port, default `8000`
- `--repo-dir`: optional, repository path, default is the script parent directory
- `--data-dir`: optional, persistent backend data directory inside the repo, default
  `<repo-dir>/backend/data`
- `--password`: deprecated and ignored; kept only so older command lines do not fail

## Runtime Layout

The non-Docker deployment now keeps mutable state inside the repository:

```text
backend/
  data/
    site_data.db
    site_data.db-wal
    site_data.db-shm
    backups/
  chapter_cache/
```

`site_data.db` is the source of truth for the current local account system.
As long as `backend/data` remains in place, re-running the deployment script after
`git pull` will not remove user accounts or reading data.

## Account Model

- `SITE_PASSWORD` is no longer part of the running backend configuration.
- Authentication uses SQLite-backed per-user accounts.
- On a brand-new database, the backend currently seeds a default admin account:
  - username: `admin`
  - password: `wyq666`
- After the first login, use `/admin/users` to create normal users or additional admins.

## Redeploy And Migration Notes

- To redeploy in place, update the repo and rerun the same script:

```bash
git pull
git submodule update --init --recursive
sudo bash scripts/deploy_ubuntu.sh --domain comic.example.com
```

- If an older server deployment still uses `backend/site_data.db`, the updated script
  stops the backend, moves that database into `backend/data/site_data.db`, and then
  starts the service with `SITE_DB_PATH` pointed at the new location.
- If both `backend/site_data.db` and `backend/data/site_data.db` already exist, the
  service uses `backend/data/site_data.db`. Verify which copy is current before you
  delete the legacy file.
- If you move the repository to a new directory or a new machine, copy the whole
  `backend/data` directory into the new repo before the first start.

## Backup And Restore

The backend enables SQLite WAL mode, so the safest manual backup flow is:
stop the backend first, copy the database files, then start the backend again.

### Backup

```bash
cd /path/to/comic-web
sudo systemctl stop comic-backend

STAMP="$(date +%F-%H%M%S)"
sudo mkdir -p "backend/data/backups/${STAMP}"
sudo cp -a backend/data/site_data.db "backend/data/backups/${STAMP}/"

if [ -f backend/data/site_data.db-wal ]; then
  sudo cp -a backend/data/site_data.db-wal "backend/data/backups/${STAMP}/"
fi

if [ -f backend/data/site_data.db-shm ]; then
  sudo cp -a backend/data/site_data.db-shm "backend/data/backups/${STAMP}/"
fi

sudo systemctl start comic-backend
```

### Restore

Replace `2026-04-21-120000` with the backup you want to restore, and replace
`comicweb` if you deployed with a custom `--app-user`.

```bash
cd /path/to/comic-web
sudo systemctl stop comic-backend

BACKUP_DIR="backend/data/backups/2026-04-21-120000"
sudo cp -a "${BACKUP_DIR}/site_data.db" backend/data/site_data.db

if [ -f "${BACKUP_DIR}/site_data.db-wal" ]; then
  sudo cp -a "${BACKUP_DIR}/site_data.db-wal" backend/data/site_data.db-wal
else
  sudo rm -f backend/data/site_data.db-wal
fi

if [ -f "${BACKUP_DIR}/site_data.db-shm" ]; then
  sudo cp -a "${BACKUP_DIR}/site_data.db-shm" backend/data/site_data.db-shm
else
  sudo rm -f backend/data/site_data.db-shm
fi

sudo chown comicweb:comicweb backend/data/site_data.db*
sudo systemctl start comic-backend
```

## Notes

- The backend is started on `127.0.0.1`, so only Nginx is exposed publicly.
- The script prints the effective SQLite path and backup directory at the end.
- If you customize `--data-dir`, it must still stay inside the repository.
