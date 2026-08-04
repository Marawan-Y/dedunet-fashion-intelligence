# Workstream B Correction — Lease Fencing

| Control | Value |
|---|---|
| Artifact ID | EV-WSB-003 |
| Date | 2026-08-04 |
| Owner | Technical lead |
| **Decision** | **`WORKSTREAM_B_VERIFIED_WITH_LEASE_FENCING`** |

The review asked whether `claim_token` acted as a fencing token. **It did not.** The token
was written at claim time and read back for diagnostics, but never appeared in a `WHERE`
clause. Finalization was a read-then-write, so a delayed worker could overwrite the state
of whichever worker had legitimately taken over. This was verified before any code was
written — the instruction said not to rewrite a correct implementation, so the first step
was establishing that it was not correct.

## 1. Finalization design

Every claim-owned write is now a compare-and-set evaluated **by the database at write
time**:

```sql
UPDATE notifications
   SET ...
 WHERE id = :id
   AND status = 'sending'
   AND claim_token = :token
```

`_finalize()` returns `rowcount == 1`. Applied to all six paths: success, retryable
failure, terminal rejection, erased-customer suppression, maximum-attempt terminalization
and claim cleanup. Cleanup is not a separate write — `_CLEARED_CLAIM` is merged into the
same `values`, so metadata cleanup can never drift away from the state change it
accompanies.

The ORM object is no longer mutated. `note_id` and `attempts_at_claim` are captured before
the provider call; the in-memory row may be stale by the time it returns, and those two
values are all the fenced write needs.

**On `rowcount == 0`** the worker treats ownership as lost: it does not retry under a new
token, does not clear anyone's metadata, does not report the row finalized. It increments
`ownership_lost` and logs a safe record.

## 2. Stale-worker race transcript

The exact sequence from the review, executed end to end through the real dispatcher:

```text
A claims (token-A)                    status=sending  attempts=1  token=token-A
A enters send() and is delayed
  -> inside A's provider call, B reclaims and completes:
       B claims (token-B)             status=sending  attempts=2  token=token-B
       B finalizes                    status=sent     provider_reference=B_ref
A's provider call returns "accepted"
A attempts to finalize with token-A   rowcount=0  -> ownership lost

dispatcher counts : {"sent": 0, "ownership_lost": 1, ...}
log               : {"event": "ownership_lost", "notification_id": N,
                     "stage": "success after lease expiry"}
final DB state    : status=sent  provider_reference=B_ref  attempts=2
```

The final state is exactly what the current owner wrote. Nothing of A's survived.

## 3–5. Fencing evidence by path

All nine fencing tests pass on **PostgreSQL**:

| Attempted stale write | Result |
|---|---|
| mark `sent` after B reclaimed | rejected; row stays `failed` (B's state) |
| retryable failure after B completed | rejected; row stays `sent`, `B_ref` intact |
| terminal rejection after B completed | rejected; row stays `sent`, no stale reason recorded |
| clear B's live claim | rejected; `token-B` and lease both intact |
| overwrite B's provider reference | rejected; `B_ref` preserved |
| finalize a settled row with a matching token | rejected; original state preserved |
| B finalizes as current owner | **accepted** — the ordinary path is unaffected |
| any rejected stale write | no row deleted |
| attempts after the race | `2`, consistent with the documented policy |

## 6. Ownership-loss behaviour

Observable three ways: the `ownership_lost` counter, a structured stdout record, and the
absence of any change in the database.

```json
{"component": "notification-dispatch", "event": "ownership_lost",
 "notification_id": 1, "stage": "success after lease expiry",
 "detail": "lease expired and the row was reclaimed; stale write discarded"}
```

The log names the row and the stage and **nothing else** — no recipient address, no message
body, no token value. A test asserts that `token-B` and `@meret.example` are absent from
the output.

Note what this record means in the success case: the provider *did* accept the message. The
delivery happened; this worker simply no longer owns the row and must not claim credit for
it. That is the at-least-once window made visible rather than hidden.

## 7–8. Suites

| Suite | Result |
|---|---|
| SQLite, full, warnings-as-errors | **149 passed**, 1 skipped (PostgreSQL-only) |
| PostgreSQL, full, warnings-as-errors | **150 passed** |

## 9. Mutations

**41 run, 41 detected, 0 survived.** Four new (M38–M41):

| Mutation | Removed | Detected by |
|---|---|---|
| M38 | the `claim_token` condition | live-claim protection |
| M39 | the `status == 'sending'` condition | settled-row finalization |
| M40 | `rowcount` deciding ownership | ownership-loss observability |
| M41 | counting a stale success as `sent` | ownership-loss observability |

**One attack initially survived, and fixing it improved the tests.** Removing the
`status == 'sending'` arm changed nothing, because the existing tests also clear the token
— so the token arm caught the stale write first and the status arm had no independent
coverage. A dedicated test now isolates it: a settled row still carrying its token must not
be finalizable. Without that, a late arrival could overwrite a completed result whenever a
partially-applied write left a token attached.

**Five pre-existing anchors rotted again.** M24, M29, M30, M35 and M36 stopped matching when
the finalization was rewritten, and the harness **errored** rather than skipping them.
Deleting those entries would have produced a clean run in seconds at the cost of five real
guards; all five were re-anchored to the equivalent construct in the new code.

This is the second time in this workstream that rewriting an implementation silently rotted
the guards protecting it. A harness that aborts on a missing anchor is the only reason it
was visible both times.

## 10–11. Commit and status

**`WORKSTREAM_B_VERIFIED_WITH_LEASE_FENCING`**

## Updated limitations

- **`EXTERNAL_SMTP_DELIVERY_PENDING`** — unchanged.
- **At-least-once remains.** Fencing prevents a stale worker corrupting *database* state.
  It cannot un-send a message the provider already accepted, so a duplicate can still reach
  a real mailbox. Both attempts carry the same `notification-<id>` key.
- **`ownership_lost` after a successful send is not a failure.** It means delivery occurred
  but this worker no longer owned the row. An operator reading only the `sent` counter will
  undercount deliveries in that window; the log is the correct source.
- Fencing protects claim-owned finalization. It does not protect against an operator
  editing rows directly.
