const API_BASE = window.FASHION_POC_API_BASE ?? `${window.location.protocol}//${window.location.hostname}:18000`;
let products = [];

// Money contract SB-AR-B3-003: the API sends authoritative INTEGER MINOR UNITS.
// The client only renders them and never performs floating-point money arithmetic.
const MINOR_UNIT_EXPONENTS = { EUR: 2 };
const CURRENCY_SYMBOLS = { EUR: "€" };

function money(minorUnits, currency = "EUR") {
  const exponent = MINOR_UNIT_EXPONENTS[currency];
  if (exponent === undefined || !Number.isInteger(minorUnits)) {
    return `${minorUnits} ${currency}`;
  }
  // Pure integer/string formatting: no division, no float ever touches the amount.
  const sign = minorUnits < 0 ? "-" : "";
  const digits = String(Math.abs(minorUnits)).padStart(exponent + 1, "0");
  const major = digits.slice(0, digits.length - exponent);
  const minor = digits.slice(digits.length - exponent);
  const symbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;
  return `${sign}${symbol}${major}.${minor}`;
}

function renderProducts(items) {
  const container = document.querySelector("#products");
  container.innerHTML = items.map(product => `
    <article class="card">
      <img src="${product.image_url}" alt="Placeholder product visual for ${product.name}" />
      <p class="eyebrow">SYNTHETIC / UNVERIFIED / NOT FOR SALE</p>
      <p class="eyebrow">${product.collection}</p>
      <h3>${product.name}</h3>
      <p>${product.description}</p>
      <div class="meta"><span>Fixture composition: ${product.fibre_composition}</span><strong>Fixture price: ${money(product.price_minor_units, product.currency)}</strong></div>
      <div class="meta"><span>Fixture origin: ${product.made_in}</span><span>Fixture quantity: ${product.variants.reduce((n, v) => n + v.stock, 0)}</span></div>
    </article>
  `).join("");
}

async function loadCatalog() {
  const status = document.querySelector("#status");
  try {
    const response = await fetch(`${API_BASE}/api/v1/products`);
    if (!response.ok) throw new Error(`API ${response.status}`);
    products = await response.json();
    renderProducts(products);
    status.textContent = `${products.length} products connected`;
  } catch (error) {
    status.textContent = `Catalog unavailable: ${error.message}`;
  }
}

function splitList(value) {
  return value.split(",").map(item => item.trim()).filter(Boolean);
}

document.querySelector("#stylist-form").addEventListener("submit", async event => {
  event.preventDefault();
  const result = document.querySelector("#recommendation");
  result.textContent = "Scoring catalog…";
  const data = new FormData(event.currentTarget);
  const payload = {
    occasion: data.get("occasion"),
    preferred_colors: splitList(data.get("colors")),
    preferred_categories: splitList(data.get("categories")),
    // Budget is submitted as authoritative integer minor units (whole EUR input x 100).
    budget_minor_units: Math.round(Number(data.get("budget"))) * 100,
    style_notes: data.get("notes")
  };
  try {
    const response = await fetch(`${API_BASE}/api/v1/stylist/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(`API ${response.status}`);
    const recommendation = await response.json();
    const selected = products.filter(item => recommendation.product_ids.includes(item.id));
    result.innerHTML = `<strong>${recommendation.rationale}</strong><p>${selected.map(item => item.name).join(" + ")} — ${money(recommendation.total_minor_units, recommendation.currency)}</p>`;
  } catch (error) {
    result.textContent = `Recommendation unavailable: ${error.message}`;
  }
});

loadCatalog();
