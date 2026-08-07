# Operational Runbooks

Procedures for the MERET platform. Local/demonstration scope — no production environment exists.

Each runbook states **how to confirm you actually fixed it**, because an incident is not closed
because an action was taken; it is closed when the symptom is gone and evidence says so.

---

## R1 — Failed deployment / service will not start

**Symptoms:** `/health` unreachable, or `/ready` returns 503.

1. Distinguish liveness from readiness. `/health` does no I/O; if it answers, the process is up
   and the fault is a dependency.
   ```bash
   curl -s localhost:18000/health
   curl -s localhost:18000/ready      # reports which check failed
   ```
2. `/ready` names the failing check (`database`, `catalog_fixture`).
3. Database unreachable → R2. Fixture missing → restore from version control.
4. If the process will not start at all, run it in the foreground to see the traceback:
   ```bash
   python -m app.server --port 18000
   ```
   Use `app.server`, never `python -m uvicorn app.main:app`. The bare uvicorn CLI defaults
   to `proxy_headers=True` with `forwarded_allow_ips=127.0.0.1`, which lets any loopback
   client rewrite its own address via `X-Forwarded-For` and bypass the rate limiter. See
   R12.
5. A `RuntimeError` about `SESSION_SECRET` is intentional: outside development the app refuses to
   sign sessions with the known development secret. Set a real secret.

**Confirm fixed:** `/ready` returns 200 with every check `ok`.

**Rollback:** `git revert` the deploying commit; the schema is backward compatible within a
migration revision. If a migration is implicated, see R7.

---

## R2 — Database failure

**Symptoms:** `/ready` reports `database: unavailable`; 500s on write paths.

1. Confirm reachability without the app:
   ```bash
   cd backend && python manage.py check
   ```
2. SQLite: check the file exists, is writable, and the disk is not full. A `database is locked`
   error means a long transaction is open — find and end it; do not delete the file.
3. PostgreSQL: check host, port, credentials and connection-pool exhaustion.
4. Verify schema version matches the code:
   ```bash
   python -m alembic current
   python -m alembic heads
   ```
   If `current` is behind `heads`, apply migrations (R7).

**Confirm fixed:** `manage.py check` exits 0 and `/ready` is 200.

**Never:** delete or recreate the database to clear an error. That destroys order history, which
is the financial record.

---

## R3 — Payment provider outage

**Symptoms:** checkout returns 503; `checkout_failed` analytics events rise.

1. The sandbox adapter raises `PaymentError` for provider faults. Checkout maps that to **503**,
   which tells the client the attempt is retryable and **no money moved**.
2. Confirm stock was released — a failed payment must not hold inventory:
   ```sql
   SELECT o.order_number, o.status, r.state
   FROM orders o JOIN reservations r ON r.order_id = o.id
   WHERE o.status = 'cancelled';
   ```
   Every reservation on a cancelled order must be `released`.
3. Confirm no payment row is `authorized` for a cancelled order:
   ```sql
   SELECT p.id FROM payments p JOIN orders o ON o.id = p.order_id
   WHERE o.status = 'cancelled' AND p.status = 'authorized';
   ```
   This must return zero rows. A row here means a customer was charged for a cancelled order —
   escalate immediately and refund.
4. Customers may retry. Idempotency keys make a retry safe: the same key replays the original
   result rather than charging twice.

**Confirm fixed:** a test checkout with `pm_success` returns 201.

**Fallback:** none automated. Do not "queue" payments for later capture; that promises a charge
the provider never authorized.

---

## R4 — AI provider outage

**Symptoms:** the stylist page shows "The stylist is unavailable right now."

1. This is a **degraded**, not failed, state by design. The catalogue, cart and checkout are
   entirely unaffected and the UI offers a link back to browsing.
2. The shipped stylist is deterministic and local, so an outage here implies the API itself is
   down → R1.
3. If a real model provider is later integrated, it must keep this property: the store must
   remain fully usable without AI.

**Confirm fixed:** stylist returns suggestions; catalogue was never interrupted.

---

## R5 — Inventory inconsistency

**Symptoms:** availability looks wrong; an oversell is suspected.

1. Check the invariant directly:
   ```sql
   SELECT variant_id, on_hand, reserved FROM inventory_items WHERE reserved > on_hand;
   ```
   This must return **zero rows**. A check constraint enforces it, so a row here means the
   constraint was dropped or the database was edited directly.
2. Reconcile reservations against orders:
   ```sql
   SELECT r.variant_id, SUM(r.quantity) FROM reservations r
   JOIN orders o ON o.id = r.order_id
   WHERE r.state = 'held' AND o.status IN ('cancelled','refunded')
   GROUP BY r.variant_id;
   ```
   Held reservations on cancelled or refunded orders are stale and should be released.
