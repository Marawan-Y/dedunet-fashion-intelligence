/* Deployment configuration for the operations portal.
 *
 * This committed copy configures NOTHING, which is correct for a local checkout: with no
 * override, api-config.js falls back to this page's host on the development API port
 * (18000), which is what `docker-compose.yml` and the README already use.
 *
 * A deployment whose API is somewhere else replaces this file at BUILD time:
 *
 *     docker build --build-arg API_BASE_URL=http://127.0.0.1:18080 -f apps/web/Dockerfile .
 *
 * Build time, not run time, deliberately — the web container runs with a read-only root
 * filesystem, so nothing may write into the served directory after start. Baking the value
 * in keeps that guarantee and makes the image self-describing.
 *
 * Staging needs it because its API is published on 18080, not 18000. Without it the portal
 * asked the wrong port and every request failed as "Failed to fetch" before an
 * administrator could sign in. This is the same file, for the same reason, as
 * apps/web/config.js.
 */
/* window.DEDUNET_API_BASE = "https://api.example"; */
