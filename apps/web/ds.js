/**
 * DEDUNET design system — runtime primitives and component library.
 *
 * SECURITY (preserves SB-RISK-003 closure)
 * ----------------------------------------
 * Every node here is built with `document.createElement` and every string is inserted as
 * `textContent`. There is no markup sink in this file and a test asserts that. The one
 * exception is `svg()`, which builds SVG through `createElementNS` from a fixed internal
 * shape table — it never accepts caller markup.
 *
 * NO BUILD STEP
 * -------------
 * nginx serves `apps/web` verbatim from a read-only filesystem, so this is a classic
 * script that publishes onto `window`, not an ES module. That is a deliberate constraint,
 * not an oversight: module scope would also break the jsdom harnesses that drive these
 * functions directly, which are what the accepted storefront behaviour is tested through.
 */

/* ------------------------------------------------------------------ element factory */

/**
 * Build an element.
 *
 * `text` sets textContent — never innerHTML. `null`/`undefined` attributes and children
 * are skipped so a caller can write `disabled: cond ? "disabled" : null` inline rather
 * than branching around the whole call.
 */
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value; // never innerHTML
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2), value);
    } else node.setAttribute(key, String(value));
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

/** Build an SVG node. Separate from `el` because SVG needs its own namespace. */
function svgEl(tag, attrs = {}, children = []) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    node.setAttribute(key, String(value));
  }
  for (const child of [].concat(children)) {
    if (child) node.appendChild(child);
  }
  return node;
}

/* ------------------------------------------------------------------ icons
 *
 * A fixed table of path data. Icons are decorative by default (`aria-hidden`) because the
 * control around them carries the accessible name — an icon that announces itself as well
 * makes every button read its label twice.
 */

const ICON_PATHS = {
  home: "M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z",
  discover: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm3.5 6.5-2 5-5 2 2-5z",
  dido: "M12 3c-2.2 0-4 1.8-4 4v2H6v12h12V9h-2V7c0-2.2-1.8-4-4-4zm0 2a2 2 0 0 1 2 2v2h-4V7a2 2 0 0 1 2-2z",
  saved: "M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z",
  account: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-4 0-7 2.2-7 5v1h14v-1c0-2.8-3-5-7-5z",
  search: "M10 4a6 6 0 1 0 3.5 10.9l4.8 4.8 1.4-1.4-4.8-4.8A6 6 0 0 0 10 4zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z",
  bag: "M6 7h12l1 14H5zM9 7a3 3 0 0 1 6 0",
  close: "M6 6l12 12M18 6L6 18",
  chevron: "M9 6l6 6-6 6",
};

/** An icon. `title` makes it meaningful; without one it is hidden from assistive tech. */
function icon(name, { title = null, size = 24 } = {}) {
  const path = ICON_PATHS[name];
  if (!path) return null;
  const children = [
    svgEl("path", {
      d: path,
      fill: name === "close" || name === "chevron" ? "none" : "currentColor",
      stroke: name === "close" || name === "chevron" ? "currentColor" : "none",
      "stroke-width": 2,
      "stroke-linecap": "round",
    }),
  ];
  if (title) children.unshift(svgEl("title", {}, [document.createTextNode(title)]));
  return svgEl(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: size,
      height: size,
      role: title ? "img" : "presentation",
      "aria-hidden": title ? null : "true",
      focusable: "false",
    },
    children
  );
}

/* ------------------------------------------------------------------ money
 *
 * The API sends authoritative INTEGER MINOR UNITS. Formatted with integer and string
 * operations only — no division, so no binary float ever touches an amount.
 * Contract: docs/side-b/SIDE_B_MONEY_CONTRACT.md.
 */

const MINOR_UNIT_EXPONENTS = { EUR: 2 };
const CURRENCY_SYMBOLS = { EUR: "€" };

