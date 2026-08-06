/**
 * Origin display rules.
 *
 * The removed proof-of-concept screen rendered `Made in {made_in}` directly from an API
 * field. That is precisely the claim this programme is not allowed to make:
 *
 *   - `docs/KNOWN_LIMITATIONS.md` §1: `country_of_origin` is the deliberately INVALID code
 *     `XX` so it cannot be mistaken for a substantiated claim.
 *   - `CONFLICT-006`: the mandated state is `country_of_origin = XX`,
 *     `intended_origin = EG`, `origin_claim_status = UNVERIFIED`, and the register says in
 *     terms: never render "Made in Egypt" as verified.
 *   - Side A's own package marks every manufacturing, fibre and origin claim as
 *     evidence-gated.
 *
 * The catalog payload carries `country_of_origin` and NOTHING that says whether it was
 * substantiated. Since the application cannot distinguish a verified code from an
 * unverified one, it must not present any code as a factual origin claim. This module is
 * the only place allowed to turn that field into text.
 */

/** Codes that explicitly mean "no substantiated origin". */
const UNSUBSTANTIATED = new Set(["", "XX", "xx"]);

/**
 * Text for a product's origin field, or `null` to render nothing.
 *
 * Never returns a "Made in ..." string. When a real-looking code is present it is labelled
 * as declared and unverified, because no evidence path exists in this payload to support
 * anything stronger.
 */
export function originLabel(countryOfOrigin: unknown): string | null {
  if (typeof countryOfOrigin !== "string") return null;

  const code = countryOfOrigin.trim();
  if (UNSUBSTANTIATED.has(code)) return null;
  if (!/^[A-Za-z]{2}$/.test(code)) return null;

  return `Declared origin ${code.toUpperCase()} — not independently verified`;
}

/**
 * Origin text using the typed states the API now ships.
 *
 * `origin_claim_status` and `intended_origin` must be read TOGETHER. Reading
 * `intended_origin` alone would let a client render "EG" as a factual origin, which is the
 * precise conversion of intent into fact that CONFLICT-006 forbids. Reading
 * `country_of_origin` alone would show a customer the literal string "XX".
 *
 * Falls back to `originLabel` when the states are absent, so the legacy fixture catalogue
 * keeps working against an older API.
 */
export function originStatement(product: {
  country_of_origin?: unknown;
  intended_origin?: unknown;
  origin_claim_status?: unknown;
}): string | null {
  const status =
    typeof product.origin_claim_status === "string" ? product.origin_claim_status.trim() : "";
  const code =
    typeof product.country_of_origin === "string" ? product.country_of_origin.trim().toUpperCase() : "";

  if (status === "" ) return originLabel(product.country_of_origin);

  if (status === "UNVERIFIED" || UNSUBSTANTIATED.has(code)) {
    const intended =
      typeof product.intended_origin === "string" ? product.intended_origin.trim().toUpperCase() : "";
    if (!/^[A-Z]{2}$/.test(intended)) return null;
    // "Intended production in EG" is a statement about a plan, not about a garment.
    return `Intended production in ${intended} — not verified, no origin claim is made`;
  }

  return originLabel(product.country_of_origin);
}

/**
 * Text for a material/fibre field, or `null`.
 *
 * Same gate as origin: seed material values are illustrative placeholders, so the label
 * says "stated" rather than presenting a composition as tested fact.
 */
export function materialLabel(material: unknown): string | null {
  if (typeof material !== "string") return null;
  const value = material.trim();
  if (value === "") return null;
  return `Stated material: ${value}`;
}
