# Workstream B — Notification Dispatch

| Control | Value |
|---|---|
| Artifact ID | EV-WSB-001 |
| Date | 2026-08-04 |
| Owner | Technical lead |
| Core dispatch | **`NOTIFICATION_DISPATCH_CORE_VERIFIED`** |
| SMTP adapter | **`SMTP_PROTOCOL_ADAPTER_VERIFIED`** |
| Real delivery | **`EXTERNAL_SMTP_DELIVERY_PENDING`** |
| **Decision** | **`WORKSTREAM_B_VERIFIED`** |

A fake SMTP server proves the protocol. It does not prove that mail reaches a real inbox,
and nothing here claims that it does.

## 1. Architecture summary

Transactional outbox. `queue_notification` writes a row inside the business transaction,
so a delivery failure can never roll back an order that was genuinely placed. A separate
worker process dispatches. The API never delivers.

## 2. Adapter contract

Mirrors `payments.py` deliberately — one pattern per external integration means one set of
review habits.

| Element | Notification |
|---|---|
| Retryable failure | `NotificationError` |
| Terminal failure | `NotificationRejected` |
| Result | `DeliveryResult` (provider, reference, accepted, delivered_at, diagnostics, metadata) |
| Contract | `NotificationSender` Protocol — `name`, keyword-only `send()` |
| Default | `ConsoleSender` |
| Real | `SmtpSender` (stdlib `smtplib`, explicit 5s timeout) |
| Selector | `get_sender()` reads config at call time, **raises** on unknown |
| Test hook | `reset_sender()` |

SMTP exception mapping: recipient/sender refused and authentication failure are
**terminal** (retrying a refused address forever destroys sender reputation);
`SMTPException`, `OSError`, `socket.timeout` are **retryable**. No credential, raw banner
or AUTH exchange is ever surfaced or logged.

## 3. Migration

`b1a7c4e2f903_notification_dispatch_columns`, revises `8d2d3d0f9b6f`.

Adds `attempts`, `sent_at`, `last_error` (**`Text`**, not `String(n)`), `provider_reference`,
a status CHECK (`queued|sending|sent|failed|suppressed`) and `ix_notifications_status`.

`server_default` on every new NOT NULL column. The ORM `default=` runs in Python only;
adding a NOT NULL column without a server default fails on a populated PostgreSQL table.
`last_error` is `Text` because PostgreSQL enforces declared lengths — a long provider error
would raise there while passing silently on SQLite.

Status stays a `String` + CHECK rather than a database enum: converting the type would turn
an `ADD COLUMN` into a type migration and would silently change `note.status` from a `str`
into an enum member, breaking every `== "sent"` comparison.

## 4. Files

**Created:** `app/commerce/notifications.py`, `notification_worker.py`,
`tests/test_notifications.py`, the migration, this evidence file.
**Modified:** `app/commerce/models.py`, `app/commerce/services.py`, `manage.py`,
`tests/conftest.py`, `Dockerfile`, `docker-compose.staging.yml`,
`scripts/validation/mutation_guard_check.py`.

## 5. Migration on PostgreSQL

```text
upgrade   -> Running upgrade 8d2d3d0f9b6f -> b1a7c4e2f903 (Context impl PostgresqlImpl)
columns   -> attempts integer NOT NULL default 0
             sent_at timestamp with time zone NULL
             last_error text NOT NULL default ''::text
             provider_reference character varying NOT NULL default ''::character varying
constraint-> ck_notification_status        index -> ix_notifications_status

downgrade -> 12 columns -> 8, constraint dropped
re-upgrade-> 8 columns -> 12
```

CHECK constraint proven enforced, not merely declared:

```text
INSERT ... status='bogus'
ERROR: new row for relation "notifications" violates check constraint "ck_notification_status"
```

## 6–7. Console and SMTP over a real socket

Console: send succeeds, records `console_…` reference, `attempts=1`, `sent_at` set.

SMTP is verified against a **real TCP socket** — a `socketserver.ThreadingTCPServer` bound
to port 0 speaking enough RFC 5321 for `smtplib` to complete a genuine exchange. A mocked
`send_message` proves only that a mock was called; it cannot catch a malformed envelope, a
missing header or a client that never connects.

Asserted on the bytes that crossed the wire:

```text
MAIL FROM: noreply@meret.example
RCPT TO:   smtp-target@meret.example
Subject: Your order FC-TEST
To: smtp-target@meret.example
X-Notification-Key: notification-<id>
```

The `X-Notification-Key` header carries the outbox row id, so a duplicate arriving at a
real mailbox can be traced back to the row that produced it.

## 8–10. Failure handling

| Case | Evidence |
|---|---|
| Retryable transport failure | Port 1 refuses connections — a genuine failure, not simulated. Row **retained**, status back to `queued`, `attempts=1`, `last_error` prefixed `retryable:` |
| Terminal rejection | Fake server returns `550`. Row **retained**, status `failed`, prefix `terminal:`, never reclaimed |
| Long error | 6000-character error persists untruncated (`Text` column) |
| Max attempts | Ceiling of 3 → `attempts` stops at 3, status becomes `failed`, further cycles claim 0 |
| No deletion | Row count never decreases across success, rejection and suppression |

## 11. Erasure suppression

The sender is **never invoked** for an erased customer — a recording sender raises if
called, and it never was. Row retained with status `suppressed` and a safe reason. No later
cycle resurrects it. A queued email must never undo a completed erasure.

## 12–13. Idempotency and retention

