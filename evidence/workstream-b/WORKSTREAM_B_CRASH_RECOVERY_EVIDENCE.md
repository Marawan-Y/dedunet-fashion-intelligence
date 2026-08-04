# Workstream B Correction — Abandoned-Claim Recovery

| Control | Value |
|---|---|
| Artifact ID | EV-WSB-002 |
| Date | 2026-08-04 |
| Owner | Technical lead |
| Supersedes | The "rows can strand in `sending`" limitation in EV-WSB-001 |
| **Decision** | **`WORKSTREAM_B_VERIFIED_WITH_CRASH_RECOVERY`** |

The review was correct. EV-WSB-001 *documented* stranded `sending` rows as a limitation
instead of solving it. A durable claim without an expiry does not remove the concurrency
failure — it converts a double-send into a permanent stall, which is quieter and therefore
worse. This correction bounds that window and proves it by execution.

## 1. Migration

`c2f8d1b40e77_notification_claim_lease`, revises `b1a7c4e2f903`.

| Column | Type | Null | Purpose |
|---|---|---|---|
| `claimed_at` | `timestamptz` | yes | when the claim was taken |
| `claim_expires_at` | `timestamptz` | yes | lease deadline; **indexed** |
| `claim_token` | `varchar(64)` | no, `''` | which worker holds it |

`ix_notifications_claim_expires_at` exists because the claim query filters on it every
cycle.

## 2. Migration up / down / up on PostgreSQL

```text
upgrade   b1a7c4e2f903 -> c2f8d1b40e77   3 claim columns + index present
downgrade c2f8d1b40e77 -> b1a7c4e2f903   claim columns: 0
upgrade   b1a7c4e2f903 -> c2f8d1b40e77   claim columns: 3
```

## 3. Claim-state transitions

| From | Event | To | `attempts` | Claim metadata |
|---|---|---|---|---|
| `queued` | claimed | `sending` | +1 | set (`claimed_at`, `claim_expires_at`, `claim_token`) |
| `sending`, lease **live** | another worker polls | `sending` | unchanged | untouched — **not** reclaimable |
| `sending`, lease **expired** | recovered | `sending` | +1 | replaced with the new worker's |
| `sending` | delivered | `sent` (+`sent_at`, `provider_reference`) | — | **cleared** |
| `sending` | retryable failure | `queued` | — | **cleared** |
| `sending` | terminal rejection | `failed` | — | **cleared** |
| `sending` | attempts ≥ max | `failed` | — | **cleared** |
| `sending` | recipient erased | `suppressed` | — | **cleared** |

No state loops back into an unbounded `sending`. `sent`, `failed` and `suppressed` are
terminal and are never claimed again, **even with an expired lease** — an exhausted row
cannot be resurrected by abandonment.

## 4. TTL and validation

`NOTIFICATION_CLAIM_TTL_SECONDS`, default **300**, read at call time.

