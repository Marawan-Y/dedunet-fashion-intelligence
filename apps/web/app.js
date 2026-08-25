/**
 * DEDUNET consumer platform — routes and views.
 *
 * SECURITY (closes SB-RISK-003, stored XSS)
 * -----------------------------------------
 * The previous implementation assembled markup with `innerHTML` and template literals,
 * so a product name, description or AI response containing markup executed in the
 * customer's browser. Every node here is built with `document.createElement` and every
 * string is inserted as `textContent`, which cannot execute. There is no `innerHTML`
 * anywhere in this file and a test asserts that.
 *
 * MONEY (preserves contract SB-AR-B3-003)
 * ---------------------------------------
 * The API sends authoritative INTEGER MINOR UNITS. `money()` formats them with integer
 * and string operations only — no division, so no binary float ever touches an amount.
 */

/* One definition of where the API lives, shared with asset URL resolution. Data requests
   and asset requests drifting apart is how the brand mark ended up pointing at the
   storefront origin while every data call went to the API. */
const API_BASE = window.DedunetAssets.apiBase();

/* Resolve an API-backed asset (brand mark, product media) to an absolute URL on the API
   origin. Never build one of these by string concatenation at a call site. */
const assetUrl = (path) => window.DedunetAssets.assetUrl(path, API_BASE);

/* The markup declares WHICH brand assets it wants; this assigns WHERE they live, now that
   the API base is known. Runs immediately: these elements are in the initial HTML. */
window.DedunetAssets.hydrateAssetElements(document, API_BASE);

/* Primitives come from the design system so the platform has ONE element factory and ONE
   money formatter. Aliased rather than rewritten at each site, so the several dozen call
   sites below are untouched and this refactor cannot quietly change what any of them
   renders. `money` moved across verbatim, degradation path included. */
const el = window.DS.el;
const money = window.DS.money;
const icon = window.DS.icon;
const DATA = window.DedunetData;

/* One-time migration of browser storage keys from the legacy brand prefix.
   Renaming a key without moving its value signs every existing session out and silently
   discards a live cart, so the old value is carried across once and then removed. */
(function migrateLegacyStorageKeys() {
  const moved = {
    meret_cart: "dedunet_cart",
    meret_token: "dedunet_token",
    meret_role: "dedunet_role",
    meret_admin_token: "dedunet_admin_token",
  };
  for (const [from, to] of Object.entries(moved)) {
    const value = localStorage.getItem(from);
    if (value !== null && localStorage.getItem(to) === null) localStorage.setItem(to, value);
    if (value !== null) localStorage.removeItem(from);
  }
})();

const state = {
  cartToken: localStorage.getItem("dedunet_cart") || "",
  token: localStorage.getItem("dedunet_token") || "",
  role: localStorage.getItem("dedunet_role") || "",
  /* The deployment's commerce mode, once the API has said what it is.
     `null` is a distinct third state meaning "not yet known", never a silent fallback to
     either working mode: assuming preview would understate a live sandbox, and assuming
     commerce-test would invite a purchase this deployment may refuse. Every reader below
     handles the three cases separately. */
  commerceMode: null,
};

/* The two modes a deployment may actually be in. `modes.current_mode()` refuses everything
   else, so a payload naming anything else -- including PUBLIC_COMMERCE_MODE -- describes a
   deployment that cannot say what it is, and leaves `state.commerceMode` null. */
const KNOWN_MODES = ["BRAND_PREVIEW_MODE", "COMMERCE_TEST_MODE"];

/* ---------------------------------------------------------------- product media
 *
 * Consumes the SAME `product.media` the mobile Gallery consumes. There is deliberately no
 * web-only media source: two clients deriving imagery from two places is how they end up
 * disagreeing about what a product looks like.
 *
 * The API already returns media in a deterministic order (sort_order, then asset_id), so
 * this preserves the server's order rather than imposing its own. Sorting here would mean
 * two surfaces could order the same product differently.
 */

/* Alt text, in the order of how much it is worth trusting: Side A's own wording, then a
   role-derived description, then the product name. Never empty on a meaningful image, and
   never invented detail about a garment nobody has photographed. */
function mediaAltText(item, product) {
  if (item.alt_text && item.alt_text.trim()) return item.alt_text.trim();
  const role = (item.role || "").trim();
  return role ? `${product.name} — ${role} view (concept artwork)` : `${product.name} (concept artwork)`;
}

function mediaFigure(item, product, { primary = false } = {}) {
  const url = assetUrl(item.url || item.path);
  if (!url) return null;

  const image = el("img", {
    class: primary ? "pdp__image pdp__image--primary" : "pdp__image",
    src: url,
    alt: mediaAltText(item, product),
    // Eager for ALL of them, not just the primary. This is one product's four small
    // concept SVGs, which is exactly what the customer opened the page to look at;
    // deferring three of them below the fold buys nothing and made the gallery's state
    // depend on scroll position. The catalogue grid still lazy-loads, because that is a
    // list that grows.
    loading: "eager",
    decoding: "async",
  });

  /* A failed image must degrade to readable text, not to the browser's broken-image
     glyph. The glyph tells a customer nothing and looks like a defect in the product. */
  image.addEventListener("error", () => {
    const fallback = el("p", {
      class: "pdp__image-missing",
      text: `${mediaAltText(item, product)} — image unavailable`,
    });
    if (image.parentNode) image.parentNode.replaceChild(fallback, image);
  });

  return el("figure", { class: primary ? "pdp__figure pdp__figure--primary" : "pdp__figure" }, [
    image,
    el("figcaption", { class: "pdp__figcaption", text: (item.role || "view").replace(/^\w/, (c) => c.toUpperCase()) }),
  ]);
}

function productGallery(product) {
  const media = Array.isArray(product.media) ? product.media.filter((m) => m && (m.url || m.path)) : [];

  /* Zero media renders NOTHING rather than an empty frame or a placeholder pretending to
     be an image. The prototype disclosure below already tells the customer what this is. */
  if (!media.length) return null;

  const [first, ...rest] = media;
  const children = [mediaFigure(first, product, { primary: true })];

  if (rest.length) {
    children.push(
      el(
        "div",
        { class: "pdp__thumbs" },
        rest.map((item) => mediaFigure(item, product)).filter(Boolean)
      )
    );
  }

  /* Concept status comes from the data, so it cannot say "concept artwork" about a real
     photograph later, nor stay silent about a concept now. */
  const concept = media.some((m) => (m.status || "").toUpperCase() === "PROTOTYPE_CONCEPT");
  if (concept) {
    children.push(el("p", { class: "pdp__media-note", text: "Concept artwork — not product photography." }));
  }

  return el("div", { class: "pdp__media" }, children.filter(Boolean));
}

/* Card thumbnail: the front image if there is one, otherwise the existing initial. */
function cardMedia(product) {
  const media = Array.isArray(product.media) ? product.media.filter((m) => m && (m.url || m.path)) : [];
  const front = media.find((m) => (m.role || "").toLowerCase() === "front") || media[0];
  if (!front) {
    return el("div", { class: "card__media", "aria-hidden": "true", text: product.name.slice(0, 1) });
  }
  const url = assetUrl(front.url || front.path);
  if (!url) {
    return el("div", { class: "card__media", "aria-hidden": "true", text: product.name.slice(0, 1) });
  }
  const image = el("img", {
    class: "card__image",
    src: url,
    alt: mediaAltText(front, product),
    loading: "lazy",
    decoding: "async",
  });
  const wrapper = el("div", { class: "card__media" }, [image]);
  image.addEventListener("error", () => {
    wrapper.textContent = product.name.slice(0, 1);
    wrapper.setAttribute("aria-hidden", "true");
  });
  return wrapper;
}

function headers(extra = {}) {
  const base = { "Content-Type": "application/json", ...extra };
  if (state.token) base["Authorization"] = `Bearer ${state.token}`;
  if (state.cartToken) base["X-Cart-Token"] = state.cartToken;
  return base;
}

/* ------------------------------------------------------------------ session policy
 *
 * Human acceptance found a customer whose stored token had expired still being shown
 * "Signed in as customer", while `/api/v1/me/orders` answered 401 "invalid or expired
 * session" and the orders page reported "You have no orders yet." -- a page stating, on the
 * strength of a rejected request, that the customer had never ordered anything.
 *
 * One rule, in one place: the server rejecting an authenticated request is the only thing
 * that ends a session on this client. The mobile client already works this way
 * (`store.ts` -> `handleFailure`); this is the same policy, not a second invention.
 */

