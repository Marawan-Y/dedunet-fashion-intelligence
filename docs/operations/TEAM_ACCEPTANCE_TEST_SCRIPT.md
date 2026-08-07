# DEDUNET — team acceptance test script

**For:** a team member testing the complete internal system on their own machine.
**Reviewed at commit:** `fc7bdeb` · **Decision:** [`READY_FOR_TEAM_ACCEPTANCE_TESTING`](../system-of-record/TEAM_ACCEPTANCE_READINESS_DECISION.md)

Nothing here touches real money, real stock, real customers or a real mailbox. Payments run
against a sandbox adapter, stock is explicitly synthetic, and mail goes to the console.

**Requirements:** Docker Desktop running, Python 3.12+, Node 20+. Nothing else — no public
DNS, no payment account, no SMTP, no Apple or Google membership, no trademark clearance.

> ## ⚠️ Read before you finish: two different shutdowns
> | Command | Effect |
> |---|---|
> | `docker compose ... down` | Stops and removes containers. **Your database survives.** This is the one you want. |
> | `docker compose ... down -v` | Also deletes the named volumes — **your PostgreSQL data is destroyed.** |
>
> Only use `-v` when you deliberately want a fresh empty database. Step 19 uses the safe form.

---

## 0. One-time setup

```bash
cd Fashion_Commerce_Codex_Multi_Agent_Pack
cp .env.staging.example .env.staging
```

Then edit `.env.staging` and set real values for `POSTGRES_PASSWORD`, `SESSION_SECRET`
(32+ characters) and `ADMIN_API_TOKEN`. The API **refuses to start** with the shipped
placeholders — that refusal is a control, not a bug.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 1. Start local staging

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

Expect `db`, `api`, `notification-worker` and `web` to come up, with `api` reaching
`(healthy)`.

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging ps
```

## 2. Confirm readiness

```bash
curl -s localhost:18080/ready
```

Expect `{"status":"ready","checks":{"database":"ok","catalog_fixture":"ok"}}`.
`/health` proves the process is alive; `/ready` proves it can actually serve.

Confirm the two startup contract lines — what this process trusts, and where its brand
assets come from:

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging logs api | grep -E "asgi_proxy_trust_boundary|brand_media_root"
```

Expect `"proxy_headers": false`, `"forwarded_allow_ips": []`, and
`"media_root": "/app/brand-assets"`.

## 3. Open the web storefront

<http://127.0.0.1:13080/storefront/>

Expect the DEDUNET wordmark in the header, five products, and **product thumbnails that
actually render**. If a thumbnail is blank, that is a real defect — report it. (Automation
cannot verify this one; a human with a visible browser is the check.)

## 4. Open the mobile application

```bash
cd apps/mobile
npm ci
EXPO_PUBLIC_API_BASE=http://127.0.0.1:18080 npm run web
```

Expect the same five products at the same prices. On the product page expect a four-image
gallery labelled Front, Back, Detail, In context, and the line
*"Concept artwork — not product photography."*

For a device or emulator use `npm start`. The API base differs per platform — Android
emulators reach the host at `10.0.2.2`, never `127.0.0.1`. See `apps/mobile/README.md`.

## 5. Open the admin portal

<http://127.0.0.1:13080/admin/>

Sign in with the administrator you create here — the entrypoint never creates one:

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging exec api python manage.py create-admin
```

It reads `ADMIN_BOOTSTRAP_EMAIL` and `ADMIN_BOOTSTRAP_PASSWORD` from `.env.staging` and
never prints the password.

## 6. Enter preview mode

`BRAND_PREVIEW_MODE` is the state the brand is actually in: everything visible, nothing
purchasable.

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging stop api
COMMERCE_MODE=BRAND_PREVIEW_MODE docker compose -f docker-compose.staging.yml --env-file .env.staging up -d api
```

## 7. Verify the DEDUNET catalogue

```bash
curl -s localhost:18080/api/v1/catalog/products | python -m json.tool | grep -c external_product_id
```

Expect **5**. In the browser confirm all five products render with imagery, and that
The Source Tee shows four ordered media. Expect every product to read **SOLD OUT** and the
origin line to say *"Intended production in EG — not verified, no origin claim is made"*.

Try to add to the bag. Expect a refusal naming brand preview:

```bash
curl -s -X POST localhost:18080/api/v1/cart/items -H 'Content-Type: application/json' -d '{"variant_id":1,"quantity":1}'
```

Expect `409` and *"this catalogue is in brand preview; nothing is available to purchase"*.

