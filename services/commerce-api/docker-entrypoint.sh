#!/bin/sh
# Prepare the database, then exec the real command.
#
# Migrations and seeding run here rather than in a separate one-shot container so a
# plain `docker compose up` yields a working store. Both steps are idempotent, so a
# restart neither fails nor duplicates data.
set -e

# Configuration first. A blank or development SESSION_SECRET is a PERMANENT error: no
# amount of waiting fixes it, and letting the database wait loop absorb it would hide the
# real cause behind sixty seconds of "waiting for database".
if ! python manage.py check-config; then
  echo "[entrypoint] configuration is invalid; refusing to start"
  exit 1
fi

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

# Seeding is OPT-OUT for development and OFF for staging. Default 1 preserves the
# existing development behaviour byte-for-byte; staging sets 0. The administrator is
# NEVER created here - it is a manual, credential-bearing step (manage.py create-admin).
if [ "${SEED_DEMO_DATA:-1}" = "1" ]; then
  echo "[entrypoint] seeding fictional demo dataset (idempotent)"
  python manage.py seed
else
  echo "[entrypoint] SEED_DEMO_DATA=0 -> skipping demo seed; no demo customer, admin, product or order is created"
fi

echo "[entrypoint] starting: $*"
# exec so the server becomes PID 1 and receives SIGTERM directly; otherwise the shell
# swallows the signal and Docker has to kill the container on timeout.
exec "$@"
