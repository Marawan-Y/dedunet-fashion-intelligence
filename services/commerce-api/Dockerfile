# Build context is the REPOSITORY ROOT, not services/commerce-api.
#
# It has to be. The media route serves `packages/brand/assets`, and a context rooted at
# this service could never reach that directory — which is why every brand and product
# media URL returned 404 in every containerised deployment while passing on a checkout.
# `Dockerfile.dockerignore` narrows the widened context back down to an allowlist, so the
# build sees this service, the normalized brand package, and nothing else.
#
#   docker build -f services/commerce-api/Dockerfile -t commerce-api .

# ---- stage 1: verify the normalized brand package before it is allowed into the image --
# A separate stage so the manifests and the verifier never reach the runtime image, and so
# a missing or rewritten asset FAILS THE BUILD. The alternative is what happened before:
# an image that builds, starts, reports ready, and serves no brand at all.
FROM python:3.12-slim AS brand-assets
WORKDIR /brand
COPY packages/brand/assets ./assets
COPY packages/brand/assets.json packages/brand/product-media.json ./
COPY scripts/brand/verify_packaged_assets.py ./verify_packaged_assets.py
RUN python verify_packaged_assets.py \
      --root /brand/assets \
      --assets /brand/assets.json \
      --media /brand/product-media.json

# ---- stage 2: runtime ------------------------------------------------------------------
FROM python:3.12-slim
WORKDIR /app

COPY services/commerce-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/commerce-api/app ./app
COPY services/commerce-api/data ./data
# Migrations and the management CLI are needed at RUNTIME: the entrypoint applies
# migrations and seeds before serving. Omitting them produces a container that starts
# and then fails on the first database query.
COPY services/commerce-api/migrations ./migrations
COPY services/commerce-api/alembic.ini services/commerce-api/manage.py ./
# The notification worker runs from this same image as a SEPARATE container, so the
# API and the dispatcher can never drift apart in version.
COPY services/commerce-api/notification_worker.py ./
COPY services/commerce-api/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# The verified assets, and only the assets. Copied from the stage that checked them, so
# the bytes in this image are the bytes the manifest attests to.
COPY --from=brand-assets /brand/assets ./brand-assets
# Explicit, not inferred from __file__. The old code computed the root from the source
# file's location, which silently assumed a repository checkout and resolved to
# /packages/brand/assets — outside /app, and absent.
ENV BRAND_MEDIA_ROOT=/app/brand-assets

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
