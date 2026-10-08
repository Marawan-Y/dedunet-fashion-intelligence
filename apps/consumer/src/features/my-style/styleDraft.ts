import type {
  BrandStanceEntry,
  FitEntry,
  SizeEntry,
  Stance,
  StanceEntry,
  StyleProfile,
} from "../../api/types";

/* The editor's state logic, as pure functions.
 *
 * Kept out of the component for the reason the Saved phase kept `savedState.ts` out of
 * its context: this is where the decisions live -- what a third click on a chip means,
 * what counts as a changed field, what a budget string parses to -- and decisions deserve
 * tests that do not need a DOM to run.
 *
 * NOTHING HERE INFERS ANYTHING. Every function maps an explicit user action onto an
 * explicit stored value. There is no scoring, no weighting and no derived preference, and
 * the absence is deliberate rather than pending.
 */

/** A draft is a profile the customer is editing but has not saved. */
export interface StyleDraft {
  personalizationEnabled: boolean;
  styleDirections: StanceEntry[];
  colours: StanceEntry[];
  colourApproach: string | null;
  fits: FitEntry[];
  sizes: SizeEntry[];
  materials: StanceEntry[];
  careEffort: string | null;
  seasonality: string | null;
  fitNotes: string;
  brands: BrandStanceEntry[];
  budgetPerPiece: string;
  budgetPerLook: string;
  currency: string;
}

const SOURCE = "USER_EXPLICIT" as const;

/**
 * Minor units to an editable string, by integer arithmetic only.
 *
 * `minor / 100` is forbidden by the money contract and it is not pedantry: binary floating
 * point cannot represent most cent values exactly, so a value that round-trips through a
 * division can come back a cent different from what the customer typed. Slicing digits
 * cannot.
 */
export function minorUnitsToInput(minor: number | null): string {
  if (minor === null || !Number.isInteger(minor)) return "";
  const sign = minor < 0 ? "-" : "";
  const digits = String(Math.abs(minor)).padStart(3, "0");
  const major = digits.slice(0, digits.length - 2);
  const cents = digits.slice(digits.length - 2);
  return cents === "00" ? `${sign}${major}` : `${sign}${major}.${cents}`;
}

/**
 * An editable string back to integer minor units, again without division.
 *
 * Returns `null` for empty (meaning "unset") and `undefined` for anything unparseable, so
 * the caller can tell "cleared" from "rejected". Collapsing those would silently clear a
 * budget when someone typed a stray character.
 */
export function inputToMinorUnits(value: string): number | null | undefined {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^\d+([.,]\d{0,2})?$/.test(trimmed)) return undefined;
  const [major, fraction = ""] = trimmed.replace(",", ".").split(".");
  const cents = (fraction + "00").slice(0, 2);
  return Number(major) * 100 + Number(cents);
}

export function draftFromProfile(profile: StyleProfile): StyleDraft {
  return {
    personalizationEnabled: profile.exists ? profile.personalization_enabled : true,
    styleDirections: [...profile.style_directions],
    colours: [...profile.colours],
    colourApproach: profile.colour_approach,
    fits: [...profile.fits],
    sizes: [...profile.sizes],
    materials: [...profile.materials],
    careEffort: profile.care_effort,
    seasonality: profile.seasonality,
    fitNotes: profile.fit_notes,
    brands: [...profile.brands],
    budgetPerPiece: minorUnitsToInput(profile.budget.per_piece_minor_units),
    budgetPerLook: minorUnitsToInput(profile.budget.per_look_minor_units),
    currency: profile.budget.currency ?? "EUR",
  };
}

/**
 * Cycle one entry: unset -> PREFERRED -> AVOIDED -> unset.
 *
 * Three states through one control, because the alternative is two controls per term and
 * a grid of sixteen colours becomes thirty-two targets on a phone. Returning to unset
 * matters as much as the other two: a customer who sets something by mistake must be able
 * to say "I have no opinion", and that is NOT the same as saying "I avoid it".
 *
 * Never mutates its input.
 */
