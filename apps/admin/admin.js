/**
 * DEDUNET operations portal.
 *
 * Same XSS discipline as the storefront: every node is created with
 * `document.createElement` and every string is inserted as `textContent`. There is no
 * `innerHTML` in this file.
 *
 * Every destructive or financially significant action (fulfil, cancel, refund, stock
 * adjustment) requires an explicit confirmation, reports success or failure visibly,
 * and produces a server-side audit record. None of them complete silently.
 */

/* One definition of where the API lives, resolved by api-config.js from the generated
   config.js. Previously computed inline here against a hard-coded :18000, which meant the
   staging portal asked a port nothing listens on and every request failed as
   "Failed to fetch" before an administrator could sign in. No deployment's port belongs in
   application logic. */
const API_BASE = window.DedunetAdminConfig.apiBase();

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

const state = { token: localStorage.getItem("dedunet_admin_token") || "" };

function money(minorUnits, currency = "EUR") {
  const exponent = MINOR_UNIT_EXPONENTS[currency];
  if (exponent === undefined || !Number.isInteger(minorUnits)) return `${minorUnits} ${currency}`;
  const sign = minorUnits < 0 ? "-" : "";
  const digits = String(Math.abs(minorUnits)).padStart(exponent + 1, "0");
  const major = digits.slice(0, digits.length - exponent);
  const minor = digits.slice(digits.length - exponent);
  return `${sign}${CURRENCY_SYMBOLS[currency] ?? currency + " "}${major}.${minor}`;
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, String(value));
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

function setBanner(message, kind = "info") {
  const host = document.getElementById("banner");
  host.replaceChildren();
  if (message) host.appendChild(el("div", { class: `banner banner--${kind}`, role: "status", text: message }));
}

function render(...nodes) {
  document.getElementById("main").replaceChildren(...nodes.filter(Boolean));
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const raw = await response.text();
  let body = null;
  try {
    body = raw ? JSON.parse(raw) : null;
  } catch {
    body = { detail: raw };
  }
  if (!response.ok) {
    const error = new Error(
      (body && typeof body.detail === "string" && body.detail) || `Request failed (${response.status})`
    );
    error.status = response.status;
    throw error;
  }
  return body;
}

function requireAuth() {
  if (!state.token) {
    location.hash = "#/login";
    return false;
  }
  return true;
}

/** Run an action behind a confirmation, and always report the outcome. */
async function guarded(question, action, successMessage) {
  if (!window.confirm(question)) return false;
  try {
    await action();
    setBanner(successMessage, "ok");
    return true;
  } catch (error) {
    setBanner(`Failed: ${error.message}`, "error");
    return false;
  }
}

/* ---------------------------------------------------------------------- views */

function viewLogin() {
  const form = el("form", { class: "form", onsubmit: submit }, [
    el("h1", { text: "Operations sign in" }),
    el("label", { for: "e", text: "Email" }),
    el("input", { id: "e", name: "email", type: "email", required: "required", value: "admin@dedunet.example" }),
    el("label", { for: "p", text: "Password" }),
    el("input", { id: "p", name: "password", type: "password", required: "required", value: "demo-password-123" }),
    el("button", { class: "btn btn--primary", type: "submit", text: "Sign in" }),
    el("p", { class: "disclaimer", text: "Local demonstration credentials against a fictional dataset." }),
  ]);

  async function submit(event) {
    event.preventDefault();
    setBanner("");
    try {
      const result = await api("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: form.elements.email.value,
          password: form.elements.password.value,
        }),
      });
      if (result.role !== "admin") {
        setBanner("That account does not have the administrator role.", "error");
        return;
      }
      state.token = result.access_token;
      localStorage.setItem("dedunet_admin_token", result.access_token);
      location.hash = "#/orders";
      route();
    } catch (error) {
      setBanner(error.message, "error");
    }
  }

  render(form);
}