3. Correct only via the audited admin endpoint, never with raw SQL:
   `POST /api/v1/admin/variants/{id}/stock` with a delta and a reason.

**Confirm fixed:** the invariant query returns zero rows and the adjustment appears in
`audit_logs`.

---

## R6 — Order processing failure

1. Locate the order and its full trail:
   ```sql
   SELECT * FROM orders WHERE order_number = 'FC-XXXXXXXX';
   SELECT * FROM payments    WHERE order_id = ?;
   SELECT * FROM reservations WHERE order_id = ?;
   SELECT * FROM audit_logs  WHERE entity_id = 'FC-XXXXXXXX';
   ```
2. Use the correlation ID from the access log to follow one request across components.
3. Legal states: `pending_payment → paid → shipped`, or `→ cancelled`, or `→ refunded`.
   Anything else indicates a partial transaction — investigate before touching data.
4. Cancel (releases stock) or fulfil (commits stock) through the admin API so the action is
   audited. Do not edit order rows by hand.

---

## R7 — Migrations

```bash
cd backend
python -m alembic current            # where the database is
python -m alembic upgrade head       # apply
python -m alembic downgrade -1       # step back one revision
```

Both directions of the initial revision have been executed and verified in this repository.

**Before any migration against real data:** take a backup (R8), run against a copy first, and
confirm `downgrade` works on that copy. A migration that has never been reversed is not
reversible — it is untested.

---

## R8 — Backup and restore

**Not yet implemented as an automated procedure.** Do not claim a tested backup.

Manual, SQLite:
```bash
cd backend
sqlite3 commerce.sqlite3 ".backup 'commerce-$(date +%Y%m%d-%H%M).sqlite3'"
sqlite3 commerce.sqlite3 "PRAGMA integrity_check;"     # must print: ok
```

Restore is a file copy back with the service stopped.

**A backup is not a backup until a restore has been rehearsed.** Restore into a scratch copy,
run `manage.py check` and the test suite against it, and record the result. Until that is done,
treat the data as unprotected.

---

## R9 — Secret rotation

1. Rotate `SESSION_SECRET`. Every existing session token becomes invalid immediately — every user
   is signed out. Schedule accordingly.
2. Rotate `ADMIN_API_TOKEN` for the legacy fixture API. While it holds the shipped placeholder,
   that API returns 503 in every environment by design.
3. Never commit a real value. `.gitignore` excludes `.env`, and its absence from history is
   verifiable:
   ```bash
   git log --all --name-only --format="" | grep -c '\.env$'    # must be 0
   ```
4. If a secret was ever committed, rotating it is mandatory — history rewriting alone does not
   un-leak it.

---

## R10 — Elevated error rate

1. The access log is structured JSON with `status`, `duration_ms` and `correlation_id`; sensitive
   fields are redacted before writing.
   ```bash
   grep '"status": 5' api.log | tail -50
   ```
2. Group by path to find the failing route, then follow one `correlation_id` end to end.
3. 402 and 409 are **business outcomes** (declined payment, insufficient stock), not faults. A
   rise in those is a demand or inventory signal, not an incident.
4. 500s are always defects. Capture the traceback and write a failing test before fixing.

---

## R11 — Queue backlog

**Symptoms:** rows in the `notifications` outbox stay at `status = 'queued'` and the count grows.

> Corrected 2026-08-07. This section previously read *"There is currently no dispatcher …
> delivery was never implemented"*, which stopped being true when Workstream B shipped one
> (`4a2c548`, `054fd47`, `c1f0188`). An operator following the old text would have concluded a
> real backlog was expected and stopped investigating. Recorded as CONFLICT-012.

A dispatcher **does** exist: `services/commerce-api/notification_worker.py`, run as a separate
`notification-worker` container in `docker-compose.staging.yml`. It never runs inside the API
process — a delivery thread there would make `/ready` lie about a subsystem it does not check,
and two API replicas would double-send every message.

1. Break the count down by state. A healthy queue drains; `queued` should not grow monotonically.
   ```sql
   SELECT status, COUNT(*) FROM notifications GROUP BY status;
   ```
2. Is the worker alive and cycling? It logs one structured line per lifecycle event.
   ```bash
   docker compose -f docker-compose.staging.yml --env-file .env.staging logs --tail 50 notification-worker
   ```
   `{"event": "started", ...}` then quiet is normal — it sleeps
   `NOTIFICATION_WORKER_INTERVAL_SECONDS` between bounded cycles. Repeated
   `{"event": "cycle_failed", ...}` is the real signal; the `error` field names the cause.
   A single `cycle_failed` mentioning *"the database system is starting up"* immediately after a
   restart is the expected startup race, not an incident — the next cycle recovers.
