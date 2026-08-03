# Workstream C — Rate Limiting

| Control | Value |
|---|---|
| Artifact ID | EV-WSC-001 |
| Version | 1.0 |
| Date | 2026-08-03 |
| Owner | Technical lead |
| **Decision** | **`WORKSTREAM_C_VERIFIED`** |

## 1. Architecture summary

Token bucket, standard library only. `security.py` already establishes that
security-critical paths carry no unvetted dependency, and a bucket is a few lines of
integer arithmetic.

**Token bucket, not fixed window.** A fixed window permits a 2× burst across the
boundary — ten requests at 11:59:59 and ten more at 12:00:00 both pass a "10 per minute"
window. A sliding log has unbounded memory. A bucket is O(1) per key, allows a deliberate
burst up to capacity, and refills smoothly.

**The clock is injectable.** Tests advance a fake clock instead of sleeping; a suite that
sleeps stops being run.

**Configuration is read at call time**, following the `payments.get_gateway` precedent,
because `config.Settings` is a frozen dataclass evaluated once at import and could not
vary per test.

## 2. Files created and modified

**Created:** `app/rate_limit.py`, `tests/test_rate_limit.py` (24 tests),
`evidence/workstream-c/WORKSTREAM_C_EVIDENCE.md`

**Modified:** `app/main.py` (middleware + expose_headers), `tests/conftest.py` (autouse
reset), `scripts/validation/mutation_guard_check.py` (+4 mutations)

## 3. Middleware-order proof

`Starlette.add_middleware` does `user_middleware.insert(0, ...)` and builds the stack with
`reversed()`, so **the last-registered middleware is outermost**. The limiter is therefore
registered **first**, which places it **innermost**.

```text
user_middleware (index 0 = OUTERMOST):
  [0] BaseHTTPMiddleware   <- correlation_and_access_log
  [1] CORSMiddleware
  [2] BaseHTTPMiddleware   <- rate_limit_middleware
```

Applied chain: **correlation → CORS → limiter → routes.** A short-circuited 429 therefore
passes back out through CORS (so a browser can read it) and through the logger (so it is
recorded and carries a correlation ID). Registering the limiter last would place it
*outside* CORS and a browser would see an opaque network error.

## 4. Limits and bucket keys

| Scope | Limit | Key | Why this value |
|---|---|---|---|
| `POST …/auth/login` | 10 / minute | `login:<client-ip>` | PBKDF2 at 240k rounds makes each attempt expensive server-side — a CPU-exhaustion vector as much as credential stuffing |
| `POST …/auth/register` | 5 / hour | `register:<client-ip>` | Account farming; humans register once |
| `/cart*` **without** `X-Cart-Token` | 20 / minute | `cart_anonymous:<client-ip>` | Every tokenless call **creates a Cart row**; unbounded table growth |
| Everything else | 300 / minute | `default:<client-ip>` | Blanket backstop |
| `/health`, `/ready` | **exempt** | — | The compose healthcheck polls `/ready` every 10s; throttling it would make an orchestrator restart a healthy API |

Tokenized cart requests fall to the generous default bucket — a returning shopper reuses
an existing row and is not the abuse case.

## 5–8. Test commands, outputs and burst transcript

```bash
cd services/commerce-api && PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q
```

| Suite | Result |
|---|---|
| SQLite, full, warnings-as-errors | **112 passed, 0 warnings** |
| PostgreSQL, full, warnings-as-errors | **112 passed, 0 warnings** |
| `tests/test_rate_limit.py` | 24 passed |

**Live burst against the containerised API** (not only the TestClient):

```text
$ 15 rapid invalid logins
401 401 401 401 401 401 401 401 401 401 429 429 429 429 429
```

Ten 401s then five 429s, in that order — the limit engages *after* the allowance.

## 9. CORS and correlation evidence — the 429 in full