## 8. Switch explicitly to commerce-test mode

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging stop api
COMMERCE_MODE=COMMERCE_TEST_MODE docker compose -f docker-compose.staging.yml --env-file .env.staging up -d api
```

`PUBLIC_COMMERCE_MODE` is not a third option — see step 18.

## 9. Load synthetic inventory

Explicitly, onto one SKU, with a deliberately verbose confirmation flag:

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging exec api \
  python manage.py load-test-inventory --confirm-test-only --sku DDN-SRC-CAR-XS --quantity 25
```

Expect `"result": "loaded"`, `"synthetic": true`, `"variants_touched": 1`. Omitting
`--confirm-test-only` is refused; so is running it in preview mode. Note the stock is
**typed** `synthetic_test_stock`, not merely a number.

## 10. Create a test customer

Register through the storefront with an obviously fictional address such as
`tester@dedunet.example`. Do not use a real person's details.

## 11. Run a sandbox decline

Check out with payment token **`pm_decline`**.

Expect: the payment is refused, **no successful order appears**, your bag is **not**
emptied, and the reserved stock is released. A cancelled order is recorded — that is the
audit trail of a real attempt, not a failure to hide.

## 12. Run a sandbox success

Check out again with **`pm_success`**.

Expect a new order. It must **not** replay the declined result — the client sends a
different idempotency intent. Retrying the *same* successful checkout returns the *same*
order rather than creating a second one.

## 13. Inspect the test order in admin

Expect the order listed and labelled `COMMERCE_TEST_MODE` / `is_test_order`. Expect the
DDN-SRC-CAR-XS stock to have dropped by exactly the quantity ordered, and the inventory to
still be classified as synthetic. Perform the approved transition (fulfil) and note the
tracking number.

## 14. Run the notification worker

The worker container is already running on a timer. To see one bounded cycle immediately:

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging exec api python manage.py dispatch-notifications
docker compose -f docker-compose.staging.yml --env-file .env.staging logs --tail 20 notification-worker
```

Expect a console line whose subject begins **`[TEST ORDER] DEDUNET —`**. Nothing is sent to
a real mailbox: `EXTERNAL_SMTP_DELIVERY_PENDING`.

## 15. Confirm the customer sees the updated status

Back in the storefront (and in mobile), open order history. Expect the order to show
**shipped** and to still declare itself a test order. Web and mobile must agree.

## 16. Clean up synthetic inventory

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging exec api \
  python manage.py clear-test-inventory --confirm-test-only
```

Expect the SKU back to **0** and `prototype_unavailable`.

## 17. Return to preview mode

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging stop api
COMMERCE_MODE=BRAND_PREVIEW_MODE docker compose -f docker-compose.staging.yml --env-file .env.staging up -d api
```

Confirm checkout is blocked again. Your test order and its notification remain — truthful
evidence of what was tested is deliberately retained.

## 18. Verify public commerce is still blocked

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging stop api
COMMERCE_MODE=PUBLIC_COMMERCE_MODE docker compose -f docker-compose.staging.yml --env-file .env.staging up -d api
docker compose -f docker-compose.staging.yml --env-file .env.staging logs --tail 20 api
```

Expect, precisely — this was measured, not assumed:

| Observation | Value |
|---|---|
| container | starts, and reports `(healthy)` |
| `/ready` | **200** |
| `GET /api/v1/catalog/products` | **500** |
| API log | `CommerceModeError: PUBLIC_COMMERCE_MODE cannot be enabled by configuration. Public commercial launch is BLOCKED: brand legal clearance is pending and product origin, material and evidence states are UNVERIFIED.` |

Public commerce is **not reachable through configuration**: nothing can be browsed, carted
or bought. That is the control working — enabling it requires a code change and the
documented activation gate.

Two things to note honestly. The refusal surfaces as a `500` rather than a stated refusal,
and `/ready` still answers `200` while every commerce request fails. Neither weakens the
block, and both are recorded as limitation **L10** in the readiness decision. Do not
report them as new findings.

Put the API back:

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging stop api
COMMERCE_MODE=BRAND_PREVIEW_MODE docker compose -f docker-compose.staging.yml --env-file .env.staging up -d api
```

## 19. Shut down safely

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging down
```

**Your database survives.** Only add `-v` if you deliberately want to destroy the staging
data and start from an empty database.

---

## Optional — backup and isolated restore

```bash
python infrastructure/backup/backup_manager.py rehearse
```

Backs up, verifies the SHA-256 **before** restoring, restores into a **new** database,
compares schema, constraints, indexes and row counts, then drops only the rehearsal copy.
It refuses to drop the source. This is a local rehearsal, not production disaster recovery.

---

## What to report

Anything that differs from the expectations above, plus:

* a blank product thumbnail (step 3 or 7);
* any order that is **not** labelled as a test order;
* any purchase that succeeds while in preview mode;
* any real email arriving anywhere;
* the API starting in `PUBLIC_COMMERCE_MODE`.

The last three would be serious. The rest are ordinary findings.
