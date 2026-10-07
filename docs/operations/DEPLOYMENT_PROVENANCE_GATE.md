# Deployment provenance gate

**Run this before asking a human to test anything. Every time.**

| | |
|---|---|
| Artifact ID | `OPS-GATE-001` · **Version** 1.0 |
| Owner | Side B / platform |
| Status | `SELF-VALIDATED` — executed by hand; not yet automated |
| Origin | `R-019`, `evidence/phase-5/SAVED_ACCEPTANCE_DEPLOYMENT_INCIDENT.md` |

## Why this exists

On 2026-10-07 a physical iPhone acceptance failed on a six-week-old artifact while the code,
the database, the API and CI were all correct. Port `13080` was reaching a leftover cutover
rehearsal container; the real staging web container had served **no request at all** since it
started.

**Code provenance and deployment provenance are separate facts.** This repository was
measuring only the first. A green pipeline tells you what the commit contains. It tells you
nothing about which bytes a URL returns.

The cost of skipping this gate is not a failed check — it is a person's time on a device, and
a failure report that looks like a product defect and is not one.

## What the gate must establish

An unbroken chain, each link proved by observable artifact evidence:

```
host URL  →  intended container  →  intended image  →  intended source revision
```

### Not acceptable as evidence

- **"`docker ps` looks right."** It did, throughout the incident. The port column named the
  correct container while a different one answered.
- **"CI is green."** It was — on the exact commit. CI describes the commit, not the deployment.
- **A `localhost` probe.** `localhost` resolved to `::1` and reached a different relay than the
  LAN address the phone uses. Query the container's own IP inside the Docker network, and
  separately query the exact URL the human will type.

## The five checks

Run against the real acceptance URL — the LAN address the human will use, not `localhost`.

### 1. Exclusive port ownership

```bash
docker ps -a --filter "publish=13080" --format '{{.Names}}  {{.Image}}  {{.Status}}'
```

Exactly one container, and it must be the intended one. A stopped container that still holds
a binding counts: it is what a restart can hand the port back to.

### 2. Access-log probe — the decisive one

```bash
MARK="probe-$RANDOM"; curl -s -o /dev/null "http://10.0.0.2:13080/$MARK"
docker logs --tail 20 dedunet-staging-web-1 | grep "$MARK"
```

If the probe does not appear, the URL is not reaching that container, whatever everything else
says. This is the only check that proves the direction of traffic rather than inferring it.

A container whose access log shows **no requests at all** is not serving anybody — treat that
as a failure of this gate, not as a quiet period.

### 3. Artifact identity — host response vs container file

```bash
curl -s -D - -o /dev/null http://10.0.0.2:13080/ | grep -i etag
docker exec dedunet-staging-web-1 sh -c 'grep -oE "assets/index-[A-Za-z0-9_-]+\.js" /usr/share/nginx/html/index.html'
```

The `ETag` from the host must match the serving container's own file, and the entry chunk name
in the served HTML must match the one on disk. Two builds can have identical byte lengths —
during the incident both `index.html` files were exactly 1967 bytes — so compare hashes and
chunk names, never sizes.

### 4. Image and source identity

```bash
docker inspect <container> --format '{{.Image}}'
docker image inspect <image> --format '{{.Created}}  {{json .Config.Labels}}'
```

The image creation time must be **at or after** the commit being accepted. During the incident
the staging image was built 26 minutes *before* the commit it was assumed to contain — which
is survivable only when the content is provably identical, and is never survivable as an
assumption.

Prefer an explicit label (`dedunet.head=<sha>`) over inference. Note the trap it carries: the
stale candidate's `dedunet.head=e29e019` named a commit that **no longer exists**, because a
history rewrite replaced it. A label proves what the builder believed, not that the commit is
still reachable — check it with `git cat-file -e <sha>`.

### 5. The stale artifact is actually gone

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://10.0.0.2:13080/assets/<old-entry-chunk>.js
```

Expect **404**. Positive evidence that the new build is served is not evidence that the old one
cannot be.

## Browser cache — check it last, and usually leave it alone

Only after server provenance is settled. During the incident the cache was **not** involved:
`index.html` is served `no-store, must-revalidate`, asset chunks are content-hashed and
`immutable`, and the stale entry chunk 404s.

**Do not ask a human to clear all Safari website data as a first move.** It destroys their
sign-in state — which is half of what a Saved acceptance is testing — to fix something that is
usually not the cause. A private tab or a cache-busting query answers the question without
costing anything.

## Residue hygiene

The incident needed two things to happen: a crossed port map, and something stale for it to
land on. Only the second is controllable.

**Stop and remove rehearsal and candidate containers once their rehearsal ends.** Keep their
**images** — those are rollback material and cost only disk. A container is a thing that can
be handed a port by a restart; an image is not.

## Status of this gate

Executed by hand. **No automated check asserts deployment provenance yet**, which is the open
part of `R-019`. Until there is one, the checks above are the gate, and "we looked and it
seemed fine" is not a substitute for running them.