async function viewOrders() {
  if (!requireAuth()) return;
  render(el("p", { class: "muted", text: "Loading orders…" }));

  let orders;
  try {
    orders = await api("/api/v1/admin/orders");
  } catch (error) {
    if (error.status === 401 || error.status === 403) return signOut();
    return render(el("p", { class: "banner banner--error", text: error.message }));
  }

  if (!orders.length) {
    return render(el("h1", { text: "Orders" }), el("p", { class: "muted", text: "No orders yet." }));
  }

  const rows = orders.map((order) =>
    el("tr", {}, [
      el("td", {}, [
        el("strong", { text: order.order_number }),
        el("br"),
        el("span", { class: "muted", text: order.lines.map((l) => `${l.quantity}× ${l.sku}`).join(", ") }),
      ]),
      el("td", {}, [el("span", { class: "tag tag--ok", text: order.status })]),
      el("td", { text: money(order.total_minor_units, order.currency) }),
      el("td", { text: order.shipments.length ? order.shipments[0].tracking_number : "—" }),
      el("td", {}, [
        order.status === "paid"
          ? el("button", {
              class: "btn btn--quiet",
              type: "button",
              text: "Fulfil",
              onclick: async () => {
                const done = await guarded(
                  `Fulfil ${order.order_number}? This commits stock and cannot be undone.`,
                  () => api(`/api/v1/admin/orders/${order.order_number}/fulfil`, { method: "POST" }),
                  `${order.order_number} fulfilled and marked shipped.`
                );
                if (done) viewOrders();
              },
            })
          : null,
        ["paid", "pending_payment", "fulfilling"].includes(order.status)
          ? el("button", {
              class: "btn btn--quiet",
              type: "button",
              text: "Cancel",
              onclick: async () => {
                const done = await guarded(
                  `Cancel ${order.order_number}? Reserved stock is released.`,
                  () => api(`/api/v1/admin/orders/${order.order_number}/cancel`, { method: "POST" }),
                  `${order.order_number} cancelled.`
                );
                if (done) viewOrders();
              },
            })
          : null,
      ]),
    ])
  );

  render(
    el("h1", { text: "Orders" }),
    el("table", { class: "table" }, [
      el("thead", {}, [
        el("tr", {}, ["Order", "Status", "Total", "Tracking", "Actions"].map((h) => el("th", { text: h }))),
      ]),
      el("tbody", {}, rows),
    ])
  );
}

async function viewInventory() {
  if (!requireAuth()) return;
  render(el("p", { class: "muted", text: "Loading inventory…" }));

  let products;
  try {
    products = await api("/api/v1/catalog/products");
  } catch (error) {
    return render(el("p", { class: "banner banner--error", text: error.message }));
  }

  /**
   * Product name plus the states that explain its commercial status.
   *
   * A DEDUNET prototype has a price and zero stock, which is indistinguishable from an
   * ordinary sold-out line at a glance. Labelling it stops an operator "correcting" it by
   * adding inventory to something that must not be sold.
   */
  function productLabel(product) {
    if (!product.external_product_id) return product.name;
    const flags = [product.external_product_id, "PREVIEW — NOT SELLABLE"];
    if (product.evidence_status) flags.push(`evidence ${product.evidence_status}`);
    return `${product.name}  [${flags.join(" · ")}]`;
  }

  const rows = [];
  for (const product of products) {
    for (const variant of product.variants) {
      rows.push(
        el("tr", {}, [
          // Operators need to see WHY a row is unpurchasable before they try to adjust its
          // stock. A prototype that looks like ordinary out-of-stock inventory invites
          // someone to "fix" it by adding units.
          el("td", { text: productLabel(product) }),
          el("td", { text: variant.sku }),
          el("td", { text: `${variant.size} · ${variant.color}` }),
          el("td", { text: String(variant.available) }),
          el("td", {}, [
            el(
              "form",
              {
                class: "inline",
                onsubmit: async (event) => {
                  event.preventDefault();
                  const delta = Number(event.target.elements.delta.value);
                  const reason = event.target.elements.reason.value.trim();
                  if (!Number.isInteger(delta) || delta === 0) {
                    return setBanner("Enter a non-zero whole number.", "error");
                  }
                  if (!reason) return setBanner("A reason is required for an adjustment.", "error");
                  const done = await guarded(
                    `Adjust ${variant.sku} by ${delta}? This is audited.`,
                    () =>
                      api(`/api/v1/admin/variants/${variant.id}/stock`, {
                        method: "POST",
                        body: JSON.stringify({ delta, reason }),
                      }),
                    `${variant.sku} adjusted by ${delta}.`
                  );
                  if (done) viewInventory();
                },
              },
              [
                el("label", { class: "sr-only", for: `d-${variant.id}`, text: "Delta" }),
                el("input", { id: `d-${variant.id}`, name: "delta", type: "number", value: "0", step: "1" }),
                el("label", { class: "sr-only", for: `r-${variant.id}`, text: "Reason" }),
                el("input", { id: `r-${variant.id}`, name: "reason", type: "text", placeholder: "Reason" }),
                el("button", { class: "btn btn--quiet", type: "submit", text: "Apply" }),
              ]
            ),
          ]),
        ])
      );
    }
  }

  render(
    el("h1", { text: "Inventory" }),
    el("table", { class: "table" }, [
      el("thead", {}, [
        el("tr", {}, ["Product", "SKU", "Variant", "Available", "Adjust"].map((h) => el("th", { text: h }))),
      ]),
      el("tbody", {}, rows),
    ])
  );
}

