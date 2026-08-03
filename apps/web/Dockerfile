FROM nginx:1.27-alpine

# Build context is the PoC root (see docker-compose.yml) so both browser clients ship in
# one image and share an origin. That matters: they call the API cross-origin already,
# and splitting them across two origins would need a second CORS entry for no benefit.
COPY apps/web   /usr/share/nginx/html/storefront
COPY apps/admin /usr/share/nginx/html/admin
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
