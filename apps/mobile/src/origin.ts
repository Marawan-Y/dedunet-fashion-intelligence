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