/** Forget the customer session. The cart is deliberately kept -- the basket is the device's. */
function clearCustomerAuth() {
  state.token = "";
  state.role = "";
  localStorage.removeItem("dedunet_token");
  localStorage.removeItem("dedunet_role");
}

/**
 * Should this failure end the session?
 *
 * ONLY a 401 answered to a request that actually carried our credentials. Everything else
 * is the network, the server or a limiter having a bad moment, and none of them are
 * evidence about the token:
 *
 *   transport failure  fetch rejects; there is no response and no status to read
 *   429                the request was never evaluated
 *   5xx                the server failed to answer, not refused to
 *   403                authenticated fine, just not permitted
 *   401 unauthenticated  a failed sign-in attempt; there is no session to end
 *
 * Signing a customer out because their train went into a tunnel is a worse defect than the
 * one being fixed, so the condition is narrow on purpose.
 */
function isSessionRejection(status, sentCredentials) {
  return status === 401 && sentCredentials;
}

async function api(path, options = {}) {
  const requestHeaders = headers(options.headers);
  const sentCredentials = Boolean(requestHeaders["Authorization"]);

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: requestHeaders,
  });
  const raw = await response.text();
  let body = null;
  try {
    body = raw ? JSON.parse(raw) : null;
  } catch {
    body = { detail: raw };
  }
  if (!response.ok) {
    const error = new Error(
      (body && typeof body.detail === "string" && body.detail) ||
        `Request failed (${response.status})`
    );
    error.status = response.status;
    if (isSessionRejection(response.status, sentCredentials)) {
      clearCustomerAuth();
      // Marked so a caller can tell "your session ended" from "that request failed", and
      // so no caller has to re-derive the rule from the status code.
      error.sessionExpired = true;
    }
    throw error;
  }
  return body;
}

/* ------------------------------------------------------- commerce-mode disclosure
 *
 * The top notice must state what THIS deployment can actually do. It used to be a fixed
 * sentence in the markup saying nothing was available to purchase, which was false in
 * COMMERCE_TEST_MODE -- synthetic stock is purchasable there and sandbox checkout
 * completes. Human acceptance found it saying so while placing a sandbox order.
 *
 * The mode and its wording both come from the API. Deriving either here would mean two
 * clients each deciding what a mode means, and inferring the mode from the catalogue --
 * "there is stock, so we must be in test mode" -- would make the disclosure a guess about
 * inventory rather than a statement about configuration.
 */

/** Render the disclosure for a mode. Text only: this is a notice, not a template. */
function renderCommerceNotice(disclosure) {
  const host = document.getElementById("commerce-mode-notice");
  if (!host) return null;

  const headline = typeof disclosure?.headline === "string" ? disclosure.headline.trim() : "";
  const detail = Array.isArray(disclosure?.detail)
    ? disclosure.detail.filter((line) => typeof line === "string" && line.trim())
    : [];

  /* A response we cannot read leaves the shipped sentence alone. It is true in every
     permitted mode, so saying nothing new is safer than saying something unverified. */
  if (!headline || !detail.length) return null;

  host.replaceChildren(
    el("strong", { class: "notice__headline", text: headline }),
    ...detail.map((line) => el("span", { class: "notice__line", text: line }))
  );
  return host;
}

/**
 * Record the deployment's mode, if the payload names one this client can act on.
 *
 * Separate from `renderCommerceNotice` because the two consume different halves of the
 * same response and must fail independently: a disclosure missing its `headline` is
 * unrenderable but may still carry a usable `mode`, and a payload naming an unknown mode
 * must not become a mode however well-formed its prose is.
 *
 * Validated against `KNOWN_MODES` rather than stored raw. Everything downstream of here
 * decides what a customer is invited to do, so an unrecognised string must land in the
 * "not known" case and not in one of the two working ones.
 */
function recordCommerceMode(disclosure) {
  const mode = typeof disclosure?.mode === "string" ? disclosure.mode.trim() : "";
  state.commerceMode = KNOWN_MODES.includes(mode) ? mode : null;
  return state.commerceMode;
}

/* The boot request for the mode, so a view that needs the mode can wait for the request
   already in flight instead of issuing a second one.

   It exists because the ordering at boot is against us: `route` and `loadCommerceNotice`
   are both DOMContentLoaded listeners and `route` is registered first, so a customer
   opening `#/orders` directly renders the page BEFORE the mode has been asked for, let
   alone answered. Without this, the mode-specific copy would be unreachable on the one
   path that matters most -- a hard reload of the page the defect was found on -- and the
   neutral fallback would be what shipped.

   Never rejects: `loadCommerceNotice` swallows its own failure, and a waiter must not be
   able to turn a disclosure problem into a route error. */
let modeReady = null;

async function loadCommerceNotice() {
  try {
    const disclosure = await api("/api/v1/commerce/mode");
    recordCommerceMode(disclosure);
    renderCommerceNotice(disclosure);
  } catch {
    /* Deliberately silent. The mode notice is a disclosure, not a feature: if the call
       fails the shipped sentence still stands, and an error banner about it would push a
       transport problem in front of a customer who can do nothing with it. */
  }
}

/**
 * Wait for the boot mode request, but never longer than `ms`.
 *
 * Bounded on purpose. `api()` has no timeout, so awaiting the mode unconditionally would
 * let a hanging `/api/v1/commerce/mode` hold a route in `loading()` indefinitely -- a blank
 * page, which is the outcome `route`'s own catch exists to prevent. On expiry the caller
 * proceeds with `state.commerceMode` still null and gets the neutral wording, which is the
 * correct thing to say when the deployment has not answered.
 *
 * Resolves immediately when the mode is already known, which is every navigation after the
 * first and, in practice, the first one too by the time a data call has returned.
 */
function awaitCommerceMode(ms = 2000) {
  if (state.commerceMode !== null || modeReady === null) return Promise.resolve(state.commerceMode);
  let timer = null;
  return Promise.race([
    modeReady,
    new Promise((resolve) => {
      timer = setTimeout(resolve, ms);
    }),
  ]).then(() => {
    if (timer !== null) clearTimeout(timer);
    return state.commerceMode;
  });
}

function setBanner(message, kind = "info") {
  const host = document.getElementById("banner");
  host.replaceChildren();
  if (message) {
    host.appendChild(el("div", { class: `banner banner--${kind}`, role: "status", text: message }));
  }
}

function render(...nodes) {
  document.getElementById("main").replaceChildren(...nodes.filter(Boolean));
  window.scrollTo(0, 0);
}

/* A skeleton rather than the word "Loading…". It reserves the grid the content will
   occupy, so arriving data does not shift the page under a reader's eyes -- and on a slow
   phone connection that shift is the difference between tapping a card and tapping the one
   that replaced it. */
function loading({ skeleton = true, count = 6 } = {}) {
  render(skeleton
    ? window.DS.skeletonGrid(count)
    : el("p", { class: "muted", role: "status", text: "Loading…" }));
}

/* Delegates to the design system's state component, keeping the three-argument shape
   every existing caller already uses. */
function emptyState(message, actionLabel, actionHref) {
  return window.DS.emptyState(message, actionLabel, actionHref);
}

function totalRow(label, minorUnits, strong = false) {
  return el("div", { class: "totals__row" }, [
    el("span", { text: label }),
    el(strong ? "strong" : "span", { text: money(minorUnits) }),
  ]);
}

/* ---------------------------------------------------------------------- views */

