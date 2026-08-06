/**
 * Origin-claim guard.
 *
 * The single rule under test: no code path produces the string "Made in". The removed PoC
 * rendered `Made in {made_in}` straight from the API, which is the unverified origin claim
 * CONFLICT-006 and KNOWN_LIMITATIONS §1 both forbid.
 */

import { materialLabel, originLabel, originStatement } from "../origin";

describe("originStatement — typed states from the DEDUNET API", () => {
  it("never renders 'Made in' for any combination of states", () => {
    const codes = ["XX", "EG", "DE", "", "  ", "Egypt", null, 7];
    const statuses = ["UNVERIFIED", "VERIFIED", "", null, 42];
    for (const country_of_origin of codes) {
      for (const origin_claim_status of statuses) {
        for (const intended_origin of codes) {
          const text = originStatement({
            country_of_origin,
            origin_claim_status,
            intended_origin,
          });
          if (text !== null) {
            expect(text.toLowerCase()).not.toContain("made in");
          }
        }
      }
    }
  });

  it("states intended production as a plan, never as an origin", () => {
    const text = originStatement({
      country_of_origin: "XX",
      intended_origin: "EG",
      origin_claim_status: "UNVERIFIED",
    });
    expect(text).toBe("Intended production in EG — not verified, no origin claim is made");
    expect(text).toContain("not verified");
    expect(text).not.toContain("Made in");
  });

  it("renders nothing when the intended origin is absent", () => {
    expect(
      originStatement({ country_of_origin: "XX", intended_origin: "", origin_claim_status: "UNVERIFIED" })
    ).toBeNull();
  });

  it("never leaks the literal placeholder XX to a customer", () => {
    const text = originStatement({
      country_of_origin: "XX",
      intended_origin: "EG",
      origin_claim_status: "UNVERIFIED",
    });
    expect(text).not.toContain("XX");
  });

  it("falls back to the legacy label when the API sends no typed status", () => {
    // The fixture catalogue predates these fields; a client that required them would
    // break against an older API.
    expect(originStatement({ country_of_origin: "XX" })).toBeNull();
    expect(originStatement({ country_of_origin: "EG" })).toBe(
      "Declared origin EG — not independently verified"
    );
  });
});

describe("originLabel", () => {
  it("renders nothing for the deliberately invalid XX code", () => {
    expect(originLabel("XX")).toBeNull();
    expect(originLabel("xx")).toBeNull();
    expect(originLabel(" XX ")).toBeNull();
  });

  it("renders nothing when the field is empty or absent", () => {
    expect(originLabel("")).toBeNull();
    expect(originLabel("   ")).toBeNull();
    expect(originLabel(null)).toBeNull();
    expect(originLabel(undefined)).toBeNull();
    expect(originLabel(42)).toBeNull();
  });

  it("never emits a 'Made in' claim for any input", () => {
    const inputs = ["EG", "eg", "DE", "IT", "XX", "", "  ", "Egypt", "Made in Egypt", null, 7];
    for (const input of inputs) {
      const label = originLabel(input);
      if (label !== null) {
        expect(label.toLowerCase()).not.toContain("made in");
      }
    }
  });

  it("labels a real-looking code as declared and unverified", () => {
    const label = originLabel("EG");
    expect(label).toBe("Declared origin EG — not independently verified");
    expect(label).toContain("not independently verified");
  });

  it("rejects anything that is not a two-letter code", () => {
    // "Egypt" as free text must not be promoted into an origin statement.
    expect(originLabel("Egypt")).toBeNull();
    expect(originLabel("E")).toBeNull();
    expect(originLabel("EGY")).toBeNull();
    expect(originLabel("E1")).toBeNull();
  });
});

describe("materialLabel", () => {
  it("marks composition as stated rather than tested", () => {
    expect(materialLabel("100% Egyptian cotton")).toBe("Stated material: 100% Egyptian cotton");
  });

  it("renders nothing for an empty value", () => {
    expect(materialLabel("")).toBeNull();
    expect(materialLabel("  ")).toBeNull();
    expect(materialLabel(null)).toBeNull();
  });
});
