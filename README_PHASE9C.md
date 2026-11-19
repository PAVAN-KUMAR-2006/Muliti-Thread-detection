# Sentinel Phase 9C
New: GET /api/models/performance, notifications API (list / mark read / read all), notification bell, /model-performance page,
pytest suite (backend/tests), cleanup of duplicate model/config/requirements lines, duplicate 0002 migration moved to backend/alembic/retired.
No database migration is needed. Existing models are not retrained or replaced.

Run the tests (throwaway SQLite database; refuses to run against anything else):
  docker compose exec backend sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q"
