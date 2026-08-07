/* Deployment configuration for the storefront.
 *
 * This committed copy configures NOTHING, which is correct for a local checkout: with no
 * override, media-url.js falls back to the page's own host on the development API port
 * (18000), which is what `docker-compose.yml` and the README already use.
 *
 * A deployment whose API is somewhere else replaces this file at BUILD time:
 *
 *     docker build --build-arg API_BASE_URL=http://127.0.0.1:18080 ...
 *
 * Build time, not run time, deliberately. The web container runs with a read-only root
 * filesystem, so nothing may write into the served directory after start; baking the
 * value in keeps that guarantee and keeps the image self-describing.
 *
 * Staging needs it because its API is published on 18080, not 18000 — without this the
 * storefront would ask the wrong port and every product, and the brand mark with them,
 * would fail to load.
 */
/* window.DEDUNET_API_BASE = "https://api.example"; */
