/**
 * DEDUNET frontend service layer.
 *
 * §28 asks for interfaces the later Looks, Brands, Style-Profile, Dido and Saved domains
 * can plug into, WITHOUT building speculative backends to satisfy frontend mocks.
 *
 * So each service is a named interface with exactly one of two implementations:
 *
 *   LIVE      talks to an endpoint that exists today
 *   FIXTURE   returns demonstration content, tagged `source: "fixture"`
 *
 * Every record carries `source`. Nothing downstream has to guess, and §29's rule — fixture
 * content must never look like verified production data — is enforceable by a test rather
 * than by reviewer memory. `isFixture()` is the single predicate the UI branches on, and
 * the fixture badge is driven from it.
 *
 * When a real endpoint lands, its service swaps `FIXTURE` for `LIVE` here. No page changes.
 */

/* ------------------------------------------------------------------ provenance */

const SOURCE = { LIVE: "live", FIXTURE: "fixture", UNAVAILABLE: "unavailable" };

function tag(records, source) {
  return records.map((r) => ({ ...r, source }));
}

function isFixture(record) {
  return !!record && record.source === SOURCE.FIXTURE;
}

/**
 * A service whose backend does not exist yet.
 *
 * Distinct from an empty result: "we have nothing to show you" and "this capability is not
 * built" are different facts and the UI must not render them the same way. §5 forbids
 * faking AI; this is how a page says so honestly instead.
 */
function unavailable(capability, arrivesIn) {
  return { source: SOURCE.UNAVAILABLE, capability, arrivesIn, items: [] };
}

/* ------------------------------------------------------------------ occasions
 *
 * Platform vocabulary, not personalised content, so these are real configuration rather
 * than fixtures. The styling SESSION they open is what does not exist yet.
 */

const OCCASIONS = [
  { slug: "work", name: "Work", hint: "Everyday professional" },
  { slug: "interview", name: "Interview", hint: "Make the right first impression" },
  { slug: "dinner", name: "Dinner", hint: "Evening, considered" },
  { slug: "date", name: "Date", hint: "Personal, confident" },
  { slug: "wedding", name: "Wedding", hint: "Guest dress codes" },
  { slug: "travel", name: "Travel", hint: "Long days, changing weather" },
  { slug: "party", name: "Party", hint: "Distinctive" },
  { slug: "weekend", name: "Weekend", hint: "Relaxed" },
  { slug: "everyday", name: "Everyday", hint: "What you actually wear" },
  { slug: "formal", name: "Formal Event", hint: "Black tie and adjacent" },
  { slug: "custom", name: "Something else", hint: "Describe it to Dido" },
];

/* ------------------------------------------------------------------ discovery taxonomy */

const DISCOVER_GROUPS = [
  {
    title: "By moment",
    slugs: ["trending", "editors", "interview", "dinner", "wedding-guest", "weekend", "travel", "work"],
  },
  {
    title: "By season",
    slugs: ["summer", "winter"],
  },
  {
    title: "By style",
    slugs: ["minimal", "classic", "smart-casual", "streetwear", "luxury", "modest", "contemporary", "avant-garde"],
  },
];

const DISCOVER_CATEGORIES = {
  trending: { name: "Trending Looks", blurb: "What people are building this week." },
  editors: { name: "Editor's Picks", blurb: "Chosen by the DEDUNET editorial desk." },
  interview: { name: "Interview Fits", blurb: "Considered, unfussy, memorable for the right reason." },
  dinner: { name: "Dinner", blurb: "Evening looks that travel from table to street." },
  "wedding-guest": { name: "Wedding Guest", blurb: "Dress codes, decoded." },
  weekend: { name: "Weekend", blurb: "Relaxed without being shapeless." },
  travel: { name: "Travel", blurb: "Long days, changing weather, one bag." },
  work: { name: "Work", blurb: "Professional, repeatable, yours." },
  summer: { name: "Summer", blurb: "Light, breathable, structured." },
  winter: { name: "Winter", blurb: "Layers that hold their line." },
  minimal: { name: "Minimal", blurb: "Few pieces, exact proportions." },
  classic: { name: "Classic", blurb: "Long-lived shapes." },
  "smart-casual": { name: "Smart Casual", blurb: "The hardest brief, solved." },
  streetwear: { name: "Streetwear", blurb: "Contemporary volume and graphics." },
  luxury: { name: "Luxury", blurb: "Material-led." },
  modest: { name: "Modest", blurb: "Coverage without compromise." },
  contemporary: { name: "Contemporary", blurb: "Current, wearable." },
  "avant-garde": { name: "Avant-Garde", blurb: "Shapes that argue." },
};

