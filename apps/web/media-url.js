/* Central resolution of the API base and of API-backed asset URLs.
 *
 * WHY THIS IS ONE PLACE
 * ---------------------
 * The storefront and the API are different origins in every supported topology: compose
 * publishes nginx on 13000 and the API on 18000, and staging on 13080 and 18080. nginx
 * proxies nothing. So a root-relative asset path like
 *
 *     /api/v1/media/assets/brand-prototype/logos/logo-primary.svg
 *
 * resolves against the STOREFRONT origin, where nothing is mounted, and returns 404. That
 * is exactly what happened to the DEDUNET brand mark and favicon: the bytes were being
 * served correctly by the API the whole time, and the browser was asking the wrong host.
 * The mobile client never had the bug because it builds absolute URLs against its
 * configured API base -- which is what this module does for the web.
 *
 * Data requests already went through one helper in app.js. Assets did not, so they drifted.
 * Everything API-backed now goes through here.
 *
 * Loads as a browser global (`window.DedunetAssets`) and as a CommonJS module, so the
 * resolution rules can be unit-tested off-browser instead of only being observed in one.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.DedunetAssets = api;
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var MEDIA_PREFIX = "/api/v1/media/";

  /* An absolute or protocol-relative URL is already addressed and must be left alone --
   * rewriting it would silently retarget a deliberate external reference. */
  function isAbsolute(value) {
    return /^[a-z][a-z0-9+.-]*:\/\//i.test(value) || value.slice(0, 2) === "//";
  }

  function stripTrailingSlashes(value) {
    return String(value).replace(/\/+$/, "");
  }

  /* The configured API origin.
   *
   * Precedence: an explicit override, then the page's own host on the development API
   * port. The port is NOT the storefront's own port: same host, different service.
   */
  function apiBase(overrides) {
    var scope = overrides || (typeof window !== "undefined" ? window : {});
    var configured = scope.FASHION_POC_API_BASE || scope.DEDUNET_API_BASE;
    if (configured) return stripTrailingSlashes(configured);

    var location = scope.location || (typeof window !== "undefined" ? window.location : null);
    if (!location) return "";
    return location.protocol + "//" + location.hostname + ":18000";
  }

  /* Resolve one API-backed asset reference to a fetchable absolute URL.
   *
   * Accepts every shape the brand package and the API payloads actually produce:
   *
   *   "https://cdn.example/x.svg"                     absolute, returned unchanged
   *   "/api/v1/media/assets/.../logo.svg"             API-root-relative (the API payload)
   *   "api/v1/media/assets/.../logo.svg"              the same, without the leading slash
   *   "assets/brand-prototype/logos/logo.svg"         a bare package path
   *
   * Returns "" for a missing or unusable reference, so a caller can decide between a
   * placeholder and rendering nothing. Returning a half-built URL here would produce a
   * broken-image icon, which is worse than an intentional absence.
   */
  function assetUrl(assetPath, base) {
    if (assetPath === null || assetPath === undefined) return "";
    var path = String(assetPath).trim();
    if (path === "") return "";
    if (isAbsolute(path)) return path;

    var origin = stripTrailingSlashes(base === undefined ? apiBase() : base);

    /* Reject traversal before building a URL. The server refuses it too, but a client
     * that cheerfully constructs "../../" requests is a client that will eventually be
     * pointed at something else. */
    if (path.indexOf("..") !== -1) return "";

    var normalised = path.charAt(0) === "/" ? path : "/" + path;
    if (normalised.indexOf(MEDIA_PREFIX) === 0) {
      return origin + normalised;
    }
    /* A path already under /api/ but not under the media route is still API-relative. */
    if (normalised.indexOf("/api/") === 0) {
      return origin + normalised;
    }
    return origin + MEDIA_PREFIX + normalised.replace(/^\/+/, "");
  }

  /* Point every element carrying data-asset at the resolved URL.
   *
   * The markup cannot hold a correct src, because the API origin is only known at
   * runtime. So the HTML declares WHICH asset it wants and this assigns WHERE it lives.
   */
  function hydrateAssetElements(documentRef, base) {
    var doc = documentRef || (typeof document !== "undefined" ? document : null);
    if (!doc || !doc.querySelectorAll) return 0;

    var hydrated = 0;
    var nodes = doc.querySelectorAll("[data-asset]");
    for (var i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      var url = assetUrl(node.getAttribute("data-asset"), base);
      if (!url) continue;
      if (node.tagName === "LINK") {
        node.setAttribute("href", url);
      } else {
        node.setAttribute("src", url);
      }
      hydrated += 1;
    }
    return hydrated;
  }

  return {
    apiBase: apiBase,
    assetUrl: assetUrl,
    hydrateAssetElements: hydrateAssetElements,
    MEDIA_PREFIX: MEDIA_PREFIX
  };
});