export function cycleStance(entries: StanceEntry[], slug: string): StanceEntry[] {
  const existing = entries.find((e) => e.slug === slug);
  if (!existing) return [...entries, { slug, stance: "PREFERRED", source: SOURCE }];
  if (existing.stance === "PREFERRED") {
    return entries.map((e) => (e.slug === slug ? { ...e, stance: "AVOIDED" as Stance } : e));
  }
  return entries.filter((e) => e.slug !== slug);
}

export function stanceOf(entries: { slug: string; stance: Stance }[], slug: string): Stance | null {
  return entries.find((e) => e.slug === slug)?.stance ?? null;
}

/** Single-select with a toggle-off: choosing the current value clears it. */
export function toggleSingle(current: string | null, slug: string): string | null {
  return current === slug ? null : slug;
}

export function setFit(fits: FitEntry[], category: string, fit: string | null): FitEntry[] {
  const without = fits.filter((f) => f.garment_category !== category);
  if (!fit) return without;
  return [...without, { garment_category: category, fit, source: SOURCE }];
}

export function fitOf(fits: FitEntry[], category: string): string | null {
  return fits.find((f) => f.garment_category === category)?.fit ?? null;
}

/**
 * Set or clear a stated size for one (category, system).
 *
 * The pair is the key. A customer may know "tops: M" and "tops: EU 50" at once, and both
 * are kept as stated -- nothing here converts between systems, because those equivalences
 * are approximately true across brands and exactly true within none.
 */
export function setSize(
  sizes: SizeEntry[],
  category: string,
  system: string,
  label: string,
): SizeEntry[] {
  const without = sizes.filter(
    (s) => !(s.garment_category === category && s.size_system === system),
  );
  const trimmed = label.trim();
  if (!trimmed) return without;
  return [
    ...without,
    { garment_category: category, size_system: system, size_label: trimmed, source: SOURCE },
  ];
}

export function sizeOf(sizes: SizeEntry[], category: string, system: string): string {
  return (
    sizes.find((s) => s.garment_category === category && s.size_system === system)?.size_label ?? ""
  );
}

export function cycleBrandStance(
  brands: BrandStanceEntry[],
  slug: string,
  name: string,
): BrandStanceEntry[] {
  const existing = brands.find((b) => b.slug === slug);
  if (!existing) return [...brands, { slug, name, stance: "PREFERRED", source: SOURCE }];
  if (existing.stance === "PREFERRED") {
    return brands.map((b) => (b.slug === slug ? { ...b, stance: "AVOIDED" as Stance } : b));
  }
  return brands.filter((b) => b.slug !== slug);
}

/**
 * How many of the five sections hold something the customer actually said.
 *
 * A COUNT. "3 of 5" is a fact the reader can check against the page in front of them.
 * "Style DNA strength: 78%" would be a number with no definition and no model behind it,
 * and it is the first piece of pseudo-science a page like this attracts.
 */
export function sectionsWithPreferences(draft: StyleDraft): number {
  let filled = 0;
  if (draft.styleDirections.length) filled += 1;
  if (draft.colours.length || draft.colourApproach) filled += 1;
  if (draft.fits.length || draft.sizes.length || draft.fitNotes.trim()) filled += 1;
  if (draft.materials.length || draft.careEffort || draft.seasonality) filled += 1;
  if (draft.brands.length || draft.budgetPerPiece.trim() || draft.budgetPerLook.trim()) filled += 1;
  return filled;
}

export const SECTION_COUNT = 5;

export class BudgetFormatError extends Error {}

/**
 * The patch to send, containing only what actually changed.
 *
 * Sending the whole draft every time would work, and would also mean every save rewrites
 * every collection -- so two tabs editing different sections would clobber each other even
 * though they never touched the same field. A minimal patch keeps the conflict surface to
 * what the customer really edited.
 */
