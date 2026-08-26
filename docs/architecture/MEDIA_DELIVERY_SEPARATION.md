# Platform action — separate static media delivery from API abuse protection

| Field | Value |
|---|---|
| Artifact ID | PLAT-ACT-001 · **Version** 1.0 |
| Status | **OPEN — NOT STARTED.** Recorded during acceptance closeout; deliberately not acted on |
| Raised by | measurement during the Home visual rebuild, 2026-08-26 |
| Owner | Side B / platform |
| Blocks | not team acceptance; **a public-launch consideration** |

> **The limiter was not changed and must not be changed to close this.** Raising a global
> security limit to hide a measurement is the wrong repair, and the owner ruled that out
> explicitly at closeout.

---

## The measurement

Taken against the deployed consumer candidate, on the real staging API:

```
ONE Home load  ->  22 requests to the API origin
                   20 of them  /api/v1/media/   static brand artwork
                    2 of them  /api/v1/          commerce mode + catalogue
```

The limiter's `default` rule is **300 requests per 60 seconds, per client IP**,
process-local, token bucket — and it covers `/api/v1/media/`.

Verified directly against the running API:

```
400 concurrent GET /api/v1/commerce/mode  ->  233 x 200,  167 x 429
```

## What that means

Roughly **thirteen Home loads a minute** from a single address before that address is
throttled. A throttled media request renders as a broken plate, because the browser
completes the request and receives nothing usable.

Nothing is malfunctioning. The limiter is doing exactly what it was written to do, and it
was written before any page was rich enough for the ratio to matter. The observation is
narrower and more specific:

**One bucket is shared between the highest-risk endpoints and the highest-volume,
lowest-risk one.** A media fetch costs the same token as a login attempt.

Two consequences follow, and only the second is hypothetical:

- **Measured:** the browser suite now runs single-worker, because at two workers it
  exceeded the limit and the application correctly rendered 429 states that the suite read
  as missing features.
- **Expected:** a real customer browsing roughly a dozen image-rich pages inside a minute
  would be throttled, and would see broken artwork rather than an error.

## Target architecture

Three policies rather than one, matched to what each endpoint actually costs and risks:

| Tier | Endpoints | Policy |
|---|---|---|
| **Static / object media** | `/media/*` — brand artwork, product plates | Cache and CDN policy. Long-lived immutable caching, content-hashed paths, ideally served from a separate origin or object store so it never touches the API's limiter at all |
| **Business API** | catalogue, commerce mode, profile reads | The general API policy — roughly today's `default` |
| **Sensitive** | auth, AI/styling, checkout | Stricter dedicated policies, tighter than today's `login` and `register` rules |

The first tier is the one that closes this: **static media should not be behind the business
API's abuse protection**, because it is neither expensive to serve nor useful to abuse, and
it is what a rich page fetches twenty of.

## Constraints on whoever picks this up

- **Do not raise the global limit.** It exists for endpoints where the cost is real —
  `login` is PBKDF2 at 240k rounds and is a CPU-exhaustion vector.
- **Do not disable rate limiting for a path prefix as a shortcut.** Media served from the
  API origin still consumes a connection and still deserves a bucket, just a different one.
- `MULTI_REPLICA_DEPLOYMENT_BLOCKED_PENDING_SHARED_OR_GATEWAY_RATE_LIMITING` (L7) is still
  open. The limiter is process-local, so any gateway-level work here should be designed
  alongside that, not in front of it.
- Whatever lands must keep the current behaviour that **a 429 does not clear a session
  token**. That is accepted, human-verified behaviour and it is what kept the 401 guard
  correct while this was being diagnosed.

## What was done instead, at closeout

Nothing to the product. The browser suite was reduced to one worker and the reason recorded
in `playwright.config.ts` and in `evidence/phase-3/HOME_VISUAL_REBUILD.md`. This document is
the follow-up action, not its resolution.