async function viewCatalog() {
  loading();
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const query = new URLSearchParams();
  for (const key of ["category", "q", "sort"]) {
    if (params.get(key)) query.set(key, params.get(key));
  }

  let products;
  try {
    products = await api(`/api/v1/catalog/products?${query.toString()}`);
  } catch (error) {
    return render(emptyState(`Could not load the collection. ${error.message}`));
  }

  const filters = el(
    "form",
    {
      class: "filters",
      onsubmit: (event) => {
        event.preventDefault();
        const next = new URLSearchParams();
        const q = event.target.elements.q.value.trim();
        if (q) next.set("q", q);
        if (event.target.elements.category.value) next.set("category", event.target.elements.category.value);
        if (event.target.elements.sort.value) next.set("sort", event.target.elements.sort.value);
        location.hash = `#/catalog?${next.toString()}`;
      },
    },
    [
      el("label", { class: "sr-only", for: "f-q", text: "Search products" }),
      el("input", { id: "f-q", name: "q", type: "search", placeholder: "Search", value: params.get("q") || "" }),
      el("label", { class: "sr-only", for: "f-cat", text: "Category" }),
      el(
        "select",
        { id: "f-cat", name: "category" },
        ["", "tops", "bottoms", "outerwear", "accessories"].map((value) =>
          el("option", {
            value,
            text: value || "All categories",
            selected: (params.get("category") || "") === value ? "selected" : null,
          })
        )
      ),
      el("label", { class: "sr-only", for: "f-sort", text: "Sort" }),
      el("select", { id: "f-sort", name: "sort" }, [
        el("option", { value: "name", text: "Sort: name" }),
        el("option", { value: "price", text: "Sort: price", selected: params.get("sort") === "price" ? "selected" : null }),
      ]),
      el("button", { class: "btn", type: "submit", text: "Apply" }),
    ]
  );

  if (!products.length) {
    return render(el("h1", { text: "Collection" }), filters, emptyState("No products match that search.", "Clear filters", "#/catalog"));
  }

  const grid = el(
    "div",
    { class: "grid" },
    products.map((product) => {
      const cheapest = Math.min(...product.variants.map((v) => v.price_minor_units));
      const inStock = product.variants.some((v) => v.available > 0);
      return el("a", { class: "card", href: `#/product/${product.slug}` }, [
        cardMedia(product),
        el("h2", { class: "card__title", text: product.name }),
        el("p", { class: "card__meta", text: product.collection || product.category }),
        el("p", { class: "card__price", text: money(cheapest, product.currency) }),
        el("p", { class: inStock ? "tag tag--ok" : "tag tag--out", text: inStock ? "In stock" : "Sold out" }),
      ]);
    })
  );

  render(el("h1", { text: "Collection" }), filters, grid);
}

async function viewProduct(slug) {
  loading();
  let product;
  try {
    product = await api(`/api/v1/catalog/products/${encodeURIComponent(slug)}`);
  } catch (error) {
    return render(
      emptyState(
        error.status === 404 ? "That product is not available." : error.message,
        "Back to collection",
        "#/catalog"
      )
    );
  }

  let selected = product.variants.find((v) => v.available > 0) || product.variants[0];
  const stock = el("p", { class: "muted", text: selected.available > 0 ? `${selected.available} available` : "Sold out" });

  const sizes = el(
    "div",
    { class: "sizes", role: "group", "aria-label": "Select a size" },
    product.variants.map((variant) => {
      const button = el("button", {
        class: "size" + (variant.id === selected.id ? " size--on" : ""),
        type: "button",
        "aria-pressed": variant.id === selected.id ? "true" : "false",
        disabled: variant.available === 0 ? "disabled" : null,
        text: variant.size,
        onclick: () => {
          selected = variant;
          for (const node of sizes.children) {
            node.className = "size";
            node.setAttribute("aria-pressed", "false");
          }
          button.className = "size size--on";
          button.setAttribute("aria-pressed", "true");
          stock.textContent = variant.available > 0 ? `${variant.available} available` : "Sold out";
          price.textContent = money(variant.price_minor_units, product.currency);
        },
      });
      return button;
    })
  );

  const price = el("p", { class: "pdp__price", text: money(selected.price_minor_units, product.currency) });

  /* Mirrors `modes.assert_purchasable`, both gates and in its order. The server refuses
     either way; this decides whether the customer is invited to press a button whose only
     outcome is a rejection. See `purchaseRefusal`.

     Awaited for the same reason the orders view awaits it: on a direct load of a product
     URL this render happens before the boot mode request has answered, and the mode gate
     cannot be evaluated against a mode nobody has stated yet. The product fetch above has
     already given it a round trip to settle. */
  const refusal = purchaseRefusal(product, await awaitCommerceMode());

  const addButton = el("button", {
    class: "btn btn--primary",
    type: "button",
    text: refusal ? "Not available to buy" : "Add to cart",
    disabled: refusal ? "disabled" : null,
    /* The label already says so, but a disabled control is skipped by some screen-reader
       navigation modes, so the reason is attached to the button itself rather than left to
       the separate banner a customer may never reach. */
    "aria-describedby": refusal ? "purchase-refusal" : null,
    onclick: async () => {
      addButton.disabled = true;
      try {
        const cart = await api("/api/v1/cart/items", {
          method: "POST",
          body: JSON.stringify({ variant_id: selected.id, quantity: 1 }),
        });
        state.cartToken = cart.cart_token;
        localStorage.setItem("dedunet_cart", cart.cart_token);
        setBanner("Added to your cart.", "ok");
      } catch (error) {
        setBanner(error.message, "error");
      } finally {
        addButton.disabled = false;
      }
    },
  });

  render(
    el("nav", { class: "crumbs" }, [el("a", { href: "#/catalog", text: "← Collection" })]),
    evidenceBanner(product),
    el("div", { class: "pdp" }, [
      productGallery(product) ||
        el("div", { class: "pdp__media", "aria-hidden": "true", text: product.name.slice(0, 1) }),
      el("div", { class: "pdp__info" }, [
        el("h1", { text: product.name }),
        price,
        el("p", { text: product.description }),
        el("h2", { class: "h6", text: "Size" }),
        sizes,
        stock,
        addButton,
        refusal
          ? el("p", { class: "muted", id: "purchase-refusal", text: refusalText(refusal) })
          : null,
        el("dl", { class: "specs" }, specRows(product)),
        el("p", {
          class: "disclaimer",
          text: disclaimerFor(product),
        }),
      ]),
    ])
  );
}

// ---------------------------------------------------------------- evidence-safe display
//
// The API ships typed states (origin_claim_status, evidence_status, sellable, ...) precisely
// so a client never has to parse prose to decide what it may say. These three helpers are
// the only place that turns those states into customer-facing text.

/**
 * Origin text, or null to render nothing.
 *
 * NEVER produces "Made in ...". `country_of_origin` is the deliberately invalid code `XX`
 * while origin is unsubstantiated, and rendering it raw would show a customer "XX". When a
 * real code is present it is still labelled unverified, because the payload carries no
 * evidence that it was substantiated.
 */
function originText(product) {
  const status = product.origin_claim_status || "";
  const code = (product.country_of_origin || "").trim().toUpperCase();

  if (status === "UNVERIFIED" || code === "XX" || code === "") {
    const intended = (product.intended_origin || "").trim().toUpperCase();
    return intended
      ? `Intended production in ${intended} — not verified, no origin claim is made`
      : null;
  }
  if (!/^[A-Z]{2}$/.test(code)) return null;
  return `Declared origin ${code} — not independently verified`;
}

function specRows(product) {
  const rows = [];
  if (product.material) {
    rows.push(el("dt", { text: "Material" }));
    rows.push(el("dd", { text: `${product.material} (stated, not tested)` }));
  }
  if (product.care_instructions) {
    rows.push(el("dt", { text: "Care" }));
    rows.push(el("dd", { text: product.care_instructions }));
  }
  const origin = originText(product);
  if (origin) {
    rows.push(el("dt", { text: "Origin" }));
    rows.push(el("dd", { text: origin }));
  }
  return rows;
}

function disclaimerFor(product) {
  if (product.external_product_id) {
    return (
      "Prototype product. Imagery is concept artwork, not product photography. " +
      "Material, composition and origin are stated intentions pending supplier documents, " +
      "samples and testing. Nothing here is available to purchase."
    );
  }
  return (
    "Fictional demonstration product. Material and origin fields are illustrative and are " +
    "not substantiated claims."
  );
}

/* ------------------------------------------------------------------ purchasability
 *
 * iPhone Safari acceptance, issue A. In BRAND_PREVIEW_MODE the product page offered an
 * ordinary, enabled "Add to cart". Pressing it produced a 409 -- the server was correct
 * throughout -- so the page was inviting the customer to do something the deployment had
 * already decided to refuse. The same class of untruth as the storefront banner closed in
 * `1a90c10` and the native order copy closed in `4e4f8c0`, one page further in.
 *
 * `modes.assert_purchasable` refuses on TWO independent gates and this mirrors both, in the
 * same order, so the client's prediction and the server's decision cannot disagree:
 *
 *   MODE     brand preview refuses every purchase, whatever the product says
 *   PRODUCT  a non-sellable product is refused in any mode
 *
 * Mirroring only the product gate -- which is what the native client does -- is correct
 * today only because every product in a preview catalogue also carries `sellable: false`.
 * That is a property of the current seed, not a rule the server enforces, so the mode gate
 * is checked here in its own right rather than inferred from the flag.
 */