export function buildPatch(draft: StyleDraft, original: StyleDraft): Record<string, unknown> {
  const patch: Record<string, unknown> = {};

  /* Compare as sorted key strings. The previous version re-sorted `b` inside the
   * predicate, which TypeScript correctly flagged as possibly-undefined on the index and
   * which also sorted once per element. One key each, compared directly. */
  const stanceKey = (entries: { slug: string; stance: Stance }[]) =>
    entries
      .map((e) => `${e.slug}:${e.stance}`)
      .sort()
      .join("|");
  const sameStances = (
    a: { slug: string; stance: Stance }[],
    b: { slug: string; stance: Stance }[],
  ) => stanceKey(a) === stanceKey(b);

  if (!sameStances(draft.styleDirections, original.styleDirections)) {
    patch.style_directions = draft.styleDirections.map((e) => ({ slug: e.slug, stance: e.stance }));
  }
  if (!sameStances(draft.colours, original.colours)) {
    patch.colours = draft.colours.map((e) => ({ slug: e.slug, stance: e.stance }));
  }
  if (!sameStances(draft.materials, original.materials)) {
    patch.materials = draft.materials.map((e) => ({ slug: e.slug, stance: e.stance }));
  }
  if (!sameStances(draft.brands, original.brands)) {
    patch.brands = draft.brands.map((e) => ({ slug: e.slug, stance: e.stance }));
  }

  const fitKey = (f: FitEntry[]) =>
    [...f].map((x) => `${x.garment_category}:${x.fit}`).sort().join("|");
  if (fitKey(draft.fits) !== fitKey(original.fits)) {
    patch.fits = draft.fits.map((f) => ({ garment_category: f.garment_category, fit: f.fit }));
  }

  const sizeKey = (s: SizeEntry[]) =>
    [...s].map((x) => `${x.garment_category}:${x.size_system}:${x.size_label}`).sort().join("|");
  if (sizeKey(draft.sizes) !== sizeKey(original.sizes)) {
    patch.sizes = draft.sizes.map((s) => ({
      garment_category: s.garment_category,
      size_system: s.size_system,
      size_label: s.size_label,
    }));
  }

  if (draft.colourApproach !== original.colourApproach) patch.colour_approach = draft.colourApproach;
  if (draft.careEffort !== original.careEffort) patch.care_effort = draft.careEffort;
  if (draft.seasonality !== original.seasonality) patch.seasonality = draft.seasonality;
  if (draft.fitNotes.trim() !== original.fitNotes.trim()) patch.fit_notes = draft.fitNotes.trim();
  if (draft.personalizationEnabled !== original.personalizationEnabled) {
    patch.personalization_enabled = draft.personalizationEnabled;
  }

  const budget: Record<string, unknown> = {};
  if (draft.budgetPerPiece !== original.budgetPerPiece) {
    const parsed = inputToMinorUnits(draft.budgetPerPiece);
    if (parsed === undefined) throw new BudgetFormatError("Budget per piece is not a number");
    budget.per_piece_minor_units = parsed;
  }
  if (draft.budgetPerLook !== original.budgetPerLook) {
    const parsed = inputToMinorUnits(draft.budgetPerLook);
    if (parsed === undefined) throw new BudgetFormatError("Budget per look is not a number");
    budget.per_look_minor_units = parsed;
  }
  if (Object.keys(budget).length) {
    // A currency always rides with an amount. A number without one is not money.
    budget.currency = draft.currency;
    patch.budget = budget;
  }

  return patch;
}

export function isDirty(draft: StyleDraft, original: StyleDraft): boolean {
  try {
    return Object.keys(buildPatch(draft, original)).length > 0;
  } catch {
    // An unparseable budget is still a change the customer made.
    return true;
  }
}

/** Plain-language errors. Never a raw status code or a server trace. */
export function saveErrorMessage(error: unknown): string {
  const status = (error as { status?: number } | null)?.status;
  if (status === 401) return "Your session has expired. Sign in again to save your Style DNA.";
  if (status === 409) return "You changed this somewhere else. Reload to see the latest version.";
  if (status === 400) {
    const message = (error as { message?: string }).message;
    return message ? `That could not be saved: ${message}` : "That could not be saved.";
  }
  if (status === 429) return "Too many changes at once. Wait a moment and try again.";
  if (typeof status === "number" && status >= 500) return "DEDUNET could not save that. Try again shortly.";
  return "DEDUNET could not reach the server. Check your connection and try again.";
}
