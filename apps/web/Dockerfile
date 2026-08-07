FROM nginx:1.27-alpine

# Build context is the PoC root (see docker-compose.yml) so both browser clients ship in
# one image and share an origin. That matters: they call the API cross-origin already,
# and splitting them across two origins would need a second CORS entry for no benefit.
COPY apps/web   /usr/share/nginx/html/storefront
COPY apps/admin /usr/share/nginx/html/admin
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

# Where the API lives, baked in at BUILD time.
#
# Not at run time: this container runs with a read-only root filesystem, so nothing may
# write into the served directory after start. Baking it in preserves that and makes the
# image self-describing. Empty means "use the client's default", which is the page host on
# the development API port — correct for docker-compose.yml, wrong for staging, whose API
# is published on 18080.
ARG API_BASE_URL=""
RUN if [ -n "$API_BASE_URL" ]; then \
      printf '/* generated at build time from API_BASE_URL */\nwindow.DEDUNET_API_BASE = "%s";\n' \
        "$API_BASE_URL" > /usr/share/nginx/html/storefront/config.js; \
      echo "storefront API base: $API_BASE_URL"; \
    else \
      echo "storefront API base: client default (page host on port 18000)"; \
    fi