/* Moved verbatim from app.js. Behaviour is deliberately unchanged, including the
   degradation path: an unknown currency or a non-integer amount renders as
   "<value> <currency>" rather than throwing. A formatter that throws inside a render turns
   one bad price into a blank page, and this one is on the path that shows customers what
   things cost. */
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

/* ------------------------------------------------------------------ components */

function button(label, { variant = "", size = "", onclick = null, disabled = false,
                        describedBy = null, testid = null, busy = false } = {}) {
  const classes = ["btn"];
  if (variant) classes.push(`btn--${variant}`);
  if (size) classes.push(`btn--${size}`);
  return el("button", {
    class: classes.join(" "),
    type: "button",
    "data-testid": testid,
    disabled: disabled ? "disabled" : null,
    "aria-describedby": describedBy,
    "aria-busy": busy ? "true" : null,
    onclick: disabled ? null : onclick,
  }, [
    busy ? el("span", { class: "btn__spinner", "aria-hidden": "true" }) : null,
    label,
  ]);
}

function linkButton(label, href, { variant = "", size = "", testid = null } = {}) {
  const classes = ["btn"];
  if (variant) classes.push(`btn--${variant}`);
  if (size) classes.push(`btn--${size}`);
  return el("a", { class: classes.join(" "), href, "data-testid": testid, text: label });
}

function badge(label, tone = "") {
  return el("span", { class: tone ? `badge badge--${tone}` : "badge", text: label });
}

/**
 * The fixture marker.
 *
 * §29 requires demonstration content to be impossible to mistake for verified production
 * data. Every module rendering non-API content carries this, and a test asserts it is
 * present wherever fixtures are.
 */
function fixtureBadge(kind = "Demo content") {
  return el("span", {
    class: "badge badge--fixture",
    "data-testid": "fixture-badge",
    text: kind,
  });
}

function chip(label, { href = null, pressed = null, onclick = null, testid = null } = {}) {
  const attrs = {
    class: "chip",
    "data-testid": testid,
    "aria-pressed": pressed === null ? null : String(pressed),
  };
  if (href) return el("a", { ...attrs, href, text: label });
  return el("button", { ...attrs, type: "button", onclick, text: label });
}

function field(labelText, control, { hint = null, error = null, id = null } = {}) {
  const controlId = id || control.id || `f-${Math.random().toString(36).slice(2, 9)}`;
  control.id = controlId;
  const hintId = hint ? `${controlId}-hint` : null;
  const errorId = error ? `${controlId}-error` : null;

  // The label is bound by `for`, and hint/error are bound by `aria-describedby`, so a
  // screen reader announces the name AND the constraint rather than the name alone.
  const described = [hintId, errorId].filter(Boolean).join(" ");
  if (described) control.setAttribute("aria-describedby", described);
  if (error) control.setAttribute("aria-invalid", "true");

  return el("div", { class: "field" }, [
    el("label", { class: "field__label", for: controlId, text: labelText }),
    control,
    hint ? el("span", { class: "field__hint", id: hintId, text: hint }) : null,
    error ? el("span", { class: "field__error", id: errorId, role: "alert", text: error }) : null,
  ]);
}

function input(attrs = {}) { return el("input", { class: "input", ...attrs }); }
function select(options, attrs = {}) {
  return el("select", { class: "select", ...attrs },
    options.map((o) => el("option", { value: o.value, selected: o.selected ? "selected" : null, text: o.label })));
}

/* ------------------------------------------------------------------ states
 *
 * §23: every surface needs deliberate loading / empty / error states, and an error must
 * say what happened rather than "Load failed" where anything better is available.
 */

function emptyState(message, actionLabel, actionHref, { title = null, testid = null } = {}) {
  return el("div", { class: "state", "data-testid": testid || "empty-state" }, [
    title ? el("p", { class: "state__title", text: title }) : null,
    el("p", { class: "state__body", text: message }),
    actionLabel ? linkButton(actionLabel, actionHref) : null,
  ]);
}