Rerun returns all-zero counts; `attempts` stays 1; status is exactly `sent` with `sent_at`
recorded. Rows are never deleted on any path.

## 14. Concurrent claim on PostgreSQL — and the bug it found

**A serious defect was found here.** The first implementation held the batch with
`SELECT … FOR UPDATE SKIP LOCKED` and committed inside the loop. Row locks last only until
the transaction ends, and the dispatcher *must* commit per row to persist attempts before
sending — so every remaining row in the batch became claimable mid-batch.

Four workers over ten rows produced **19 sends**. In production that is duplicate customer
email.

Fixed with a **durable claim**: one atomic statement moves rows to an intermediate
`sending` state and increments `attempts`, using `FOR UPDATE SKIP LOCKED` in the
sub-select and `RETURNING` to identify exactly the rows claimed. A state change survives
the commit; a lock does not.

```text
4 workers, 10 rows -> 10 sent, every row attempts == 1
```

A retryable failure returns the row to `queued`; a row left in `sending` would be invisible
to every future claim and stuck forever.

## 15. Maximum attempts

Configurable, default **5** (`NOTIFICATION_MAX_ATTEMPTS`). No authoritative specification
fixed this, so it is a documented conservative default rather than a silent invention.
Retryable failures stay `queued` until the ceiling, then become `failed`. Terminal
rejections never retry. Dead-letter procedure: rows in `failed` are the review queue —
query by status, correct the cause, reset `status='queued'` and `attempts=0` to requeue.

## 16. Worker

Separate process, never a thread in the API: a delivery thread would make `/ready` lie
about a subsystem it does not check, would fight the per-request session model, and two API
replicas would double-send.

```text
{"event": "started", "interval_seconds": 15.0, "sender": "console", "pid": 1}
[notification] to=ops@dedunet.example subject='Staging worker delivery' key=notification-2
{"event": "cycle", "sent": 1, "failed": 0, "retried": 0, "suppressed": 0, "claimed": 1}
{"event": "stop_requested", "signal": "SIGTERM"}
{"event": "stopped", "cycles": 4}          exit code: 0
```

Interval 15s, batch 50, max attempts 5. Sleeps in 0.5s slices so SIGTERM is honoured
promptly. Silent when idle — no busy-loop. A failed cycle is logged and the loop continues;
one bad cycle must not stop all delivery silently. Resolves the sender at startup so a
misconfigured channel fails immediately (`startup_failed`, exit 1).

## 17. API readiness is independent of the worker

`/ready` returned 200 while the worker was **crash-looping**, and again while it was
**stopped**. Readiness describes what this process can serve; making it depend on a worker
it cannot observe would pull the API out of rotation for a delivery backlog.

## 18–20. Suites and mutations

| Check | Result |
|---|---|
| SQLite full suite | **128 passed, 1 skipped** (PostgreSQL-only test), 0 warnings |
| PostgreSQL full suite | **129 passed**, 0 warnings |
| Mutation guards | **31** — 8 new (M24–M31) |

## 21. Staging worker

Added to `docker-compose.staging.yml`: same image as the API (so versions cannot drift),
own entrypoint bypassing migrations and the HTTP server, **no ports**, `read_only: true`,
`no-new-privileges`, 256 MiB / 0.5 CPU, `stop_grace_period: 30s`,
`NOTIFICATION_CHANNEL=console`.

## 22. Secret scan

`.env`, `.env.staging` untracked, ignored, absent from history. No SMTP credential exists
anywhere in the repository. `SmtpSender` never logs a credential; `SMTPAuthenticationError`
text is deliberately not echoed because it can contain the attempted username.

## 23. Known limitations

- **`EXTERNAL_SMTP_DELIVERY_PENDING`.** No real provider account. The protocol is proven
  against a fake server; real deliverability, SPF/DKIM/DMARC and reputation are untested.
- **At-least-once delivery.** If the provider accepts a message and the process dies before
  `sent_at` commits, a later cycle re-sends. The alternative — commit after sending — loses
  the attempt record on crash and retries forever. `X-Notification-Key` makes duplicates
  investigable.
- A row can strand in `sending` if the process is killed between claim and outcome. It
  needs manual requeue; no automatic reaper exists yet.
- Console sender logs recipient and subject but **not** the body, which carries order
  numbers and amounts.
- Single worker assumed. `SKIP LOCKED` makes multiple workers safe on PostgreSQL, but this
  is unexercised beyond the 4-thread test.
- No SMS, push, marketing email, message queue or cloud scheduler — all out of scope.

## 24. Rollback

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging stop notification-worker
cd services/commerce-api && python -m alembic downgrade 8d2d3d0f9b6f
git revert --no-edit <workstream-b-commit>
```

The migration downgrade is proven on PostgreSQL. Stopping the worker halts delivery without
affecting the API — queued rows simply accumulate.

## 25–26. Commit and decision

One commit on `dedunet/repository-restructure-and-workstreams-a-f`.

**`WORKSTREAM_B_VERIFIED`**

## Hollow guards found in this workstream

**M29 survived its first run.** Deleting `note.status = "sent"` left the row in `sending`,
which the claim query also excludes — so it was not re-sent, and the "does not resend" test
passed. The real failure was different and worse: the row is *silently stuck forever*,
invisible to every future cycle and to any delivered-count report.

The test now asserts the exact terminal status and that `sent_at` is recorded, which
catches both stranding and re-sending. Asserting only "not re-sent" caught neither.

This is the fifth hollow guard found across the workstreams, and the first the harness
caught by itself rather than by manual attack.
