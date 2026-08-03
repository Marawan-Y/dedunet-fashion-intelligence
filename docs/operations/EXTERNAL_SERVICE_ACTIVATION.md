# External Service Activation

Every external integration currently runs as a sandbox or contract-compatible mock. The platform
is fully testable without any real credential, and no real provider account has been created.

**Nothing in this document records a completed activation.** These are instructions.

---

## Principle

Callers depend on an interface, never on a concrete provider. Activating a real provider means
implementing that interface and setting one environment variable. No caller changes.

A misconfigured provider **fails loudly**. `get_gateway()` raises when `PAYMENT_PROVIDER` names a
provider with no adapter, rather than silently falling back to the sandbox — a fallback there
would mean live money quietly flowing through a mock.

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+pysqlite:///commerce.sqlite3` | Database connection |
| `APP_ENV` | `development` | Environment name; gates unsafe defaults |
| `SESSION_SECRET` | dev-only value | HMAC key for session tokens. **Required outside development** |
| `CORS_ORIGINS` | `http://localhost:13000` | Exact browser origins allowed |
| `ADMIN_API_TOKEN` | `change-me` | Legacy fixture admin API; placeholder returns 503 |
| `PAYMENT_PROVIDER` | `sandbox` | Payment adapter selector |
| `STORE_CURRENCY` | `EUR` | Only EUR has a reviewed minor-unit exponent |
| `API_PORT` / `STOREFRONT_PORT` | `18000` / `13000` | Local host ports |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | unset | Reserved; the shipped stylist does not call a model |

Never commit real values. `.env` is git-ignored and verified absent from history.

---

## 1. Payment provider

**Current:** `SandboxGateway` — deterministic, in-process, no network. Implements authorize,
refund, declines, provider errors and idempotent replay keyed by idempotency key.

**To activate a real provider:**

1. Create an account and obtain **test** credentials first. Never start with live keys.
2. Implement the `PaymentGateway` protocol in `app/commerce/payments.py`:
   ```python
   class StripeGateway:
       name = "stripe"
       def authorize(self, *, amount_minor_units, currency,
                     payment_method_token, idempotency_key) -> AuthorizationResult: ...
       def refund(self, *, provider_reference, amount_minor_units,
                  idempotency_key) -> AuthorizationResult: ...
   ```
3. Pass the idempotency key to the provider's own idempotency mechanism. Do not invent your own.
4. Amounts are already integer minor units — send them unchanged. Do not convert to decimal.
5. Register it in `get_gateway()` and set `PAYMENT_PROVIDER=stripe`.
6. Use a **hosted payment UI**. Raw card data must never reach this platform; nothing here is
   PCI-scoped and it must stay that way.

**Verify:** run the payment tests against the provider's sandbox — success, decline, provider
error, and duplicate idempotency key. All four must behave as the sandbox does. Confirm no card
data appears in any log.

**Do not claim payments are live** until a real test transaction has settled and been reconciled.

---

## 2. Email / SMS / push

**Current:** notifications are written to the `notifications` outbox table. **Nothing sends
them.** No message has ever been delivered.

**To activate:**

1. Build a dispatcher that reads `status = 'queued'`, sends, then marks `sent` or `failed` with
   an attempt count.
2. Make it idempotent — a redelivery after a crash must not send twice. Never delete a row on
   failure.
3. Respect `marketing_consent`. Transactional messages (order confirmation, shipment, refund) are
   not marketing and do not require it; anything promotional does.
4. Verify domain authentication (SPF, DKIM, DMARC) before sending externally.

**Verify:** queue a message, run the dispatcher, confirm exactly one delivery and a `sent` row.
Kill the dispatcher mid-send and confirm no duplicate on restart.

---

## 3. Shipping carrier

**Current:** `mock-carrier` with locally generated tracking numbers. No carrier API is integrated
and no label has ever been produced.

**To activate:** implement a carrier adapter behind the same pattern as payments — rate quote,
label creation, tracking webhook. Treat tracking updates as untrusted input and verify webhook
signatures.

**Verify:** produce one real test label in the carrier's sandbox and confirm the tracking number
resolves on the carrier's own site.

---

## 4. Object storage / CDN

**Current:** none. Product imagery is a CSS gradient placeholder with the product initial.

**To activate:** add a storage adapter, validate uploads (type, size, and content — not just the
extension), strip EXIF, and serve via signed URLs. Never trust a client-supplied filename or
content type.

---

## 5. AI model provider

**Current:** deterministic rule-based scoring over the local catalogue. No model is called.

**To activate:**

1. Keep retrieval grounded in the platform's own catalogue, inventory and policy data.
2. The model may **rank and phrase**. It may not originate a product, price, stock level, size,
   material, delivery promise, return policy or certification.
3. Treat retrieved content and user input as data, never as instructions — a product description
   containing "ignore previous instructions" must not alter behaviour.
4. Implement a deterministic fallback and keep the store fully usable when the model is down.
5. Record evaluation cases and track latency, cost and failure rate before enabling for customers.
6. Never send customer personal data to a model provider without a lawful basis and a processing
   agreement.

**Verify:** an evaluation set where every recommended item exists in the catalogue with the
quoted price and non-zero stock. Any hallucinated item is a release blocker.

---

## 6. Production database

**Current:** SQLite. The models avoid SQLite-only constructs, so PostgreSQL should work by
changing `DATABASE_URL` — but PostgreSQL has **not** been exercised here.

**To activate:** provision the instance, set `DATABASE_URL`, run `alembic upgrade head` against a
copy first, verify with `manage.py check` and the full suite, then cut over. Establish backups
(R8) **before** loading any real data.

---

## 7. App stores

**Current:** no mobile build exists. The Expo project has an unresolved peer-dependency conflict
and has never been installed, built or run.

Store submission requires a working build first. Do not describe the mobile app as delivered, and
never claim App Store or Google Play approval unless an approval actually occurred.

---

## 8. DNS, TLS and hosting

**Current:** none. The platform runs on localhost only.

Before any public exposure, all of the following must be true — this is not a preference list:

- [ ] Named human risk owners for the open launch blockers (CTRL-01)
- [ ] `SESSION_SECRET` set to a real generated secret
- [ ] `ADMIN_API_TOKEN` rotated off the placeholder
- [ ] Rate limiting on login, registration and checkout
- [ ] TLS terminated; HSTS enabled at the edge
- [ ] `CORS_ORIGINS` restricted to the real origin
- [ ] Backups configured **and a restore rehearsed**
- [ ] Monitoring and alerting in place
- [ ] Legal pages reviewed by a qualified adviser
- [ ] All fictional seed data removed