/**
 * Why this product cannot be bought, or null if nothing forbids it.
 *
 * Returns the REASON, not a boolean, because the two refusals are different facts about
 * the deployment and a customer told the wrong one has been misinformed rather than merely
 * under-informed.
 *
 * An unresolved mode (`null`) deliberately does not refuse on its own. The mode gate cannot
 * be evaluated before the deployment has answered, and disabling on that basis would block
 * a legitimate purchase in COMMERCE_TEST_MODE for as long as the mode call is in flight.
 * The product gate still applies meanwhile, and in a preview catalogue it is what fires.
 */
function purchaseRefusal(product, mode) {
  if (mode === "BRAND_PREVIEW_MODE") return "preview";
  /* `sellable === false` is a deliberate refusal. `undefined` is the legacy payload, which
     predates the flag, and must not be read as "not sellable". */
  if (product?.sellable === false) return "product";
  return null;
}

/** The reason text for a refusal, for the control it disables. */
function refusalText(refusal) {
  if (refusal === "preview") {
    return "This catalogue is in preview. Nothing is available to buy while it is.";
  }
  return "This piece is shown for review and is not available to buy.";
}

/** Banner shown when a product is visible but deliberately not purchasable. */
function evidenceBanner(product) {
  if (product.sellable !== false) return null;
  return el("p", {
    class: "disclaimer",
    role: "status",
    text:
      "Preview only — this piece is not available to buy. " +
      "It is shown to review design, copy and imagery before any commercial launch.",
  });
}

async function viewCart() {
  loading();
  if (!state.cartToken) return render(emptyState("Your cart is empty.", "Browse the collection", "#/catalog"));

  let cart;
  let quote = null;
  try {
    cart = await api("/api/v1/cart");
    if (cart.lines.length) quote = await api("/api/v1/cart/quote");
  } catch (error) {
    return render(emptyState(error.message, "Back to collection", "#/catalog"));
  }
  if (!cart.lines.length) return render(emptyState("Your cart is empty.", "Browse the collection", "#/catalog"));

  const rows = cart.lines.map((line) =>
    el("tr", {}, [
      el("td", {}, [
        el("strong", { text: line.product_name }),
        el("br"),
        el("span", { class: "muted", text: `${line.size} · ${line.color} · ${line.sku}` }),
      ]),
      el("td", { text: String(line.quantity) }),
      el("td", { text: money(line.unit_price_minor_units) }),
      el("td", {}, [
        el("button", {
          class: "btn btn--quiet",
          type: "button",
          text: "Remove",
          "aria-label": `Remove ${line.product_name}`,
          onclick: async () => {
            try {
              await api(`/api/v1/cart/items/${line.variant_id}`, { method: "DELETE" });
              viewCart();
            } catch (error) {
              setBanner(error.message, "error");
            }
          },
        }),
      ]),
    ])
  );

  render(
    el("h1", { text: "Cart" }),
    el("table", { class: "table" }, [
      el("thead", {}, [
        el("tr", {}, [el("th", { text: "Item" }), el("th", { text: "Qty" }), el("th", { text: "Price" }), el("th", { text: "" })]),
      ]),
      el("tbody", {}, rows),
    ]),
    quote
      ? el("div", { class: "totals" }, [
          totalRow("Subtotal", quote.subtotal_minor_units),
          quote.discount_minor_units ? totalRow(`Discount ${quote.promotion_code}`, -quote.discount_minor_units) : null,
          totalRow("Shipping", quote.shipping_minor_units),
          totalRow("Total", quote.total_minor_units, true),
          el("p", { class: "muted", text: `Includes VAT ${money(quote.tax_minor_units)}` }),
        ])
      : null,
    el("a", { class: "btn btn--primary", href: "#/checkout", text: "Checkout" })
  );
}

async function viewCheckout() {
  if (!state.token) {
    setBanner("Please sign in to complete your order.", "info");
    location.hash = "#/account";
    return;
  }
  loading();

  let quote;
  try {
    quote = await api("/api/v1/cart/quote");
  } catch (error) {
    return render(emptyState(error.message, "Back to cart", "#/cart"));
  }

  const form = el("form", { class: "form", onsubmit: submit }, [
    el("h1", { text: "Checkout" }),
    el("label", { for: "pm", text: "Payment method (sandbox)" }),
    el("select", { id: "pm", name: "pm" }, [
      el("option", { value: "pm_success", text: "Test card — succeeds" }),
      el("option", { value: "pm_decline", text: "Test card — declined" }),
      el("option", { value: "pm_error", text: "Test card — provider error" }),
    ]),
    el("label", { for: "promo", text: "Promotion code (optional)" }),
    el("input", { id: "promo", name: "promo", type: "text", placeholder: "WELCOME10" }),
    el("div", { class: "totals" }, [
      totalRow("Subtotal", quote.subtotal_minor_units),
      totalRow("Shipping", quote.shipping_minor_units),
      totalRow("Total", quote.total_minor_units, true),
    ]),
    el("button", { class: "btn btn--primary", type: "submit", text: "Place order" }),
    el("p", { class: "disclaimer", text: "Sandbox payments only. No real card is charged and no real order is placed." }),
  ]);

  async function submit(event) {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    setBanner("");
    try {
      const result = await api("/api/v1/checkout", {
        method: "POST",
        body: JSON.stringify({
          payment_method_token: form.elements.pm.value,
          // Per-attempt key: retrying after a decline must be a new attempt, while an
          // accidental double-submit of the SAME attempt must replay, not re-charge.
          idempotency_key: `web-${state.cartToken}-${form.elements.pm.value}-${Date.now()}`,
          country_code: "DE",
          promotion_code: form.elements.promo.value.trim().toUpperCase(),
        }),
      });
      localStorage.removeItem("dedunet_cart");
      state.cartToken = "";
      location.hash = `#/order/${result.order.order_number}`;
    } catch (error) {
      setBanner(error.message, "error");
      button.disabled = false;
    }
  }

  render(form);
}

async function viewOrder(orderNumber) {
  loading();
  let order;
  try {
    order = await api(`/api/v1/me/orders/${encodeURIComponent(orderNumber)}`);
  } catch (error) {
    if (error.sessionExpired) return requireSignIn();
    return render(emptyState(error.message, "My orders", "#/orders"));
  }

  render(
    el("h1", { text: `Order ${order.order_number}` }),
    el("p", {}, [el("span", { class: "tag tag--ok", text: order.status })]),
    el("table", { class: "table" }, [
      el("thead", {}, [el("tr", {}, [el("th", { text: "Item" }), el("th", { text: "Qty" }), el("th", { text: "Total" })])]),
      el(
        "tbody",
        {},
        order.lines.map((line) =>
          el("tr", {}, [
            el("td", { text: `${line.product_name} (${line.size})` }),
            el("td", { text: String(line.quantity) }),
            el("td", { text: money(line.line_total_minor_units) }),
          ])
        )
      ),
    ]),
    el("div", { class: "totals" }, [
      totalRow("Subtotal", order.subtotal_minor_units),
      order.discount_minor_units ? totalRow("Discount", -order.discount_minor_units) : null,
      totalRow("Shipping", order.shipping_minor_units),
      totalRow("Total", order.total_minor_units, true),
    ]),
    order.shipments.length
      ? el("p", { text: `Tracking: ${order.shipments[0].tracking_number} (${order.shipments[0].status})` })
      : el("p", { class: "muted", text: "Not yet shipped." }),
    order.status === "shipped" || order.status === "delivered"
      ? el("button", {
          class: "btn",
          type: "button",
          text: "Request a return",
          onclick: async () => {
            const reason = window.prompt("Why are you returning this order?");
            if (!reason) return;
            try {
              await api(`/api/v1/me/orders/${order.order_number}/returns`, {
                method: "POST",
                body: JSON.stringify({ reason }),
              });
              setBanner("Return requested.", "ok");
            } catch (error) {
              setBanner(error.message, "error");
            }
          },
        })
      : null
  );
}

/**
 * The empty order history, in wording the current commerce mode can support.
 *
 * iPhone Safari acceptance, issue B. The page said "You have no orders yet." full stop,
 * which in BRAND_PREVIEW_MODE reads as an invitation to place one. Nothing can be placed
 * there: `assert_purchasable` refuses every purchase before a payment call is reached.
 *
 * Derived from the MODE, never from stock or from the catalogue. A client reasoning "there
 * is inventory, so orders must be placeable" would be right today and wrong the first time
 * a preview catalogue carries a non-zero count for any reason.
 *
 * Three cases, none of them sharing a sentence with another -- the same discipline the
 * server applies to `PREVIEW_DISCLOSURE` and `COMMERCE_TEST_DISCLOSURE`, because a shared
 * sentence is how "no card is charged" ends up on a screen where one could be. The third
 * promises nothing at all: before the deployment has said what it allows, the honest answer
 * is that this client does not yet know.
 *
 * Wording matches the native client's `ordersEmptyDetail` exactly. Two surfaces describing
 * the same deployment differently is a defect even when both sentences are true.
 */