function viewNewProduct() {
  if (!requireAuth()) return;

  const form = el("form", { class: "form", onsubmit: submit }, [
    el("h1", { text: "New product" }),
    el("label", { for: "slug", text: "Slug (lowercase, hyphens)" }),
    el("input", { id: "slug", name: "slug", type: "text", pattern: "[a-z0-9-]+", required: "required" }),
    el("label", { for: "name", text: "Name" }),
    el("input", { id: "name", name: "name", type: "text", required: "required" }),
    el("label", { for: "cat", text: "Category" }),
    el("input", { id: "cat", name: "category", type: "text", value: "tops", required: "required" }),
    el("label", { for: "desc", text: "Description" }),
    el("textarea", { id: "desc", name: "description" }),
    el("label", { for: "sku", text: "First variant SKU" }),
    el("input", { id: "sku", name: "sku", type: "text", required: "required" }),
    el("label", { for: "size", text: "Size" }),
    el("input", { id: "size", name: "size", type: "text", value: "M", required: "required" }),
    el("label", { for: "color", text: "Colour" }),
    el("input", { id: "color", name: "color", type: "text", value: "Ink", required: "required" }),
    el("label", { for: "price", text: "Price in minor units (e.g. 5900 = €59.00)" }),
    el("input", { id: "price", name: "price", type: "number", min: "1", step: "1", value: "5900", required: "required" }),
    el("label", { for: "stock", text: "Opening stock" }),
    el("input", { id: "stock", name: "stock", type: "number", min: "0", step: "1", value: "0", required: "required" }),
    el("label", { class: "check" }, [
      el("input", { id: "active", name: "is_active", type: "checkbox" }),
      " Publish immediately (leave unchecked to create as a draft)",
    ]),
    el("button", { class: "btn btn--primary", type: "submit", text: "Create product" }),
    el("p", {
      class: "disclaimer",
      text: "Prices are entered in integer minor units because that is the authoritative storage format. Do not enter a decimal.",
    }),
  ]);

  async function submit(event) {
    event.preventDefault();
    setBanner("");
    try {
      const created = await api("/api/v1/admin/catalog/products", {
        method: "POST",
        body: JSON.stringify({
          slug: form.elements.slug.value.trim(),
          name: form.elements.name.value.trim(),
          category: form.elements.category.value.trim(),
          description: form.elements.description.value.trim(),
          is_active: form.elements.is_active.checked,
          variants: [
            {
              sku: form.elements.sku.value.trim(),
              size: form.elements.size.value.trim(),
              color: form.elements.color.value.trim(),
              price_minor_units: Number(form.elements.price.value),
              on_hand: Number(form.elements.stock.value),
            },
          ],
        }),
      });
      setBanner(`Created ${created.slug}.`, "ok");
      form.reset();
    } catch (error) {
      setBanner(error.message, "error");
    }
  }

  render(form);
}

function viewAudit() {
  if (!requireAuth()) return;
  // The audit trail is written server-side for every privileged action. A read API is
  // not yet exposed; this page states that plainly rather than showing an empty table
  // that would imply nothing was recorded.
  render(
    el("h1", { text: "Audit" }),
    el("p", {
      text: "Every privileged action is recorded server-side in the audit_logs table with actor, action, entity, correlation ID and timestamp.",
    }),
    el("p", { class: "muted", text: "A read-only audit API is not implemented yet, so this page cannot list entries. Query the audit_logs table directly." }),
    el("p", { class: "disclaimer", text: "This page is intentionally empty of data rather than showing a placeholder table that would suggest no actions were logged." })
  );
}

function signOut() {
  state.token = "";
  localStorage.removeItem("dedunet_admin_token");
  location.hash = "#/login";
  route();
}

/* -------------------------------------------------------------------- routing */

const ROUTES = [
  [/^#\/login$/, viewLogin],
  [/^#\/orders$/, viewOrders],
  [/^#\/inventory$/, viewInventory],
  [/^#\/products$/, viewNewProduct],
  [/^#\/audit$/, viewAudit],
];

function route() {
  setBanner("");
  const who = document.getElementById("who");
  if (who) who.textContent = state.token ? "Sign out" : "Sign in";
  if (who) who.onclick = state.token ? (e) => { e.preventDefault(); signOut(); } : null;

  const hash = location.hash || (state.token ? "#/orders" : "#/login");
  for (const [pattern, handler] of ROUTES) {
    if (pattern.test(hash)) {
      Promise.resolve(handler()).catch((error) =>
        render(el("p", { class: "banner banner--error", text: `Something went wrong. ${error.message}` }))
      );
      return;
    }
  }
  location.hash = state.token ? "#/orders" : "#/login";
}

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", route);
