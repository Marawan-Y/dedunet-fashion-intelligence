# Security

## Reporting a vulnerability

Open a GitHub issue, or use GitHub's private vulnerability reporting if it is enabled on this
repository. Please do not post working exploit details in a public issue before it is fixed.

There is no production deployment and no real customer data, so nothing here is an active
incident. Reports are still welcome — the point of this repository is that its security
reasoning can be checked.

## What this build is

A locally runnable prototype. It cannot transact: `PUBLIC_COMMERCE_MODE` raises rather than
activating, so a real payment path cannot be reached by configuration alone. Every customer,
order and payment in it is fabricated and the payment adapter is a sandbox.

## Controls that are real, and tested

| Control | Where |
|---|---|
| Purchase refused by commerce mode, sellable flag and commerce route, in that order | `app/commerce/commerce_action.py`, server-side |
| `PUBLIC_COMMERCE_MODE` cannot be enabled by environment variable | `app/commerce/modes.py` |
| Password hashing — PBKDF2-SHA256 | `app/commerce/security.py` |
| Rate limiting, on by default | `app/commerce/rate_limit.py` |
| Forwarded-header handling — the server trusts no proxy by default | `app/server.py`, `TRUSTED_PROXY_MODE=none` |
| Document security headers, including a guard that a future nginx location cannot silently drop them | `apps/consumer/security-headers.conf`, `tests/test_consumer_security_headers.py` |
| External-link safety — https allow-list, validated at write time, `noopener` enforced | `app/commerce/brands.py` |
| No markup sinks in browser clients | `tests/test_frontend_security.py` |
| Guard mutation testing — each safety guard is removed and the suite must fail | `scripts/validation/mutation_guard_check.py` |

## Known gaps, stated rather than hidden

These are **open** and recorded in [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md):

- **Client identity behind a proxy.** Under the same-origin proxy the rate limiter keys on the
  proxy container's address, not the client's. Acceptable for single-user LAN staging; not
  acceptable for hosted multi-user production.
- **Rate limiting is in-process.** Buckets live in process memory, so the deployment is
  single-replica by construction.
- **Static media shares the general API limiter.** One page load costs roughly 22 requests to
  the API origin, about 20 of them media. The limiter was deliberately not raised to hide it.
- **No TLS in the local stack.** HSTS is deliberately not set over plain HTTP rather than set
  misleadingly.

## What is deliberately not in this repository

The domain ownership certification for `dedunet.com` is real and names a real registrant. It
was removed from the working tree and from all history before first publication. See
[`evidence/governance/domain/README.md`](evidence/governance/domain/README.md).

No `.env` file has ever been committed — CI asserts this on every run.