/* ------------------------------------------------------------------ look fixtures
 *
 * DEMONSTRATION CONTENT. These describe how a Look is SHAPED so the components can be
 * built and tested; they are not recommendations, not personalised, and not derived from
 * any engine. Phase 8/9 replace this adapter with the real one.
 *
 * Prices are integer minor units, like everywhere else, so the fixtures exercise the same
 * money path as live data instead of a softer one.
 */

const LOOK_FIXTURES = [
  {
    slug: "quiet-interview",
    title: "The Quiet Interview",
    occasion: "Interview",
    style: "Minimal · Classic",
    categories: ["interview", "minimal", "classic", "editors", "work"],
    total_minor_units: 27800,
    currency: "EUR",
    rationale:
      "Unbroken vertical line, one contrast point, nothing that asks to be looked at. " +
      "Chosen to be forgettable as clothing and memorable as a person.",
    items: [
      { slot: "Top", name: "The Passage Shirt", brand: "DEDUNET", external_product_id: "DDN-SH01", price_minor_units: 9800 },
      { slot: "Trouser", name: "The Measure Trouser", brand: "DEDUNET", external_product_id: "DDN-TR01", price_minor_units: 12800 },
      { slot: "Layer", name: "The Structure Overshirt", brand: "DEDUNET", external_product_id: "DDN-OS01", price_minor_units: 5200 },
    ],
  },
  {
    slug: "long-table-dinner",
    title: "Long Table Dinner",
    occasion: "Dinner",
    style: "Contemporary · Luxury",
    categories: ["dinner", "contemporary", "luxury", "trending"],
    total_minor_units: 21500,
    currency: "EUR",
    rationale: "Softer shoulder, deeper tone, one textural piece that reads well in low light.",
    items: [
      { slot: "Top", name: "The Source Tee", brand: "DEDUNET", external_product_id: "DDN-TS01", price_minor_units: 7200 },
      { slot: "Layer", name: "The Structure Overshirt", brand: "DEDUNET", external_product_id: "DDN-OS01", price_minor_units: 14300 },
    ],
  },
  {
    slug: "one-bag-travel",
    title: "One Bag, Four Days",
    occasion: "Travel",
    style: "Minimal",
    categories: ["travel", "minimal", "weekend", "summer"],
    total_minor_units: 19900,
    currency: "EUR",
    rationale: "Three pieces that recombine into four days without reading as a uniform.",
    items: [
      { slot: "Top", name: "The Source Tee", brand: "DEDUNET", external_product_id: "DDN-TS01", price_minor_units: 7200 },
      { slot: "Trouser", name: "The Measure Trouser", brand: "DEDUNET", external_product_id: "DDN-TR01", price_minor_units: 12700 },
    ],
  },
  {
    slug: "weekend-line",
    title: "The Weekend Line",
    occasion: "Weekend",
    style: "Smart Casual",
    categories: ["weekend", "smart-casual", "trending", "everyday"],
    total_minor_units: 9600,
    currency: "EUR",
    rationale: "Relaxed volume held together by one deliberate proportion.",
    items: [
      { slot: "Top", name: "The Source Tee", brand: "DEDUNET", external_product_id: "DDN-TS01", price_minor_units: 7200 },
      { slot: "Accessory", name: "The Trace Scarf", brand: "DEDUNET", external_product_id: "DDN-SC01", price_minor_units: 2400 },
    ],
  },
  {
    slug: "winter-column",
    title: "Winter Column",
    occasion: "Everyday",
    style: "Classic",
    categories: ["winter", "classic", "editors", "work"],
    total_minor_units: 31200,
    currency: "EUR",
    rationale: "One tone head to toe, broken only at the throat.",
    items: [
      { slot: "Layer", name: "The Structure Overshirt", brand: "DEDUNET", external_product_id: "DDN-OS01", price_minor_units: 18400 },
      { slot: "Trouser", name: "The Measure Trouser", brand: "DEDUNET", external_product_id: "DDN-TR01", price_minor_units: 12800 },
    ],
  },
  {
    slug: "wedding-guest-restraint",
    title: "Wedding Guest, Restrained",
    occasion: "Wedding",
    style: "Classic · Modest",
    categories: ["wedding-guest", "classic", "modest", "formal"],
    total_minor_units: 24600,
    currency: "EUR",
    rationale: "Dress code respected, attention left with the couple.",
    items: [
      { slot: "Top", name: "The Passage Shirt", brand: "DEDUNET", external_product_id: "DDN-SH01", price_minor_units: 9800 },
      { slot: "Trouser", name: "The Measure Trouser", brand: "DEDUNET", external_product_id: "DDN-TR01", price_minor_units: 14800 },
    ],
  },
];

