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
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# The database lives outside /app/data so it cannot pollute the preserved sample
# fixtures, which are checksum-protected and mounted read-only.
ENV COMMERCE_DB_PATH=/app/var/commerce.sqlite3
RUN mkdir -p /app/var

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