/**
 * An error state that names the failure.
 *
 * `status` is mapped to a sentence a customer can act on. The generic branch is last and
 * still carries the correlation-relevant status, because "something went wrong" with no
 * code is unactionable for the customer AND for whoever they report it to.
 */
const STATUS_COPY = {
  0: ["Cannot reach DEDUNET", "Check your connection and try again."],
  401: ["Your session has ended", "Sign in again to continue."],
  403: ["Not available on this account", "You do not have access to this."],
  404: ["Not found", "That page or item does not exist."],
  409: ["Not available", "This action cannot be completed in the current mode."],
  429: ["Too many requests", "Wait a moment, then try again."],
  500: ["DEDUNET had a problem", "This is our side, not yours. Try again shortly."],
  503: ["Temporarily unavailable", "The service is starting or under maintenance."],
};

function errorState(error, { onRetry = null, testid = null } = {}) {
  const status = Number(error && error.status) || 0;
  const known = STATUS_COPY[status] || STATUS_COPY[status >= 500 ? 500 : 0];
  const [title, body] = known;
  return el("div", { class: "state", "data-testid": testid || "error-state", role: "alert" }, [
    el("p", { class: "state__title", text: title }),
    el("p", { class: "state__body", text: body }),
    // The server's own message, when it sent one, below our sentence rather than instead
    // of it. It is often precise and is always more specific than a status code.
    error && error.message && error.message !== title
      ? el("p", { class: "ds-subtle", text: error.message })
      : null,
    status ? el("p", { class: "state__code", text: `Status ${status}` }) : null,
    onRetry ? button("Try again", { onclick: onRetry }) : null,
  ]);
}

function offlineState(onRetry = null) {
  return errorState({ status: 0, message: "" }, { onRetry, testid: "offline-state" });
}

function unauthorizedState(onSignIn) {
  return el("div", { class: "state", "data-testid": "unauthorized-state" }, [
    el("p", { class: "state__title", text: "Sign in to continue" }),
    el("p", { class: "state__body", text: "This part of DEDUNET is yours, so it needs an account." }),
    onSignIn ? button("Sign in", { variant: "primary", onclick: onSignIn }) : linkButton("Sign in", "#/account", { variant: "primary" }),
  ]);
}

function skeletonCard() {
  return el("div", { class: "card", "aria-hidden": "true" }, [
    el("div", { class: "skeleton skeleton--media" }),
    el("div", { class: "card__body" }, [
      el("div", { class: "skeleton skeleton--title" }),
      el("div", { class: "skeleton skeleton--text" }),
    ]),
  ]);
}

/** A grid of skeletons. Reserves the real layout, so content arriving does not shift it. */
function skeletonGrid(count = 6, gridClass = "ds-grid") {
  return el("div", { class: gridClass, "data-testid": "loading-state", "aria-busy": "true" },
    Array.from({ length: count }, () => skeletonCard()));
}

/* ------------------------------------------------------------------ Dido character
 *
 * Egyptian PROPORTION and geometry, not costume. A vertical cartouche frame, a stacked
 * lintel silhouette, a single accent iris. §8 rules out headdresses, gold-mask pastiche
 * and tourist iconography explicitly — and those are also what would date the brand.
 *
 * Drawn as inline SVG so it costs no request, no library and no animation runtime. §24
 * warns against pulling in a heavyweight animation dependency before measuring; this is
 * the measurement-free option. `didoAnimator` is the seam a Rive or Lottie renderer would
 * later implement, so swapping it in is a change to one factory rather than to callers.
 */

const DIDO_STATES = [
  "idle", "listening", "asking", "thinking", "styling",
  "comparing", "presenting", "success", "error", "offline",
];

