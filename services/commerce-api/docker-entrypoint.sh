#!/bin/sh
# Prepare the database, then exec the real command.
#
# Migrations and seeding run here rather than in a separate one-shot container so a
# plain `docker compose up` yields a working store. Both steps are idempotent, so a
# restart neither fails nor duplicates data.
set -e

# Wait for the database before touching it. depends_on: service_healthy alone does not
# close this race: pg_isready can succeed against the temporary server initdb starts
# during first-boot bootstrap, after which the real server restarts and the port briefly
# drops. Reuses manage.py check, which is engine-agnostic and never prints the URL.
attempts=0
max_attempts="${DB_WAIT_ATTEMPTS:-30}"
until python manage.py check >/dev/null 2>&1; do
  attempts=$((attempts + 1))
  if [ "$attempts" -ge "$max_attempts" ]; then
    echo "[entrypoint] database unreachable after ${max_attempts} attempts; refusing to start"
    python manage.py check   # run once more, unsuppressed, so the reason is in the log
    exit 1
  fi
  echo "[entrypoint] waiting for database (attempt ${attempts}/${max_attempts})"
  sleep 2
done
echo "[entrypoint] database reachable"

echo "[entrypoint] applying migrations"
python -m alembic upgrade head

echo "[entrypoint] seeding fictional MERET dataset (idempotent)"
python manage.py seed

echo "[entrypoint] starting: $*"
# exec so the server becomes PID 1 and receives SIGTERM directly; otherwise the shell
# swallows the signal and Docker has to kill the container on timeout.
exec "$@"