Rejected with a clear message: `0` and `-5` ("must be positive"), `abc` ("must be an
integer"). A non-positive lease would make every claim instantly stale and let two workers
dispatch the same row simultaneously — precisely the failure the lease exists to prevent,
so it fails loudly rather than defaulting.

**Expiry is compared database-side.** `func.now()` on PostgreSQL, `CURRENT_TIMESTAMP` on
SQLite; the deadline is written with a database expression too. Two workers on hosts with
drifted clocks must reach the same verdict on staleness, and only the database observes one
consistent clock. No worker-local timer participates in claim validity.

## 5. Pre-expiry: a live claim is protected

```text
crash after claim -> status=sending, attempts=1, lease recorded
second dispatch   -> claimed=0, attempts still 1
```

## 6. Post-expiry: recovery and settlement

```text
lease aged past its deadline
next dispatch -> claimed=1, sent=1
row           -> status=sent, attempts=2, claim_expires_at=NULL, claim_token=''
```

## 7. Concurrent stale-claim recovery

Two workers both offered the same expired claim: `sum(claimed) == 1`, `attempts == 2`.
Recovery does not itself become a double-send.

## 8. Hard worker termination in staging

Not simulated — the container was actually killed.

```text
row 3 seeded as an abandoned claim (status=sending, lease 300s in the past)
docker kill --signal=KILL   ->  exit code 137
worker restarted            ->  {"event": "started", "sender": "console"}
                                [notification] to=ops@dedunet.example key=notification-3
                                {"event": "cycle", "sent": 1, "claimed": 1}
outbox                      ->  3 status=sent attempts=2 claim_token='' expires=NULL
```

## 9. Provider-accepted crash window

Executed, not described:

```text
provider accepts -> worker dies before the sent commit
row  -> status=sending, sent_at=NULL          (accepted but uncommitted)
lease expires
retry -> same idempotency key: notification-<id>
row  -> status=sent
```

**At-least-once, never exactly-once.** The provider may observe a duplicate. Both attempts
carry the same stable, row-derived key, so a duplicate at a real mailbox is correlatable
rather than mysterious.

The crash is simulated with `KeyboardInterrupt`, which derives from `BaseException` and so
cannot be swallowed by the dispatcher's `except NotificationError` handlers. That makes it a
faithful stand-in for SIGKILL rather than a handled error path wearing a crash costume.

## 10. Stable key across retries

`recorded == [first_key]` and `first_key == "notification-<id>"`. The key is derived from
the row, not from the attempt, so every retry of the same notification presents the same
identifier.

## 11. Maximum attempts vs repeated abandonment

A row abandoned repeatedly stops at the ceiling (`attempts <= 3`) and becomes terminal. A
further expired lease claims **0** rows.

## 12–14. Suites and mutations

| Check | Result |
|---|---|
| SQLite full suite | **140 passed**, 1 skipped (PostgreSQL-only), 0 warnings |
| PostgreSQL full suite | **141 passed**, 0 warnings |
| Mutation guards | **37** — 6 new (M32–M37) |

Each new guard was attacked individually **before** being added, and each failed the
intended test for the intended reason:

| Mutation | Removed | Detected by |
|---|---|---|
| M32 | the stale-claim recovery arm | abandoned-claim recovery test |
| M33 | `claim_expires_at < now` | live-claim protection test |
| M34 | persisting the lease | post-termination state test |
| M35 | clearing the claim on success | metadata-cleared test |
| M36 | clearing the claim on terminal failure | metadata-cleared test |
| M37 | the positive-TTL check | TTL validation test |

Two pre-existing anchors (M25, M26) stopped matching because the claim query was rewritten.
Both were re-anchored to the new structure rather than deleted — a mutation that no longer
applies is a guard silently lost.

## 15. Updated known limitations

- **`EXTERNAL_SMTP_DELIVERY_PENDING`** — unchanged. No real provider account exists.
- **At-least-once delivery.** Now demonstrated rather than asserted. Exactly-once is not
  claimed and is not achievable without provider-side deduplication.
- **A recovery is indistinguishable from a first attempt at the provider.** The key is
  identical by design; only `attempts` in the database reveals it was a retry.
- **The TTL is a guess about provider latency.** 300s comfortably exceeds a 5s SMTP
  timeout, but a future provider with long-running calls would need it raised. Too short
  causes duplicate sends; too long delays recovery. It is configurable for that reason.
- Rows in `failed` remain a manual review queue; there is still no automated dead-letter
  process.
- The lease bounds abandonment; it does not detect a *hung* worker still holding a live
  lease. Such a worker keeps renewing nothing and its claim simply expires — correct, but
  it means detection is by timeout, not by liveness.

## 16. Rollback

```bash
cd services/commerce-api && python -m alembic downgrade b1a7c4e2f903   # drops lease columns
git revert --no-edit <this-commit>
```

Downgrade is proven on PostgreSQL. Reverting restores the previous dispatcher, which
reintroduces the stranding risk this correction removed — that is the trade-off, and it is
why the revert is documented rather than recommended.

## 17–18. Commit and status

**`WORKSTREAM_B_VERIFIED_WITH_CRASH_RECOVERY`**
