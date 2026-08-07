FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data
# Migrations and the management CLI are needed at RUNTIME: the entrypoint applies
# migrations and seeds before serving. Omitting them produces a container that starts
# and then fails on the first database query.
COPY migrations ./migrations
COPY alembic.ini manage.py ./
# The notification worker runs from this same image as a SEPARATE container, so the
# API and the dispatcher can never drift apart in version.
COPY notification_worker.py ./
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# The database lives outside /app/data so it cannot pollute the preserved sample
# fixtures, which are checksum-protected and mounted read-only.
ENV COMMERCE_DB_PATH=/app/var/commerce.sqlite3
RUN mkdir -p /app/var

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# app.server, NOT the bare `uvicorn` CLI. uvicorn defaults to proxy_headers=True with
# forwarded_allow_ips="127.0.0.1", so the bare CLI lets any loopback client set its own
# address via X-Forwarded-For and mint a fresh rate-limit bucket per request. app.server
# states proxy trust explicitly and defaults to interpreting no forwarded header at all.
CMD ["python", "-m", "app.server", "--host", "0.0.0.0", "--port", "8000"]
