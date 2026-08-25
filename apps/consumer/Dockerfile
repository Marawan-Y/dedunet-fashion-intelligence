# DEDUNET consumer web application — multi-stage.
#
# THE RUNTIME SECURITY POSTURE IS UNCHANGED FROM THE CLASSIC CLIENT.
#
# ADR-0003 argued that no build stage could be added "without changing the container's
# security posture". That premise is wrong, and this file is the demonstration: the build
# happens in a stage that is thrown away, and the stage that actually runs is the same
# nginx image serving static files from a read-only root filesystem. Nothing writes into
# the served directory after start, because nothing in the final stage can write anywhere.
#
# Build context is the REPOSITORY ROOT, so the admin client can ship in the same image and
# share an origin with the consumer app — the same reason the classic image did it.

# ---------------------------------------------------------------- build stage
FROM node:24-alpine AS build

WORKDIR /build

# Dependencies first, so a source change does not re-resolve the tree.
COPY apps/consumer/package.json apps/consumer/package-lock.json ./
# `npm ci` rather than `npm install`: it installs exactly the lockfile and fails if the
# two disagree, which is the difference between a reproducible image and a hopeful one.
RUN npm ci

COPY apps/consumer/ ./

# Where the API lives, baked in at BUILD time.
#
# Not at run time, for the reason above. Empty means "the page host on the development API
# port", which is correct for a bare checkout and for docker-compose.yml, and wrong for
# staging — whose API is published on 18080 and which passes this through.
ARG API_BASE_URL=""
ENV VITE_API_BASE_URL=$API_BASE_URL

# Type-check and build. `npm run build` runs `tsc -b` first, so a type error fails the
# IMAGE rather than shipping and failing in someone's browser.
RUN npm run build && echo "consumer API base: ${API_BASE_URL:-client default}"

# ---------------------------------------------------------------- serve stage
FROM nginx:1.27-alpine

COPY --from=build /build/dist /usr/share/nginx/html
COPY apps/admin /usr/share/nginx/html/admin
COPY apps/consumer/nginx.conf /etc/nginx/conf.d/default.conf

# The admin client is a classic static surface with its own config seam, and it resolves
# the API itself. One build argument configures both so they cannot disagree about where
# the API is — which is a defect this programme has already fixed once.
ARG API_BASE_URL=""
RUN if [ -n "$API_BASE_URL" ]; then \
      printf '/* generated at build time from API_BASE_URL */\nwindow.DEDUNET_API_BASE = "%s";\n' \
        "$API_BASE_URL" > /usr/share/nginx/html/admin/config.js; \
      echo "admin API base: $API_BASE_URL"; \
    else \
      echo "admin API base: client default (page host on port 18000)"; \
    fi

EXPOSE 80
