#!/bin/sh
# Prepare the database, then exec the real command.
#
# Migrations and seeding run here rather than in a separate one-shot container so a
# plain `docker compose up` yields a working store. Both steps are idempotent, so a
# restart neither fails nor duplicates data.
set -e

echo "[entrypoint] applying migrations"
python -m alembic upgrade head

echo "[entrypoint] seeding fictional MERET dataset (idempotent)"
python manage.py seed

echo "[entrypoint] starting: $*"
# exec so the server becomes PID 1 and receives SIGTERM directly; otherwise the shell
# swallows the signal and Docker has to kill the container on timeout.
exec "$@"
