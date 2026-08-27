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

# Where the API is, from the BROWSER's point of view.
#
# Empty is the intended value for this image, because nginx proxies /api on the same
# origin (see the serve stage). The client then needs no absolute base at all, which is
# both simpler and one fewer thing that can be wrong in a deployment.
#
# API_BASE_URL remains available for a cross-origin deployment, where it is baked in at
# BUILD time rather than read at run time — the served directory is read-only after start.
ARG API_BASE_URL=""
ARG API_SAME_ORIGIN="true"
ENV VITE_API_BASE_URL=$API_BASE_URL
ENV VITE_API_SAME_ORIGIN=$API_SAME_ORIGIN

# Type-check and build. `npm run build` runs `tsc -b` first, so a type error fails the
# IMAGE rather than shipping and failing in someone's browser.
RUN npm run build && echo "consumer API base: ${API_BASE_URL:-same-origin via nginx proxy}"

# ---------------------------------------------------------------- serve stage
FROM nginx:1.27-alpine

COPY --from=build /build/dist /usr/share/nginx/html
COPY apps/admin /usr/share/nginx/html/admin

# A TEMPLATE, rendered at container start.
#
# The nginx entrypoint runs envsubst over /etc/nginx/templates/*.template and writes the
# result into conf.d. NGINX_ENVSUBST_FILTER restricts substitution to the DEDUNET_ prefix
# so nginx's own $uri, $host and $upstream variables survive untouched — without the
# filter, envsubst would blank every one of them.
COPY apps/consumer/default.conf.template /etc/nginx/templates/default.conf.template
ENV NGINX_ENVSUBST_FILTER="DEDUNET_"

# The document security header contract, included by the template at server level AND by
# every location that declares an add_header of its own — because nginx discards inherited
# add_header directives in any scope that adds one. Copied to /etc/nginx rather than into
# conf.d: conf.d is a tmpfs at runtime (the entrypoint renders the template into it), and
# this file must come from the read-only image layer.
COPY apps/consumer/security-headers.conf /etc/nginx/security-headers.conf

# Where the commerce API is, from INSIDE the container.
#
# A service name on a shared Docker network by default, never a host address: the image
# stays portable and no LAN address is baked into it. Override per deployment.
ENV DEDUNET_API_UPSTREAM="api:8000"

# The admin client is a classic static surface with its own config seam and it resolves the
# API itself, so it cannot use the same-origin proxy above: its resolver treats an empty
# base as "not configured" and falls back to the page host on port 18000.
#
# Its argument is therefore SEPARATE from the consumer's. Sharing one would mean that
# configuring the admin silently switched the consumer out of same-origin mode, which is
# exactly the "two clients disagreeing about where the API is" defect this programme has
# already fixed once.
#
# Left unset, /admin on this image is not configured and is not part of the consumer
# acceptance surface.
ARG ADMIN_API_BASE_URL=""
RUN if [ -n "$ADMIN_API_BASE_URL" ]; then \
      printf '/* generated at build time from ADMIN_API_BASE_URL */\nwindow.DEDUNET_API_BASE = "%s";\n' \
        "$ADMIN_API_BASE_URL" > /usr/share/nginx/html/admin/config.js; \
      echo "admin API base: $ADMIN_API_BASE_URL"; \
    else \
      echo "admin API base: NOT CONFIGURED on this image"; \
    fi

EXPOSE 80