/* ------------------------------------------------------------------ brand fixtures
 *
 * The three ownership shapes ADR-0002 §2.0 defines, so the UI is built against the real
 * model. §11 forbids exposing the technical terms to consumers, so `consumerLabel` is what
 * a page renders and `ownership_type` is what it branches on.
 *
 * Only DEDUNET is real. The other two are shape demonstrations and say so — §11 also
 * forbids inventing commercial partnerships.
 */

const BRAND_CONSUMER_LABEL = {
  PLATFORM_CURATED: "DEDUNET selection",
  MERCHANT_OWNED: "Partner brand",
  EXTERNAL_CURATED: "External brand",
};

const BRAND_FIXTURES = [
  {
    slug: "dedunet",
    name: "DEDUNET",
    ownership_type: "PLATFORM_CURATED",
    first_party: true,
    story:
      "DEDUNET's own capsule. Designed to test the platform end to end: five pieces, " +
      "sixty-two variants, and every material and origin field deliberately left unverified.",
    commerce_route: "NON_PURCHASABLE",
    product_count: 5,
  },
  {
    slug: "example-partner",
    name: "Partner brand (shape demonstration)",
    ownership_type: "MERCHANT_OWNED",
    first_party: false,
    story:
      "Placeholder showing how a brand WITHOUT its own website would appear: hosted by " +
      "DEDUNET, with its catalogue, story and checkout on this platform. No such partner " +
      "exists and none has been approached.",
    commerce_route: "HOSTED",
    product_count: 0,
  },
  {
    slug: "example-external",
    name: "External brand (shape demonstration)",
    ownership_type: "EXTERNAL_CURATED",
    first_party: false,
    story:
      "Placeholder showing how a brand DEDUNET lists but does not operate would appear: " +
      "discovery here, purchase on the brand's own site. No such listing exists.",
    commerce_route: "REFERRAL",
    product_count: 0,
  },
];

/* ------------------------------------------------------------------ services */

/**
 * Looks. FIXTURE — the outfit engine is Phase 9.
 *
 * `forYou` deliberately does NOT claim personalisation. §6 forbids fake AI personalisation
 * claims, so the module that would eventually be "selected for you" is labelled by what it
 * actually is until an engine exists to make it true.
 */