3. Run one bounded cycle by hand to see the outcome directly:
   ```bash
   docker compose -f docker-compose.staging.yml --env-file .env.staging exec api python manage.py dispatch-notifications
   ```
   It prints `{"dispatched": {"sent": N, "failed": N, "retried": N, "suppressed": N,
   "claimed": N, "ownership_lost": N}}`.
4. Rows stuck in `sending` are **claimed**, not lost. A worker killed mid-send leaves a claim that
   expires after `NOTIFICATION_CLAIM_TTL_SECONDS`, after which another worker may recover it.
   `claim_expires_at` is compared against the DATABASE clock, never a worker-local timer.
   ```sql
   SELECT id, status, attempts, claimed_at, claim_expires_at FROM notifications
   WHERE status = 'sending' ORDER BY claimed_at;
   ```
   Do not clear claims by hand while a worker is running; let the lease expire.
5. `suppressed` counts notifications for erased customers. That is correct behaviour, not a failure.
6. A row that reached `NOTIFICATION_MAX_ATTEMPTS` stops being retried and keeps its `last_error`.
   It is **never deleted** — the row is the record that a message was owed.

**Delivery channel:** `NOTIFICATION_CHANNEL=console` in every current environment. Nothing is sent
to a real mailbox and no inbox delivery is claimed — `EXTERNAL_SMTP_DELIVERY_PENDING`. A growing
queue with a console sender means the worker is not running, not that mail is failing.

**Confirm fixed:** `queued` drains on the next cycle and `sent` increases by the same amount.

---

## R12 — Proxy trust boundary and rate-limit identity

**Symptoms:** the rate limiter appears not to engage; a burst that should return 429 keeps
returning 401/200; `X-RateLimit-Remaining` never falls.

### Why application-level proxy-hop configuration was not enough

`app/rate_limit.py` buckets on `request.client.host` and ignores `X-Forwarded-For` unless
`RATE_LIMIT_TRUSTED_PROXY_COUNT` is raised. That code is correct and it is **read too
late**. uvicorn ships `ProxyHeadersMiddleware` enabled (`proxy_headers=True`) and, with
`forwarded_allow_ips` unset, trusts `127.0.0.1`. For a loopback client it rewrites
`scope["client"]` from the header *before any application code runs*, so the limiter
buckets on an attacker-chosen value and does so faithfully. Reproduced against
`python -m uvicorn app.main:app --port 18300`:

| burst | result |
|---|---|
| 16 logins, no `X-Forwarded-For` | `401` ×10 then `429` ×6 — limiter works |
| 16 logins, a different `X-Forwarded-For` each | `401` ×16 — never limited |

uvicorn does not validate the value either: `X-Forwarded-For: not-an-ip` is accepted as a
client identity. The real peer is unrecoverable afterwards — the middleware overwrites it
and the scope keeps no copy — so this cannot be repaired inside the application.

### Current configuration (unproxied — local and local staging)

Nothing sits in front of the API. `TRUSTED_PROXY_MODE` is unset or `none`, which makes
`app/server.py` pass `proxy_headers=False` **and** `forwarded_allow_ips=[]` explicitly.
No forwarded header is interpreted, from any peer, including loopback.

**The exact safe startup command:**

```bash
python -m app.server --host 127.0.0.1 --port 18000
```

Never `python -m uvicorn app.main:app` and never the bare `uvicorn` CLI: both inherit the
trusting defaults above. Confirm what a running process actually trusts — it logs one
structured line at startup:

```json
{"event": "asgi_proxy_trust_boundary", "mode": "none", "proxy_headers": false, "forwarded_allow_ips": [], "trusted_proxy_hops": 0}
```

### Requirements before putting a reverse proxy in front

`TRUSTED_PROXY_MODE=explicit` refuses to start unless **all** of these are set:

| Variable | Requirement |
|---|---|
| `TRUSTED_PROXY_IPS` | The proxy addresses/networks. `*` is refused. |
| `RATE_LIMIT_TRUSTED_PROXY_COUNT` | `>= 1`. How many hops your own infrastructure appends. |
| `TRUSTED_PROXY_NETWORK_BOUNDARY` | One line stating what stops anything else reaching this port. |

The last one is not paperwork. An allowlist of source addresses is not a boundary if any
host can connect and claim that address; something — a security group, a private network,
mTLS — has to enforce it, and whoever raises this setting has to name it.

**Confirm fixed:** `tests/test_proxy_boundary.py` launches the real supported server
process and asserts that varied and malformed `X-Forwarded-For` values do not mint fresh
buckets. Run it after any change to a startup path.
