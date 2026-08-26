# Production disclosure rule

| Field | Value |
|---|---|
| Artifact ID | GOV-DISC-001 · **Version** 1.0 |
| Status | **DECIDED** — owner instruction, 2026-08-26 |
| Applies to | every customer-facing surface, from now until public launch |
| Owner | Side B / platform |

---

## The rule

**During development, the prototype must keep telling the truth about what is not built.**
That behaviour is accepted and is to be preserved. A surface that quietly omits a missing
capability is worse than one that names it, because the reviewer cannot tell the difference
between "absent" and "broken".

**Before production V1, no customer-facing surface may carry implementation or backlog
language.** The following is a non-exhaustive list of strings that must not survive into
production:

```
NOT BUILT
not modelled
imagery to come
no saved-items model
merchant accounts not built
```

## The only two permitted resolutions

For every such surface, before launch:

| | Resolution |
|---|---|
| **A** | The capability **becomes genuinely functional** |
| **B** | The surface is **removed or hidden from the production user journey** |

**There is no third option.** In particular:

- Deleting the disclosure while leaving the non-functional surface in place is **faking
  completion** and is forbidden.
- Rewording the disclosure into vaguer marketing language is the same act with better
  grammar, and is equally forbidden.
- A control that looks operable and does nothing is the specific defect this whole
  programme exists to prevent.

## Current inventory

Every surface that carries such language today, and which resolution it will need.

| Surface | Language today | Resolution needed |
|---|---|---|
| Saved | "Saving is not built yet", "no saved-items model" | **A** — persistence, or **B** if it slips |
| My Style | "DEDUNET knows nothing about you yet", "Not set" | **A** or **B** |
| Dido | "The intelligence behind it is not built", "Not built" in the input table | **A** or **B** |
| Looks | "Editorially arranged", "personalised selection is not built" | **A** — an outfit engine, or keep as an honest editorial claim, which is resolution A for that narrower promise |
| Look detail | "Not priced", "Saving is not built" | **A** — priced catalogue |
| Brands | "Structure demonstration — not a real brand" | **B** — remove the demonstration entry once real brands exist |
| For Brands | "The merchant platform is not built" | **A** or **B** |
| Product | "Not priced", "Save — not built" | **A** |
| Footer / banner | prototype disclosure, preview-mode notice | **A** — these become the real commerce disclosure, which is a different true statement rather than a deletion |

## Enforcement

This is a **release gate, not a style guide**. Before `PUBLIC_COMMERCIAL_LAUNCH`:

1. Grep the built bundle for the phrases above and for any successor phrasing.
2. For each hit, record which resolution was applied and where it is evidenced.
3. A hit with no recorded resolution **blocks the release**.

The gate is deliberately mechanical. "We reviewed the copy" is not evidence; a list of hits
with a resolution against each one is.