```text
HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
x-ratelimit-reset: 55
retry-after: 1
access-control-expose-headers: X-Correlation-ID, Retry-After, X-RateLimit-Limit,
                               X-RateLimit-Remaining, X-RateLimit-Reset
access-control-allow-origin: http://localhost:13000
x-correlation-id: e758001b181a570e

{
    "detail": "rate limit exceeded",
    "reason": "RATE_LIMIT_EXCEEDED",
    "scope": "login",
    "retry_after_seconds": 1
}
```

Traceback / "Internal Server Error" occurrences in the body: **0**. `/ready` → 200 and
`/health` → 200 immediately after the burst.

## 10. Proxy trust

```text
X-Forwarded-For: 10.0.0.1 -> 401   (one token remained)
X-Forwarded-For: 10.0.0.2 -> 429
X-Forwarded-For: 10.0.0.3 -> 429
```

A different spoofed IP per request does **not** mint a fresh bucket. Honouring
`X-Forwarded-For` unconditionally would be worse than having no limiter at all, since any
client could bypass it with one header. It is trusted only when
`RATE_LIMIT_TRUSTED_PROXY_COUNT > 0`, and then only the entry that many hops from the
right. A non-numeric value fails safe to the direct peer rather than crashing.

## 11–12. Default-enabled and cart-token behaviour

`rate_limiting_enabled()` returns `True` when `RATE_LIMIT_ENABLED` is absent; only
`0`/`false`/`no` disable it. A request carrying a valid `X-Cart-Token` succeeds even after
the tokenless bucket is fully exhausted.

## 13. Mutation guards

**23 mutations: 23 detected, 0 survived.** Four are new (M20–M23): limiter enabled by
default, health/ready exemption, XFF not trusted, rate-limit headers exposed.

## 14. Performance / smoke

The limiter adds one dictionary lookup and a few floating-point operations per request.
Suite wall time is unchanged within noise (~29s before, ~30s after, for 24 more tests).
Live container smoke after rebuild: catalog 200, `/ready` 200, storefront 200, admin 200.
No load test was run and none is claimed.

## 15. Known limitations

- **Process-local. Single API process or replica only.** Buckets live in this process's
  memory; two processes mean two independent bucket sets and twice the effective limit.
  `uvicorn --workers N` multiplies it by N. **Multi-replica deployment must remain blocked
  until a shared (Redis) or gateway-level limiter exists.** This is a deployment
  constraint, not a code TODO.
- Redis, distributed limiting and WAF rules are explicitly out of scope for Workstream C.
- Keyed per IP, so clients behind one NAT share a bucket. Acceptable for the abuse classes
  targeted; a per-account limit would be a separate control.
- CI remains `CI_CONFIGURATION_VALIDATED_LOCALLY`.

## 16. Rollback

```bash
git revert --no-edit <workstream-c-commit>
docker compose up --build --detach
```

Or disable at runtime without a deploy: `RATE_LIMIT_ENABLED=0`. That is an operational kill
switch, not the default — a test asserts the default is enabled, and M20 fails if anyone
changes it.

No schema change, no migration, no data touched. Rollback is a code revert only.

## 17. Commit

See repository log; this workstream is one commit on
`dedunet/repository-restructure-and-workstreams-a-f`.

## 18. Decision

**`WORKSTREAM_C_VERIFIED`**

## The false guard caught in this workstream

The CORS test initially asserted only `Access-Control-Allow-Origin`. Deleting
`expose_headers` entirely — the exact regression the requirement targets — left all 24
tests passing.

Headers being *present on the wire* is not the property that matters. Without
`Access-Control-Expose-Headers` a browser is **forbidden** from reading them, so client
code cannot honour `Retry-After` even though the server sent it. The test now asserts the
exposed set, and the mutation is detected (M23).

This is the third false guard found by attacking my own tests rather than trusting a green
run: the R0 fail-closed check that was really crashing, the Workstream A datetime test that
passed with the normaliser deleted, and this one.