function ordersEmptyMessage(mode) {
  if (mode === "BRAND_PREVIEW_MODE") {
    return "No orders yet. Purchasing is unavailable while this catalogue is in preview.";
  }
  if (mode === "COMMERCE_TEST_MODE") {
    return "No orders yet. Sandbox test orders you place will appear here.";
  }
  return "No orders yet. Orders you place will appear here once this deployment allows purchasing.";
}

async function viewOrders() {
  if (!state.token) {
    location.hash = "#/account";
    return;
  }
  loading();

  let orders;
  try {
    orders = await api("/api/v1/me/orders");
  } catch (error) {
    // `.catch(() => [])` here previously turned every failure -- including the 401 that
    // ends the session -- into an empty list, so a rejected request rendered as "You have
    // no orders yet." That is not a degraded message; it is a false statement about the
    // customer's history, and it hid the expiry that caused it.
    if (error.sessionExpired) return requireSignIn();
    return render(emptyState(error.message, "Browse the collection", "#/catalog"));
  }

  if (!orders.length) {
    /* Awaited only on the branch that needs it, and only after the orders call has already
       returned -- so the boot request has had that whole round trip to settle and the wait
       is normally already over. A customer with orders never waits for it at all. */
    return render(
      emptyState(ordersEmptyMessage(await awaitCommerceMode()), "Browse the collection", "#/catalog")
    );
  }
  render(
    el("h1", { text: "My orders" }),
    el(
      "ul",
      { class: "list" },
      orders.map((order) =>
        el("li", {}, [
          el("a", { href: `#/order/${order.order_number}`, text: order.order_number }),
          el("span", { class: "muted", text: ` · ${order.status} · ${money(order.total_minor_units)}` }),
        ])
      )
    )
  );
}

/**
 * Send an expired session to the account page and say why.
 *
 * `clearCustomerAuth()` has already run by the time this is called, so the account view
 * renders its signed-out form rather than "Signed in as ..." -- the stale state the human
 * tester saw. The banner is what turns a silent redirect into an explanation.
 */
function requireSignIn() {
  location.hash = "#/account";
  route();
  setBanner("Your session has expired. Please sign in again.", "info");
}

function viewAccount() {
  if (state.token) {
    return render(
      el("h1", { text: "Account" }),
      el("p", { text: `Signed in as ${state.role}.` }),
      el("p", {}, [el("a", { href: "#/orders", text: "View my orders" })]),
      el("button", {
        class: "btn",
        type: "button",
        text: "Download my data",
        onclick: async () => {
          try {
            const data = await api("/api/v1/me/data-export");
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
            const link = el("a", { href: URL.createObjectURL(blob), download: "dedunet-my-data.json" });
            document.body.appendChild(link);
            link.click();
            link.remove();
          } catch (error) {
            setBanner(error.message, "error");
          }
        },
      }),
      el("button", {
        class: "btn btn--quiet",
        type: "button",
        text: "Sign out",
        // The same clearing the server-side rejection performs. Two copies of "what it
        // means to be signed out" is how one of them ends up forgetting a key.
        onclick: () => {
          clearCustomerAuth();
          location.hash = "#/catalog";
          route();
        },
      })
    );
  }

  async function submit(event, path) {
    event.preventDefault();
    setBanner("");
    const form = event.target;
    const body = { email: form.elements.email.value, password: form.elements.password.value };
    if (path.endsWith("register")) {
      body.full_name = form.elements.full_name.value;
      body.marketing_consent = form.elements.marketing_consent.checked;
    }
    try {
      const result = await api(path, { method: "POST", body: JSON.stringify(body) });
      state.token = result.access_token;
      state.role = result.role;
      localStorage.setItem("dedunet_token", result.access_token);
      localStorage.setItem("dedunet_role", result.role);
      location.hash = "#/orders";
      route();
    } catch (error) {
      setBanner(error.message, "error");
    }
  }

  const login = el("form", { class: "form", onsubmit: (e) => submit(e, "/api/v1/auth/login") }, [
    el("h2", { text: "Sign in" }),
    el("label", { for: "le", text: "Email" }),
    el("input", { id: "le", name: "email", type: "email", required: "required", value: "customer@dedunet.example" }),
    el("label", { for: "lp", text: "Password" }),
    el("input", { id: "lp", name: "password", type: "password", required: "required", value: "demo-password-123" }),
    el("button", { class: "btn btn--primary", type: "submit", text: "Sign in" }),
  ]);

  const register = el("form", { class: "form", onsubmit: (e) => submit(e, "/api/v1/auth/register") }, [
    el("h2", { text: "Create an account" }),
    el("label", { for: "rn", text: "Full name" }),
    el("input", { id: "rn", name: "full_name", type: "text", required: "required" }),
    el("label", { for: "re", text: "Email" }),
    el("input", { id: "re", name: "email", type: "email", required: "required" }),
    el("label", { for: "rp", text: "Password (minimum 8 characters)" }),
    el("input", { id: "rp", name: "password", type: "password", minlength: "8", required: "required" }),
    el("label", { class: "check" }, [
      el("input", { id: "rc", name: "marketing_consent", type: "checkbox" }),
      " Send me occasional updates (optional)",
    ]),
    el("button", { class: "btn", type: "submit", text: "Create account" }),
  ]);

  render(el("h1", { text: "Account" }), el("div", { class: "two" }, [login, register]));
}

/* -------------------------------------------------------------------- stylist */

function viewStylist() {
  const output = el("div", { class: "recommendation", "aria-live": "polite" });

  const form = el(
    "form",
    {
      class: "form",
      onsubmit: async (event) => {
        event.preventDefault();
        const button = form.querySelector("button[type=submit]");
        button.disabled = true;
        output.replaceChildren(el("p", { class: "muted", text: "Thinking…" }));
        try {
          const result = await api("/api/v1/stylist/recommend", {
            method: "POST",
            body: JSON.stringify({
              occasion: form.elements.occasion.value,
              preferred_colors: form.elements.colors.value.split(",").map((s) => s.trim()).filter(Boolean),
              preferred_categories: form.elements.categories.value.split(",").map((s) => s.trim()).filter(Boolean),
              budget_eur: Number(form.elements.budget.value),
              notes: form.elements.notes.value,
            }),
          });
          const items = result.items || result.products || [];
          output.replaceChildren(
            el("h2", { class: "h6", text: "Suggested pieces" }),
            el("p", { text: result.rationale || "" }),
            el(
              "ul",
              { class: "list" },
              items.map((item) =>
                el("li", { text: `${item.name || item.slug} — ${money(item.price_minor_units ?? 0)}` })
              )
            ),
            el("p", {
              class: "disclaimer",
              text: "Deterministic rule-based suggestion computed from the local catalogue. It is not personalised advice and invents no product, price or stock.",
            })
          );
        } catch (error) {
          // The store must remain fully usable when the assistant is unavailable.
          output.replaceChildren(
            el("p", { class: "banner banner--error", text: `The stylist is unavailable right now. ${error.message}` }),
            el("p", {}, [el("a", { class: "btn", href: "#/catalog", text: "Browse the collection instead" })])
          );
        } finally {
          button.disabled = false;
        }
      },
    },
    [
      el("h1", { text: "Stylist" }),
      el("label", { for: "s-occ", text: "Occasion" }),
      el("input", { id: "s-occ", name: "occasion", type: "text", value: "summer dinner in Berlin", required: "required" }),
      el("label", { for: "s-col", text: "Preferred colours (comma separated)" }),
      el("input", { id: "s-col", name: "colors", type: "text", value: "Black, Sand" }),
      el("label", { for: "s-cat", text: "Preferred categories (comma separated)" }),
      el("input", { id: "s-cat", name: "categories", type: "text", value: "tops, bottoms" }),
      el("label", { for: "s-bud", text: "Budget (EUR)" }),
      el("input", { id: "s-bud", name: "budget", type: "number", min: "1", value: "200", required: "required" }),
      el("label", { for: "s-note", text: "Style notes" }),
      el("textarea", { id: "s-note", name: "notes", text: "modern eastern silhouette" }),
      el("button", { class: "btn btn--primary", type: "submit", text: "Recommend" }),
    ]
  );

  render(form, output);
}


