# Comic Web Backlog

This file tracks the next features and engineering work for the current project.

## P0

- Persist local site user data in Docker and server deployments.
  Status: Docker bind mount for `backend/site_data.db` is done. Ubuntu deploy script still needs to be updated to keep the database across redeploys.
- Update non-Docker deployment docs and scripts to match the new local account system.
  Scope: `scripts/deploy_ubuntu.sh`, `README-Server.md`.
- Improve admin user management.
  Scope: delete user, disable user, reset password, self-service password change.
- Add comment list support.
  Scope: backend `GET /api/comments`, frontend comment panel, pagination.

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
- Add backup / restore guidance for `backend/site_data.db`.
