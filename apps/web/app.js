/**
 * DEDUNET storefront — prototype build.
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

const MINOR_UNIT_EXPONENTS = { EUR: 2 };
const CURRENCY_SYMBOLS = { EUR: "€" };

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
};

/* ----------------------------------------------------------------- formatting */

function money(minorUnits, currency = "EUR") {
  const exponent = MINOR_UNIT_EXPONENTS[currency];
  if (exponent === undefined || !Number.isInteger(minorUnits)) {
    return `${minorUnits} ${currency}`;
  }
  const sign = minorUnits < 0 ? "-" : "";
  const digits = String(Math.abs(minorUnits)).padStart(exponent + 1, "0");
  const major = digits.slice(0, digits.length - exponent);
  const minor = digits.slice(digits.length - exponent);
  const symbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;
  return `${sign}${symbol}${major}.${minor}`;
}

/* ------------------------------------------------------------------ DOM utils */

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value; // never innerHTML
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2), value);
    } else node.setAttribute(key, String(value));
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

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

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: headers(options.headers),
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
    throw error;
  }
  return body;
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

function loading() {
  render(el("p", { class: "muted", text: "Loading…" }));
}

function emptyState(message, actionLabel, actionHref) {
  return el("div", { class: "empty" }, [
    el("p", { class: "muted", text: message }),
    actionLabel ? el("a", { class: "btn", href: actionHref, text: actionLabel }) : null,
  ]);
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

  const addButton = el("button", {
    class: "btn btn--primary",
    type: "button",
    text: "Add to cart",
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

async function viewOrders() {
  if (!state.token) {
    location.hash = "#/account";
    return;
  }
  loading();
  const orders = await api("/api/v1/me/orders").catch(() => []);
  if (!orders.length) return render(emptyState("You have no orders yet.", "Browse the collection", "#/catalog"));
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
        onclick: () => {
          state.token = "";
          state.role = "";
          localStorage.removeItem("dedunet_token");
          localStorage.removeItem("dedunet_role");
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

/* -------------------------------------------------------------------- routing */

const ROUTES = [
  [/^#\/product\/(.+)$/, viewProduct],
  [/^#\/order\/(.+)$/, viewOrder],
  [/^#\/catalog/, viewCatalog],
  [/^#\/stylist$/, viewStylist],
  [/^#\/cart$/, viewCart],
  [/^#\/checkout$/, viewCheckout],
  [/^#\/orders$/, viewOrders],
  [/^#\/account$/, viewAccount],
];

function route() {
  setBanner("");
  const hash = location.hash || "#/catalog";
  for (const [pattern, handler] of ROUTES) {
    const match = hash.match(pattern);
    if (match) {
      Promise.resolve(handler(match[1])).catch((error) =>
        // A route must never fail silently and leave a blank page.
        render(emptyState(`Something went wrong. ${error.message}`, "Back to collection", "#/catalog"))
      );
      return;
    }
  }
  render(emptyState("That page does not exist.", "Back to collection", "#/catalog"));
}

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", route);