const LooksService = {
  implementation: SOURCE.FIXTURE,
  async list({ category = null, maxMinorUnits = null } = {}) {
    let items = LOOK_FIXTURES;
    if (category) items = items.filter((l) => l.categories.includes(category));
    if (maxMinorUnits) items = items.filter((l) => l.total_minor_units <= maxMinorUnits);
    return tag(items, SOURCE.FIXTURE);
  },
  async get(slug) {
    const found = LOOK_FIXTURES.find((l) => l.slug === slug);
    return found ? { ...found, source: SOURCE.FIXTURE } : null;
  },
  /** Personalised selection needs Style DNA (Phase 6) and the engine (Phase 8). */
  async forYou() {
    return unavailable("Personalised look selection", "a later platform phase");
  },
};

/** Brands. FIXTURE — the Brand entity is Phase 4. */
const BrandsService = {
  implementation: SOURCE.FIXTURE,
  async list() { return tag(BRAND_FIXTURES, SOURCE.FIXTURE); },
  async get(slug) {
    const found = BRAND_FIXTURES.find((b) => b.slug === slug);
    return found ? { ...found, source: SOURCE.FIXTURE } : null;
  },
  consumerLabel(brand) {
    return BRAND_CONSUMER_LABEL[brand && brand.ownership_type] || "Brand";
  },
};

/**
 * Saved. UNAVAILABLE — no persistence exists.
 *
 * §14 asks for clean states and interfaces WITHOUT fabricating persisted data, so this
 * reports unavailable rather than reading and writing localStorage to look functional. A
 * save button that silently forgets is worse than one that says it is not built.
 */
const SavedService = {
  implementation: SOURCE.UNAVAILABLE,
  async looks() { return unavailable("Saved looks", "the styling platform phase"); },
  async products() { return unavailable("Saved products", "the styling platform phase"); },
  async brands() { return unavailable("Saved brands", "the marketplace phase"); },
  get canSave() { return false; },
};

/** Style profile. UNAVAILABLE — Style DNA is Phase 6. */
const StyleProfileService = {
  implementation: SOURCE.UNAVAILABLE,
  async get() { return unavailable("Your Style DNA", "the Style DNA phase"); },
  sections: [
    { key: "dna", name: "Style DNA", hint: "The mix of styles you actually wear" },
    { key: "sizes", name: "Sizes", hint: "Tops, bottoms, shoes" },
    { key: "colours", name: "Colours", hint: "Preferred and avoided" },
    { key: "fits", name: "Fits", hint: "How you like things to sit" },
    { key: "brands", name: "Brands", hint: "Preferred and avoided" },
    { key: "budget", name: "Budget", hint: "Per item and per outfit" },
    { key: "materials", name: "Materials", hint: "Comfort and sensitivity" },
    { key: "personalization", name: "Personalization", hint: "What DEDUNET may remember" },
  ],
};

/**
 * Dido. UNAVAILABLE — orchestration is Phase 7/10.
 *
 * `openSession` returns a scripted OPENING, explicitly marked, and never a recommendation.
 * §5: prefer functional navigation over fake AI.
 */
const DidoService = {
  implementation: SOURCE.UNAVAILABLE,
  async openSession(occasionSlug = null) {
    const occasion = OCCASIONS.find((o) => o.slug === occasionSlug) || null;
    return {
      source: SOURCE.UNAVAILABLE,
      capability: "Styling conversation",
      arrivesIn: "the Dido phase",
      occasion,
      opening: occasion
        ? `${occasion.name}. Good — that is a brief I can work with.`
        : "Clothes have always told people who we are. Tell me where you're going.",
    };
  },
  async reply() {
    return unavailable("Styling conversation", "the Dido phase");
  },
};

/* ------------------------------------------------------------------ exports */

window.DedunetData = {
  SOURCE, isFixture, unavailable,
  OCCASIONS, DISCOVER_GROUPS, DISCOVER_CATEGORIES,
  BRAND_CONSUMER_LABEL,
  LooksService, BrandsService, SavedService, StyleProfileService, DidoService,
};
