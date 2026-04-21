# Comic Web Backlog

This file tracks the next features and engineering work for the current project.

## P0

- Persist local site user data in Docker and server deployments.
  Status: Done on 2026-04-21. Docker and Ubuntu now keep the SQLite site data in `backend/data/site_data.db`, and the Ubuntu deploy script migrates legacy `backend/site_data.db` on the first rerun.
- Update non-Docker deployment docs and scripts to match the new local account system.
  Status: Done on 2026-04-21. `scripts/deploy_ubuntu.sh` and `README-Server.md` now use the per-user SQLite account model, `SITE_DB_PATH`, and documented backup / restore steps.
- Improve admin user management.
  Status: Done on 2026-04-21. Admins can now create users, enable/disable users, grant/revoke admin, reset passwords, and users can change their own password from settings.
- Add comment list support.
  Status: Done on 2026-04-21. The project now has site-local comment list, posting, replying, deleting, and pagination support on the comic detail page.

## P1

- Double-page reader mode.
- Infinite scrolling for list pages.
- Reader loading indicator in page mode.
- Chapter search inside the reader drawer.
- Keyboard support in scroll mode.
- Auto page turning / auto scrolling.
- Better resume-reading actions in favorites and history.
- Error message classification for API failures.

## P2

- Cache quota management and cleanup policy.
- Import / export user data.
- PWA / offline support.
- Personal profile page.
- Operation logs for admin actions.
- Automated tests and CI for auth, favorites, history, and reading progress.

## Technical Debt

- Replace the obsolete `version` field in `docker-compose.yml`.
- Review UTF-8 / Chinese text rendering consistency in docs and UI copy.
- Automate backup rotation for `backend/data/site_data.db`.
