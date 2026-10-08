import { describe, expect, it } from "vitest";
import type { StyleProfile } from "../../api/types";
import {
  BudgetFormatError,
  buildPatch,
  cycleBrandStance,
  cycleStance,
  draftFromProfile,
  fitOf,
  inputToMinorUnits,
  isDirty,
  minorUnitsToInput,
  saveErrorMessage,
  sectionsWithPreferences,
  setFit,
  setSize,
  sizeOf,
  stanceOf,
  toggleSingle,
  type StyleDraft,
} from "./styleDraft";

const EMPTY_PROFILE: StyleProfile = {
  exists: false,
  revision: 0,
  personalization_enabled: false,
  style_directions: [],
  colours: [],
  colour_approach: null,
  fits: [],
  sizes: [],
  materials: [],
  care_effort: null,
  seasonality: null,
  fit_notes: "",
  brands: [],
  budget: { per_piece_minor_units: null, per_look_minor_units: null, currency: null },
  sections_with_preferences: 0,
  section_count: 5,
  created_at: null,
  updated_at: null,
};

const base = (): StyleDraft => draftFromProfile(EMPTY_PROFILE);

describe("money, by integer arithmetic only", () => {
  it("formats minor units without dividing", () => {
    expect(minorUnitsToInput(7200)).toBe("72");
    expect(minorUnitsToInput(19999)).toBe("199.99");
    expect(minorUnitsToInput(5)).toBe("0.05");
    expect(minorUnitsToInput(0)).toBe("0");
    expect(minorUnitsToInput(null)).toBe("");
  });

  it("parses an input into integer minor units", () => {
    expect(inputToMinorUnits("72")).toBe(7200);
    expect(inputToMinorUnits("199.99")).toBe(19999);
    expect(inputToMinorUnits("199,99")).toBe(19999);
    expect(inputToMinorUnits("0.5")).toBe(50);
    expect(inputToMinorUnits("  ")).toBeNull();
  });

  it("distinguishes cleared from unparseable", () => {
    // Collapsing these would silently clear a budget when someone typed a stray character.
    expect(inputToMinorUnits("")).toBeNull();
    expect(inputToMinorUnits("abc")).toBeUndefined();
    expect(inputToMinorUnits("-5")).toBeUndefined();
    expect(inputToMinorUnits("1.999")).toBeUndefined();
  });

  it("round-trips the value that float division gets wrong", () => {
    // 19999 / 100 * 100 is not 19999 in binary floating point.
    expect(inputToMinorUnits(minorUnitsToInput(19999))).toBe(19999);
    expect(inputToMinorUnits(minorUnitsToInput(70))).toBe(70);
  });
});

describe("stance cycling", () => {
  it("goes unset to preferred to avoided and back to unset", () => {
    let entries = cycleStance([], "black");
    expect(stanceOf(entries, "black")).toBe("PREFERRED");
    entries = cycleStance(entries, "black");
    expect(stanceOf(entries, "black")).toBe("AVOIDED");
    entries = cycleStance(entries, "black");
    // Returning to unset matters: "no opinion" is not "I avoid it".
    expect(stanceOf(entries, "black")).toBeNull();
    expect(entries).toEqual([]);
  });

  it("never mutates its input", () => {
    const original = cycleStance([], "navy");
    const snapshot = JSON.parse(JSON.stringify(original));
    cycleStance(original, "navy");
    expect(original).toEqual(snapshot);
  });

  it("marks every created entry as explicitly set by the user", () => {
    const entries = cycleStance([], "linen");
    expect(entries[0]?.source).toBe("USER_EXPLICIT");
  });

  it("cycles brands while keeping the display name", () => {
    let brands = cycleBrandStance([], "dedunet", "DEDUNET");
    expect(brands[0]).toMatchObject({ slug: "dedunet", name: "DEDUNET", stance: "PREFERRED" });
    brands = cycleBrandStance(brands, "dedunet", "DEDUNET");
    expect(brands[0]?.stance).toBe("AVOIDED");
    expect(cycleBrandStance(brands, "dedunet", "DEDUNET")).toEqual([]);
  });
});

describe("single-select fields", () => {
  it("clears when the current value is chosen again", () => {
    expect(toggleSingle(null, "tonal")).toBe("tonal");
    expect(toggleSingle("tonal", "tonal")).toBeNull();
    expect(toggleSingle("tonal", "colour-led")).toBe("colour-led");
  });
});