/* ===================================================================== PLATFORM VIEWS
 *
 * DEDUNET is a personal fashion intelligence platform. The catalogue supports the styling
 * experience; it is no longer the product's identity. Every view below is built from the
 * design system, and every module that renders demonstration content carries the fixture
 * badge -- §29 requires that fixtures can never be mistaken for verified data.
 */

/** A section wrapper with a heading and an optional "see all" link. */
function section(title, children, { href = null, linkLabel = "See all", eyebrow = null,
                                    fixture = false, testid = null } = {}) {
  return el("section", { class: "ds-section", "data-testid": testid }, [
    el("div", { class: "ds-container" }, [
      el("div", { class: "ds-section__head" }, [
        el("div", {}, [
          eyebrow ? el("p", { class: "ds-eyebrow", text: eyebrow }) : null,
          el("h2", {}, [title, fixture ? " " : null, fixture ? window.DS.fixtureBadge() : null]),
        ]),
        href ? el("a", { class: "link-btn", href, text: linkLabel }) : null,
      ]),
      ...[].concat(children),
    ]),
  ]);
}

/** A Look card. Actions it cannot yet perform are disabled, never faked. */
function lookCard(look) {
  const canSave = DATA.SavedService.canSave;
  return el("article", { class: "card", "data-testid": "look-card" }, [
    el("div", { class: "card__media card__media--wide", "aria-hidden": "true" },
      [el("span", { class: "ds-eyebrow", text: look.occasion })]),
    el("div", { class: "card__body" }, [
      el("h3", { class: "card__title" }, [
        el("a", { class: "card__link", href: `#/look/${look.slug}`, text: look.title }),
      ]),
      el("p", { class: "card__meta", text: `${look.occasion} · ${look.style}` }),
      el("p", { class: "price price--sm", text: money(look.total_minor_units, look.currency) }),
    ]),
    el("div", { class: "card__foot" }, [
      window.DS.button("Save", {
        size: "sm",
        disabled: !canSave,
        testid: "look-save",
        describedBy: canSave ? null : "saved-unavailable",
      }),
      window.DS.linkButton("Ask Dido", `#/dido?look=${look.slug}`, { size: "sm" }),
    ]),
  ]);
}

/** A Brand card. Consumer language only -- the ownership type never reaches the page. */
function brandCard(brand) {
  return el("article", { class: "card", "data-testid": "brand-card" }, [
    el("div", { class: "card__media card__media--wide", "aria-hidden": "true" },
      [el("span", { class: "ds-eyebrow", text: brand.name.slice(0, 1) })]),
    el("div", { class: "card__body" }, [
      el("h3", { class: "card__title" }, [
        el("a", { class: "card__link", href: `#/brand/${brand.slug}`, text: brand.name }),
      ]),
      el("p", { class: "card__meta", text: DATA.BrandsService.consumerLabel(brand) }),
      brand.first_party ? null : window.DS.fixtureBadge("Shape demo"),
    ]),
  ]);
}

/** A capability that does not exist yet, said plainly. Never a fake result. */
function unavailableState(payload, { testid = null } = {}) {
  return el("div", { class: "state", "data-testid": testid || "unavailable-state" }, [
    el("p", { class: "state__title", text: `${payload.capability} is not built yet` }),
    el("p", { class: "state__body",
              text: `This arrives in ${payload.arrivesIn}. DEDUNET will not show you a ` +
                    `result it cannot actually produce.` }),
  ]);
}

/* ------------------------------------------------------------------------ home */

async function viewHome() {
  const brand = window.DEDUNET_BRAND || { name: "DEDUNET" };

  const hero = el("section", { class: "hero", "data-testid": "hero" }, [
    el("div", { class: "hero__art", "aria-hidden": "true", "data-hero-art": "true" }),
    el("div", { class: "hero__inner" }, [
      el("h1", { class: "hero__wordmark", text: brand.name }),
      el("p", { class: "hero__promise", text: "Personal fashion intelligence." }),
      el("p", { class: "hero__body",
                text: "DEDUNET helps you decide what to wear, then helps you find it. " +
                      "Tell Dido where you're going and it builds complete looks — " +
                      "explained, priced, and traceable to the brands that make them." }),
      el("div", { class: "hero__ctas" }, [
        window.DS.linkButton("Style me with Dido", "#/dido", { variant: "accent", testid: "cta-dido" }),
        window.DS.linkButton("Discover looks", "#/discover", { testid: "cta-discover" }),
      ]),
    ]),
  ]);

  const occasions = section(
    "What are you dressing for?",
    el("div", { class: "occasions", "data-testid": "occasions" },
      DATA.OCCASIONS.map((o) =>
        el("a", { class: "occasion", href: `#/dido?occasion=${o.slug}`, "data-testid": "occasion-card" }, [
          el("span", { class: "occasion__name", text: o.name }),
          el("span", { class: "occasion__hint", text: o.hint }),
        ]))),
    { testid: "occasion-picker" }
  );

  const [trending, editors, under100, under200, brands, forYou] = await Promise.all([
    DATA.LooksService.list({ category: "trending" }),
    DATA.LooksService.list({ category: "editors" }),
    DATA.LooksService.list({ maxMinorUnits: 10000 }),
    DATA.LooksService.list({ maxMinorUnits: 20000 }),
    DATA.BrandsService.list(),
    DATA.LooksService.forYou(),
  ]);

  const rail = (looks) => el("div", { class: "ds-rail" }, looks.map(lookCard));

  render(
    hero,
    occasions,
    /* "Selected for you" would be a personalisation claim, and no engine exists to make it
       true. §6 forbids that, so the module states what it is instead of pretending. */
    section("Looks selected for you", unavailableState(forYou, { testid: "for-you" }),
            { eyebrow: "Personalised", testid: "module-for-you" }),
    section("Trending looks", rail(trending), { href: "#/discover/trending", fixture: true, testid: "module-trending" }),
    section("Editor's picks", rail(editors), { href: "#/discover/editors", fixture: true, testid: "module-editors" }),
    section("Looks under €100", rail(under100), { href: "#/looks", fixture: true, testid: "module-under-100" }),
    section("Looks under €200", rail(under200), { href: "#/looks", fixture: true, testid: "module-under-200" }),
    section("Discover brands", el("div", { class: "ds-grid" }, brands.map(brandCard)),
            { href: "#/brands", testid: "module-brands" }),
    section("Meet Dido", el("div", { class: "dido-stage" }, [
      window.DS.didoFigure("idle"),
      el("div", {}, [
        el("p", { class: "ds-lede",
                  text: "Dido is DEDUNET's stylist. It asks what you're dressing for, " +
                        "what you already own and what you'd rather avoid — then builds " +
                        "looks it can explain." }),
        window.DS.linkButton("Start with Dido", "#/dido", { variant: "primary" }),
      ]),
    ]), { testid: "module-dido" }),
    section("For brands", el("div", {}, [
      el("p", { class: "ds-lede",
                text: "Reach customers through styling intelligence and fashion discovery, " +
                      "whether or not you already sell online." }),
      window.DS.linkButton("DEDUNET for Brands", "#/for-brands"),
    ]), { testid: "module-for-brands" })
  );
}

/* -------------------------------------------------------------------- discover */

async function viewDiscover(category = null) {
  loading();
  const looks = await DATA.LooksService.list({ category });
  const known = category ? DATA.DISCOVER_CATEGORIES[category] : null;

  if (category && !known) {
    return render(el("div", { class: "ds-container ds-section" },
      [window.DS.errorState({ status: 404 })]));
  }

  const groups = DATA.DISCOVER_GROUPS.map((group) =>
    el("div", { class: "ds-stack" }, [
      el("p", { class: "ds-eyebrow", text: group.title }),
      el("div", { class: "chip-row" }, group.slugs.map((slug) =>
        window.DS.chip(DATA.DISCOVER_CATEGORIES[slug].name, {
          href: `#/discover/${slug}`,
          pressed: slug === category,
          testid: "discover-chip",
        }))),
    ]));

  render(
    el("div", { class: "ds-container ds-section" }, [
      el("h1", { text: known ? known.name : "Discover" }),
      el("p", { class: "ds-lede",
                text: known ? known.blurb
                            : "Complete looks, grouped by the moment you're dressing for, " +
                              "the season and the way you like to dress." }),
      el("div", { class: "ds-stack", "data-testid": "discover-filters" }, groups),
    ]),
    section(known ? known.name : "All looks",
      looks.length
        ? el("div", { class: "ds-grid" }, looks.map(lookCard))
        : emptyState("No looks in this category yet.", "See all looks", "#/discover"),
      { fixture: looks.length > 0, testid: "discover-results" })
  );
}

