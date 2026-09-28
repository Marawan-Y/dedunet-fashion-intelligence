# Domain ownership evidence — held privately, deliberately

| Field | Value |
|---|---|
| Artifact ID | EV-GOV-DOM-002 · **Version** 2.0 |
| Domain | `dedunet.com` |
| Status | **`HUMAN-VERIFIED`** — registrar-issued certification letter, reviewed by the owner |
| Evidence location | **NOT in this repository.** Held by the owner offline |
| Owner | Repository owner (secrets and infrastructure risk owner) |

## Why this document is a placeholder

The domain ownership evidence — a Cloudflare registrar certification letter for `dedunet.com`
— is **real**, and it names a **real registrant** against a **real registration**. Everything
else in this repository is fabricated: no company, factory, supplier, product, certification
or customer exists, and every price, order and customer is invented. This one artifact was the
exception, and that made it the one artifact that did not belong in a public repository.

It was removed from the working tree **and from all 84 commits of history** before this
repository was first published, and the objects were pruned. A redacted copy that removes the
residential address, telephone number and email address still identifies a named individual
against a dated registration, so redaction was not sufficient on its own.

The generator script that produced the redacted PDF
(`scripts/validation/make_redacted_domain_evidence.py`) was removed with it, because it
hard-coded the same registrant name, registrar and name servers. Removing the document while
keeping the script that reproduces it would have achieved nothing.

## What this does not change

The verification **happened** and its result stands. `dedunet.com` is registered to the
repository owner through Cloudflare, confirmed by a registrar-issued letter and recorded as
`HUMAN-VERIFIED` at the time. What changed is where the document is kept, not whether it
exists.

`LEGAL_CLEARANCE_PENDING` is unchanged. Owning a domain is not trademark clearance, not a
registered company, and not permission to trade under the name. See
[`docs/KNOWN_LIMITATIONS.md`](../../../docs/KNOWN_LIMITATIONS.md).

## For a reader auditing the governance trail

If you are verifying this project's evidence discipline, this file is the honest answer to
"where is the domain evidence": it is real, it was verified, and it is withheld because
publishing a named individual's registrar document to satisfy a documentation convention would
be the wrong trade. A governance trail that discloses someone's legal registration to look
complete has misunderstood what it is for.

Requests for verification go to the repository owner.