describe("fit and size", () => {
  it("keeps one fit per garment category", () => {
    let fits = setFit([], "tops", "relaxed");
    fits = setFit(fits, "tops", "oversized");
    expect(fits).toHaveLength(1);
    expect(fitOf(fits, "tops")).toBe("oversized");
    expect(setFit(fits, "tops", null)).toEqual([]);
  });

  it("keeps sizes for two systems in the same category side by side", () => {
    let sizes = setSize([], "tops", "ALPHA", "M");
    sizes = setSize(sizes, "tops", "EU", "50");
    expect(sizes).toHaveLength(2);
    expect(sizeOf(sizes, "tops", "ALPHA")).toBe("M");
    expect(sizeOf(sizes, "tops", "EU")).toBe("50");
  });

  it("never converts between size systems", () => {
    const sizes = setSize([], "tops", "ALPHA", "M");
    // Setting ALPHA must not populate any other system.
    expect(sizeOf(sizes, "tops", "EU")).toBe("");
    expect(sizeOf(sizes, "tops", "UK")).toBe("");
  });

  it("clears a size when the input is emptied", () => {
    const sizes = setSize(setSize([], "tops", "ALPHA", "M"), "tops", "ALPHA", "  ");
    expect(sizes).toEqual([]);
  });
});

describe("completeness is a count, not a score", () => {
  it("counts filled sections out of five", () => {
    const draft = base();
    expect(sectionsWithPreferences(draft)).toBe(0);
    expect(sectionsWithPreferences({ ...draft, colours: cycleStance([], "black") })).toBe(1);
    expect(
      sectionsWithPreferences({
        ...draft,
        colours: cycleStance([], "black"),
        materials: cycleStance([], "linen"),
      }),
    ).toBe(2);
  });

  it("counts a section filled by any of its fields", () => {
    const draft = base();
    expect(sectionsWithPreferences({ ...draft, colourApproach: "tonal" })).toBe(1);
    expect(sectionsWithPreferences({ ...draft, fitNotes: "long in the body" })).toBe(1);
    expect(sectionsWithPreferences({ ...draft, budgetPerPiece: "200" })).toBe(1);
  });
});

describe("patch building", () => {
  it("sends nothing when nothing changed", () => {
    const draft = base();
    expect(buildPatch(draft, draft)).toEqual({});
    expect(isDirty(draft, draft)).toBe(false);
  });

  it("sends only the fields that actually changed", () => {
    const original = base();
    const draft = { ...original, colours: cycleStance([], "navy") };
    expect(buildPatch(draft, original)).toEqual({
      colours: [{ slug: "navy", stance: "PREFERRED" }],
    });
  });

  it("sends an empty list when a collection is cleared", () => {
    const original = { ...base(), colours: cycleStance([], "navy") };
    const draft = { ...original, colours: [] };
    // Empty means "clear this", and it must be distinguishable from absent.
    expect(buildPatch(draft, original)).toEqual({ colours: [] });
  });

  it("does not resend a reordered but identical collection", () => {
    const original = {
      ...base(),
      colours: cycleStance(cycleStance([], "navy"), "black"),
    };
    const draft = { ...original, colours: [...original.colours].reverse() };
    expect(buildPatch(draft, original)).toEqual({});
  });

  it("always sends a currency with a budget amount", () => {
    const original = base();
    const draft = { ...original, budgetPerPiece: "200" };
    expect(buildPatch(draft, original)).toEqual({
      budget: { per_piece_minor_units: 20000, currency: "EUR" },
    });
  });

  it("refuses an unparseable budget instead of guessing", () => {
    const original = base();
    const draft = { ...original, budgetPerPiece: "two hundred" };
    expect(() => buildPatch(draft, original)).toThrow(BudgetFormatError);
    // And it still counts as a change, so the save button stays available to fix it.
    expect(isDirty(draft, original)).toBe(true);
  });

  it("carries the personalisation switch", () => {
    const original = base();
    const draft = { ...original, personalizationEnabled: false };
    expect(buildPatch(draft, original)).toEqual({ personalization_enabled: false });
  });
});

describe("error messages are plain language", () => {
  it("explains a conflict rather than showing a status code", () => {
    const message = saveErrorMessage({ status: 409 });
    expect(message).toContain("somewhere else");
    expect(message).not.toContain("409");
  });

  it("explains an expired session", () => {
    expect(saveErrorMessage({ status: 401 })).toContain("Sign in");
  });

  it("falls back to a connection message with no status", () => {
    expect(saveErrorMessage(new Error("boom"))).toContain("connection");
  });

  it("never leaks a server trace", () => {
    const message = saveErrorMessage({ status: 500, message: "Traceback (most recent call last)" });
    expect(message).not.toContain("Traceback");
  });
});

describe("draft construction", () => {
  it("defaults an absent profile to personalisation on", () => {
    // Making a profile IS the opt-in; there is no profile until the customer creates one.
    expect(base().personalizationEnabled).toBe(true);
    expect(base().currency).toBe("EUR");
  });

  it("reflects a disabled profile faithfully", () => {
    const draft = draftFromProfile({
      ...EMPTY_PROFILE,
      exists: true,
      personalization_enabled: false,
      colours: [{ slug: "black", stance: "PREFERRED", source: "USER_EXPLICIT" }],
    });
    expect(draft.personalizationEnabled).toBe(false);
    // Disabled still keeps every value.
    expect(draft.colours).toHaveLength(1);
  });
});