/* ----------------------------------------------------------------------- looks */

async function viewLooks() {
  loading();
  const looks = await DATA.LooksService.list();
  render(
    el("div", { class: "ds-container ds-section" }, [
      el("h1", {}, ["Looks ", window.DS.fixtureBadge()]),
      el("p", { class: "ds-lede",
                text: "A look is a complete outfit with its reasoning attached — what it's " +
                      "for, why these pieces, and what it costs." }),
    ]),
    section("All looks", el("div", { class: "ds-grid" }, looks.map(lookCard)),
            { testid: "looks-list" })
  );
}

async function viewLook(slug) {
  loading({ skeleton: false });
  const look = await DATA.LooksService.get(slug);
  if (!look) {
    return render(el("div", { class: "ds-container ds-section" },
      [window.DS.errorState({ status: 404, message: "That look does not exist." })]));
  }

  const items = el("ul", { class: "look-items", "data-testid": "look-items" },
    look.items.map((item) =>
      el("li", { class: "look-item" }, [
        el("div", { class: "look-item__media", "aria-hidden": "true" }),
        el("div", {}, [
          el("p", { class: "look-item__slot", text: item.slot }),
          el("p", { class: "look-item__name", text: item.name }),
          el("p", { class: "card__meta", text: item.brand }),
        ]),
        el("p", { class: "price price--sm", text: money(item.price_minor_units, look.currency) }),
      ])));

  render(
    el("div", { class: "ds-container ds-section" }, [
      el("nav", { class: "crumbs", "aria-label": "Breadcrumb" },
        [el("a", { href: "#/looks", text: "← Looks" })]),
      el("div", { class: "detail" }, [
        el("div", { class: "detail__media" }, [
          el("div", { class: "card__media card__media--wide", "aria-hidden": "true" }),
        ]),
        el("div", { class: "detail__info" }, [
          window.DS.fixtureBadge("Demonstration look"),
          el("p", { class: "detail__brand", text: look.occasion }),
          el("h1", { class: "detail__title", text: look.title }),
          el("p", { class: "card__meta", text: look.style }),
          el("p", { text: look.rationale }),
          el("h2", { class: "ds-eyebrow", text: "The pieces" }),
          items,
          el("div", { class: "look-total" }, [
            el("span", { class: "ds-eyebrow", text: "Total" }),
            el("span", { class: "price", text: money(look.total_minor_units, look.currency) }),
          ]),
          el("div", { class: "ds-row" }, [
            window.DS.button("Save look", {
              disabled: !DATA.SavedService.canSave,
              describedBy: "saved-unavailable",
              testid: "look-save",
            }),
            window.DS.linkButton("Ask Dido about this", `#/dido?look=${look.slug}`),
          ]),
          el("p", {
            class: "ds-subtle", id: "saved-unavailable",
            text: "Saving arrives with the styling platform phase. Nothing is stored yet.",
          }),
          el("p", { class: "disclaimer",
                    text: "Demonstration look. Assembled to exercise the platform, not " +
                          "produced by a recommendation engine, and not personalised." }),
        ]),
      ]),
    ])
  );
}

/* ---------------------------------------------------------------------- brands */

async function viewBrands() {
  loading();
  const brands = await DATA.BrandsService.list();
  render(
    el("div", { class: "ds-container ds-section" }, [
      el("h1", { text: "Brands" }),
      el("p", { class: "ds-lede",
                text: "DEDUNET's own capsule, partner brands we host, and brands we list " +
                      "and link to. Only DEDUNET is live today." }),
    ]),
    section("All brands", el("div", { class: "ds-grid" }, brands.map(brandCard)),
            { testid: "brands-list" })
  );
}

async function viewBrand(slug) {
  loading({ skeleton: false });
  const brand = await DATA.BrandsService.get(slug);
  if (!brand) {
    return render(el("div", { class: "ds-container ds-section" },
      [window.DS.errorState({ status: 404, message: "That brand does not exist." })]));
  }

  /* Commerce language is derived from the route, never from the ownership type. §11: the
     technical terms must not reach a consumer, and §21 of the architecture: a route is
     where the money goes, which is a different question from who owns the data. */
  const ROUTE_COPY = {
    HOSTED: "Available on DEDUNET",
    EXTERNAL: "Purchase on the brand's own site",
    REFERRAL: "View at the brand",
    NON_PURCHASABLE: "Not available to buy",
  };

  render(
    el("div", { class: "ds-container ds-section" }, [
      el("nav", { class: "crumbs", "aria-label": "Breadcrumb" },
        [el("a", { href: "#/brands", text: "← Brands" })]),
      el("div", { class: "detail" }, [
        el("div", { class: "detail__media" },
          [el("div", { class: "card__media card__media--wide", "aria-hidden": "true" })]),
        el("div", { class: "detail__info" }, [
          brand.first_party ? null : window.DS.fixtureBadge("Shape demo"),
          el("p", { class: "detail__brand", text: DATA.BrandsService.consumerLabel(brand) }),
          el("h1", { class: "detail__title", text: brand.name }),
          el("p", { text: brand.story }),
          el("p", { class: "availability availability--preview",
                    "data-testid": "brand-commerce",
                    text: ROUTE_COPY[brand.commerce_route] || "Not available to buy" }),
          brand.product_count
            ? window.DS.linkButton(`See ${brand.product_count} pieces`, "#/shop")
            : el("p", { class: "ds-subtle", text: "No catalogue on DEDUNET yet." }),
          el("p", { class: "disclaimer",
                    text: brand.first_party
                      ? "DEDUNET's own prototype capsule. Material and origin fields are " +
                        "stated intentions, not substantiated claims."
                      : "Placeholder illustrating how this kind of brand would appear. " +
                        "No such brand exists and none has been approached." }),
        ]),
      ]),
    ])
  );
}

/* ----------------------------------------------------------------------- saved */

async function viewSaved() {
  loading({ skeleton: false });
  const [looks, products, brands] = await Promise.all([
    DATA.SavedService.looks(),
    DATA.SavedService.products(),
    DATA.SavedService.brands(),
  ]);
  render(
    el("div", { class: "ds-container ds-section" }, [
      el("h1", { text: "Saved" }),
      el("p", { class: "ds-lede",
                text: "Looks, products and brands you keep. Nothing is stored yet — " +
                      "persistence arrives with the styling platform." }),
      el("div", { class: "ds-stack" }, [
        el("section", {}, [el("h2", { text: "Saved looks" }),
                           unavailableState(looks, { testid: "saved-looks" })]),
        el("section", {}, [el("h2", { text: "Saved products" }),
                           unavailableState(products, { testid: "saved-products" })]),
        el("section", {}, [el("h2", { text: "Saved brands" }),
                           unavailableState(brands, { testid: "saved-brands" })]),
      ]),
    ])
  );
}

/* -------------------------------------------------------------------- my style */

async function viewMyStyle() {
  loading({ skeleton: false });
  const profile = await DATA.StyleProfileService.get();
  render(
    el("div", { class: "ds-container ds-section" }, [
      el("nav", { class: "crumbs", "aria-label": "Breadcrumb" },
        [el("a", { href: "#/account", text: "← Account" })]),
      el("h1", { text: "My Style" }),
      el("p", { class: "ds-lede",
                text: "Your Style DNA is what lets Dido recommend for you rather than at " +
                      "you. You will be able to see, edit and delete every part of it." }),
      unavailableState(profile, { testid: "style-profile" }),
      el("div", { class: "ds-grid ds-grid--tight", "data-testid": "style-sections" },
        DATA.StyleProfileService.sections.map((s) =>
          el("article", { class: "card" }, [
            el("div", { class: "card__body" }, [
              el("h2", { class: "card__title", text: s.name }),
              el("p", { class: "card__meta", text: s.hint }),
              el("p", { class: "ds-subtle", text: "Not collected yet" }),
            ]),
          ]))),
      el("p", { class: "disclaimer",
                text: "DEDUNET stores nothing about your style today. When it does, this " +
                      "page is where you view, edit, delete and switch it off." }),
    ])
  );
}

/* --------------------------------------------------------------------- dido */

/**
 * The Dido experience shell.
 *
 * Phase 2 builds the SURFACE: character, states, conversation layout, message and option
 * components, accessibility and reduced motion. There is no orchestration behind it, and
 * the shell says so rather than scripting a fake exchange. §5 is explicit: prefer
 * functional navigation over fake AI.
 */