function didoFigure(state = "idle", { label = "Dido, your DEDUNET stylist" } = {}) {
  const safeState = DIDO_STATES.includes(state) ? state : "idle";
  const figure = el("div", {
    class: "dido-figure",
    "data-testid": "dido-figure",
    dataset: { state: safeState },
    role: "img",
    "aria-label": `${label}. Current state: ${safeState}.`,
  }, [
    svgEl("svg", { viewBox: "0 0 120 160", "aria-hidden": "true", focusable: "false" }, [
      // cartouche frame
      svgEl("rect", { x: 8, y: 8, width: 104, height: 144, fill: "none",
                      stroke: "currentColor", "stroke-width": 1.5, opacity: 0.35 }),
      // stacked lintel head
      svgEl("path", { d: "M34 44h52v10H34zM30 54h60v34H30zM38 88h44v20H38z",
                      fill: "currentColor", opacity: 0.12 }),
      svgEl("path", { d: "M34 44h52v10H34zM30 54h60v34H30zM38 88h44v20H38z",
                      fill: "none", stroke: "currentColor", "stroke-width": 1.5 }),
      // shoulders
      svgEl("path", { d: "M24 132c0-14 16-24 36-24s36 10 36 24", fill: "none",
                      stroke: "currentColor", "stroke-width": 1.5 }),
      // presenting rays
      svgEl("g", { class: "dido-rays", stroke: "currentColor", "stroke-width": 1, opacity: 0 }, [
        svgEl("path", { d: "M60 20v-8M40 26l-4-7M80 26l4-7" }),
      ]),
      // the single accent iris
      svgEl("ellipse", { class: "dido-iris", cx: 60, cy: 71, rx: 9, ry: 5 }),
    ]),
  ]);
  return figure;
}

/**
 * The animation seam.
 *
 * Returns a controller with `setState`. The CSS owns what each state LOOKS like, keyed off
 * `data-state`, so this sets one attribute rather than manipulating styles — which is what
 * lets a future Rive/Lottie implementation swap in without any caller changing.
 */
function didoAnimator(figure) {
  return {
    states: DIDO_STATES,
    setState(next) {
      const safe = DIDO_STATES.includes(next) ? next : "idle";
      figure.dataset.state = safe;
      const label = figure.getAttribute("aria-label") || "";
      figure.setAttribute("aria-label", label.replace(/Current state: \w+\./, `Current state: ${safe}.`));
      return safe;
    },
    get state() { return figure.dataset.state; },
  };
}

function didoMessage(text, { from = "dido" } = {}) {
  return el("div", { class: `dido-msg dido-msg--${from}`, "data-testid": `dido-msg-${from}` }, [
    el("div", {}, [
      el("p", { class: "dido-msg__who", text: from === "dido" ? "Dido" : "You" }),
      el("div", { class: "dido-msg__body", text }),
    ]),
  ]);
}

function didoThinking() {
  return el("div", {
    class: "dido-thinking",
    "data-testid": "dido-thinking",
    role: "status",
    "aria-label": "Dido is thinking",
  }, [el("span"), el("span"), el("span")]);
}

function didoOption(label, { hint = null, onclick = null, disabled = false, testid = null } = {}) {
  return el("button", {
    class: "dido-option",
    type: "button",
    "data-testid": testid,
    disabled: disabled ? "disabled" : null,
    onclick: disabled ? null : onclick,
  }, [
    el("span", { class: "dido-option__label", text: label }),
    hint ? el("span", { class: "dido-option__hint", text: hint }) : null,
  ]);
}

/* ------------------------------------------------------------------ live region
 *
 * §22 requires status changes to reach a screen reader. One polite region, announced by
 * replacing its text — components call `announce()` rather than each inventing a region,
 * because several live regions on a page compete and the user hears the loser.
 */

function announce(message) {
  const region = document.getElementById("ds-live");
  if (region) region.textContent = message;
  return region;
}

/* ------------------------------------------------------------------ exports */

window.DS = {
  el, svgEl, icon, money,
  button, linkButton, badge, fixtureBadge, chip, field, input, select,
  emptyState, errorState, offlineState, unauthorizedState,
  skeletonCard, skeletonGrid,
  didoFigure, didoAnimator, didoMessage, didoThinking, didoOption, DIDO_STATES,
  announce,
  STATUS_COPY,
};
