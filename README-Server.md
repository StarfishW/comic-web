# Server Deployment

This repository includes a one-command Ubuntu deployment script for a non-Docker setup.

## What It Does

The script at `scripts/deploy_ubuntu.sh` will:

- install `nginx`, `python3`, `python3-venv`, `pip`, `git`, `curl`, and Node.js 22
- initialize the `jmcomic` submodule
- create a Python virtual environment and install backend dependencies
- build the Vue frontend
- create a systemd service for the FastAPI backend
- write an Nginx site config that serves the frontend and proxies `/api` to the backend

## Usage

Run this on the Ubuntu server from the repository root:

```bash
sudo bash scripts/deploy_ubuntu.sh --password 'change-me' --domain comic.example.com
```

If you only have a public IP for now:

```bash
sudo bash scripts/deploy_ubuntu.sh --password 'change-me' --domain 203.0.113.10
```

## Arguments

- `--password`: required, sets the backend login password
- `--domain`: optional, Nginx `server_name`, default `_`
- `--app-user`: optional, Linux user for the backend service, default `comicweb`
- `--api-port`: optional, backend bind port, default `8000`
- `--repo-dir`: optional, repository path, default is the script parent directory

## Notes

- The backend now supports `SITE_PASSWORD` from the environment and falls back to the old hardcoded value only if unset.
- The backend is started on `127.0.0.1`, so only Nginx is exposed publicly.
- Re-run the same script after `git pull` to update the server in place.
