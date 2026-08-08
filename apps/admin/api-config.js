/* Where the operations portal finds the API.
 *
 * WHY THIS EXISTS
 * ---------------
 * The admin bundle previously resolved its API inline:
 *
 *     window.FASHION_POC_API_BASE ?? `${protocol}//${hostname}:18000`
 *
 * with no runtime configuration seam and no `config.js` in its markup. Staging publishes
 * the API on 18080, so the deployed portal asked port 18000, where nothing listens, and
 * every request died as "Failed to fetch" before an administrator could even sign in.
 * The storefront already had this seam; the admin was simply never given one.
 *
 * This is the storefront's mechanism, not a second invention: a generated `config.js` sets
 * a global, and this module resolves it with the same precedence
 * (`apps/web/media-url.js` -> `apiBase`). A test asserts the two agree, so they cannot
 * drift into disagreeing about where the API lives.
 *
 * Loads as a browser global (`window.DedunetAdminConfig`) and as a CommonJS module, so the
 * precedence and the validation can be unit-tested off-browser rather than only observed
 * in one.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.DedunetAdminConfig = api;
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /* The DEVELOPMENT default only. Staging and any other deployment supply their own origin
   * through config.js, generated from the API_BASE_URL build argument — so no deployment's
   * port is ever written into application logic. */
  var DEV_API_PORT = 18000;

  function stripTrailingSlashes(value) {
    return String(value).replace(/\/+$/, "");
  }

  /* A configured base must be an absolute http(s) origin. Anything else is REJECTED rather
   * than quietly ignored: silently falling back after a typo is how the portal ends up
   * pointing at the wrong host while looking configured, which is the defect this closes. */
  function validate(value) {
    var text = stripTrailingSlashes(String(value).trim());
    if (!/^https?:\/\/[^/\s?#]+$/i.test(text)) {
      /* The example deliberately carries no port. A concrete deployment port written here
       * would be one more place a reader could mistake for configuration. */
      throw new Error(
        "DEDUNET admin API base is not a usable absolute origin: " +
          JSON.stringify(String(value)) +
          '. Expected an absolute origin such as "http://api.example" or "http://host:port".'
      );
    }
    return text;
  }

  /* Resolve the API origin.
   *
   * Precedence is deliberately identical to the storefront's:
   *   1. FASHION_POC_API_BASE  — the legacy manual override, still honoured
   *   2. DEDUNET_API_BASE      — what the generated config.js sets
   *   3. this page's host on the development API port
   *
   * `hostname`, not `host`: the API is a different service on a different port, and using
   * `host` would carry the storefront's port across. Reading it from the page means
   * localhost and 127.0.0.1 each keep the spelling the operator actually browsed with,
   * which matters because they are distinct origins to CORS.
   */
  function apiBase(overrides) {
    var scope = overrides || (typeof window !== "undefined" ? window : {});
    var configured = scope.FASHION_POC_API_BASE || scope.DEDUNET_API_BASE;
    if (configured) return validate(configured);

    var location = scope.location || (typeof window !== "undefined" ? window.location : null);
    if (!location) {
      throw new Error("cannot resolve the DEDUNET admin API base: no configuration and no page location");
    }
    return location.protocol + "//" + location.hostname + ":" + DEV_API_PORT;
  }

  return { apiBase: apiBase, validate: validate, DEV_API_PORT: DEV_API_PORT };
});