async function viewDido() {
  const params = new URLSearchParams((location.hash.split("?")[1] || ""));
  const session = await DATA.DidoService.openSession(params.get("occasion"));

  const figure = window.DS.didoFigure("asking");
  const animator = window.DS.didoAnimator(figure);

  const log = el("div", { class: "dido-log", "data-testid": "dido-log" }, [
    window.DS.didoMessage(session.opening),
    window.DS.didoMessage(
      "I can't build looks yet — my styling engine arrives in a later platform phase. " +
      "Until then, browse what the editorial desk has put together."
    ),
  ]);

  /* Choosing an occasion moves the character through its states. This is the animation
     seam being exercised, not a simulated answer: no recommendation is produced. */
  const options = el("div", { class: "dido-options", "data-testid": "dido-options" },
    DATA.OCCASIONS.slice(0, 6).map((o) =>
      window.DS.didoOption(o.name, {
        hint: o.hint,
        testid: "dido-option",
        onclick: () => {
          log.appendChild(window.DS.didoMessage(o.name, { from: "user" }));
          animator.setState("thinking");
          const thinking = window.DS.didoThinking();
          log.appendChild(thinking);
          window.DS.announce("Dido is thinking");
          setTimeout(() => {
            thinking.remove();
            animator.setState("presenting");
            log.appendChild(window.DS.didoMessage(
              `${o.name}. Noted — but I can't style it yet. ` +
              `Here is what the editorial desk has for ${o.name.toLowerCase()}.`
            ));
            log.appendChild(el("p", { class: "ds-row" },
              [window.DS.linkButton(`See ${o.name} looks`, "#/discover", { size: "sm" })]));
            window.DS.announce(`Dido replied about ${o.name}`);
          }, 600);
        },
      })));

  render(
    el("div", { class: "ds-container ds-section" }, [
      el("h1", { class: "sr-only", text: "Style with Dido" }),
      el("div", { class: "dido-stage" }, [
        el("div", {}, [
          figure,
          el("p", { class: "ds-eyebrow", style: "text-align:center;margin-top:1rem", text: "Dido Net" }),
        ]),
        el("div", { class: "dido-convo", "data-testid": "dido-convo" }, [
          log,
          el("h2", { class: "ds-eyebrow", text: "Where are we going?" }),
          options,
          el("p", { class: "ds-subtle", "data-testid": "dido-disclosure",
                    text: "Styling intelligence arrives in a later platform phase. " +
                          "Dido will not invent a recommendation it cannot justify." }),
        ]),
      ]),
    ])
  );
}

/* ----------------------------------------------------------------- for brands */

function viewForBrands() {
  const available = [
    "A hosted brand page on dedunet.com",
    "Your catalogue, media and story presented editorially",
    "Discovery through looks and occasions",
  ];
  const later = [
    "Recommendation exposure through Dido",
    "Connected catalogue sync from Shopify, WooCommerce or a feed",
    "Hosted checkout and order routing",
    "Analytics on impressions, clicks and conversion",
    "Subscription plans and billing",
  ];

  render(
    el("div", { class: "ds-container ds-section" }, [
      el("p", { class: "ds-eyebrow", text: "DEDUNET for Brands" }),
      el("h1", { text: "Reach customers through styling intelligence." }),
      el("p", { class: "ds-lede",
                text: "People come to DEDUNET to decide what to wear. Brands appear at the " +
                      "moment that decision is being made — inside a complete look, with " +
                      "the reasoning attached." }),
      el("div", { class: "pitch", "data-testid": "for-brands-pitch" }, [
        el("div", { class: "pitch__item" }, [
          el("h3", { text: "If you already sell online" }),
          el("p", { text: "Connect your catalogue. DEDUNET handles discovery and styling; " +
                          "the sale stays on your own site." }),
        ]),
        el("div", { class: "pitch__item" }, [
          el("h3", { text: "If you have no website" }),
          el("p", { text: "DEDUNET becomes your commerce surface: brand page, catalogue, " +
                          "media, inventory and checkout, hosted here. This is a core " +
                          "capability, not an edge case." }),
        ]),
      ]),
      el("h2", { text: "What is available now" }),
      el("ul", { class: "status-list", "data-testid": "brands-available" },
        available.map((t) => el("li", {}, [window.DS.badge("Available", "success"), el("span", { text: t })]))),
      el("h2", { text: "What is coming later" }),
      el("ul", { class: "status-list", "data-testid": "brands-later" },
        later.map((t) => el("li", {}, [window.DS.badge("Later", "preview"), el("span", { text: t })]))),
      el("div", { class: "alert alert--warning", "data-testid": "for-brands-honesty" }, [
        el("p", { text: "Merchant onboarding is not open. DEDUNET is not accepting brands " +
                        "yet, has no commercial agreements with any brand, and the merchant " +
                        "platform described above is not built. This page explains the " +
                        "intended product, not a live service." }),
      ]),
    ])
  );
}

/* -------------------------------------------------------------------- routing */

const ROUTES = [
  [/^#\/?$/, viewHome],
  [/^#\/home$/, viewHome],
  [/^#\/dido/, viewDido],
  [/^#\/discover\/([\w-]+)$/, viewDiscover],
  [/^#\/discover$/, () => viewDiscover(null)],
  [/^#\/looks$/, viewLooks],
  [/^#\/look\/([\w-]+)$/, viewLook],
  [/^#\/brands$/, viewBrands],
  [/^#\/brand\/([\w-]+)$/, viewBrand],
  [/^#\/saved$/, viewSaved],
  [/^#\/my-style$/, viewMyStyle],
  [/^#\/for-brands$/, viewForBrands],
  [/^#\/product\/(.+)$/, viewProduct],
  [/^#\/order\/(.+)$/, viewOrder],
  [/^#\/shop/, viewCatalog],
  [/^#\/catalog/, viewCatalog],
  [/^#\/stylist$/, viewStylist],
  [/^#\/cart$/, viewCart],
  [/^#\/checkout$/, viewCheckout],
  [/^#\/orders$/, viewOrders],
  [/^#\/account$/, viewAccount],
];

function route() {
  setBanner("");
  /* Home, not the catalogue. DEDUNET is a fashion intelligence platform whose landing
     experience is styling; the shop is one destination within it rather than the front
     door. This single default is the difference between "clothing store with extras" and
     "platform with a shop". */
  const hash = location.hash || "#/";
  for (const [pattern, handler] of ROUTES) {
    const match = hash.match(pattern);
    if (match) {
      Promise.resolve(handler(match[1])).catch((error) =>
        // A route must never fail silently and leave a blank page.
        render(el("div", { class: "ds-container ds-section" },
          [window.DS.errorState(error, { onRetry: () => route() })]))
      );
      markActiveNav();
      return;
    }
  }
  render(el("div", { class: "ds-container ds-section" }, [
    window.DS.errorState({ status: 404, message: "That page does not exist." }),
    el("p", { class: "ds-row" }, [window.DS.linkButton("Back to DEDUNET", "#/")]),
  ]));
  markActiveNav();
}

/**
 * Mark the current route in both navigations.
 *
 * `aria-current="page"` is the source of truth and the CSS keys off it, so the visual
 * highlight and what a screen reader announces are the same fact rather than two that can
 * drift apart.
 */
function markActiveNav() {
  const hash = location.hash || "#/";
  for (const link of document.querySelectorAll("[data-route]")) {
    const prefix = link.getAttribute("data-route");
    const active = prefix === "#/" ? hash === "#/" || hash === "" : hash.startsWith(prefix);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

/* Published for the jsdom test harnesses, which drive these directly rather than through
   a browser. Classic-script scope already puts function declarations on `window`; this is
   an explicit, greppable list of what the tests are entitled to depend on. */
window.viewHome = viewHome;
window.viewDiscover = viewDiscover;
window.viewLooks = viewLooks;
window.viewLook = viewLook;
window.viewBrands = viewBrands;
window.viewBrand = viewBrand;
window.viewSaved = viewSaved;
window.viewMyStyle = viewMyStyle;
window.viewDido = viewDido;
window.viewForBrands = viewForBrands;
window.route = route;
window.markActiveNav = markActiveNav;

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", route);
/* Once, at boot: the mode is a property of the deployment, not of the page being viewed.
   Not awaited by `route`, so a slow or unreachable API delays the disclosure but never the
   catalogue.

   The promise is kept because two views DO need the answer -- the empty order history and
   the product page's purchase gate -- and they wait on this one request through
   `awaitCommerceMode`, bounded, rather than issuing their own. */
window.addEventListener("DOMContentLoaded", () => {
  modeReady = loadCommerceNotice();
});
