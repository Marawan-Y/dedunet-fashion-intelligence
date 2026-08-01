# Side B Docker Build and Runtime Evidence

- Artifact ID: SB-EV-BOOT-004
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: `platform/poc/docker-compose.yml`, both Dockerfiles, local Docker Engine, SB-EV-BOOT-001
- Acceptance criteria: Compose configuration renders after local setup; both images build; runtime health is attributed only to this checkout.
- Validation procedure/result: configuration and image build passed; runtime for this checkout failed because host port 8000 was already owned by containers from a different checkout.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-004_docker_checks.md`
- Readiness status: BLOCKED
- Downstream consumer: SB-AR-B2-001; B2 backlog
- Remaining risks/next action: rerun Compose on an isolated host or after the external owner frees ports 8000/3000; then capture this checkout's health, API, storefront, logs, and shutdown.

## Before local `.env`

Working directory: `platform/poc`

```text
COMMAND: docker compose config
WARNING: Error loading config file: open C:\Users\User\.docker\config.json: Access is denied.
WARNING: Error loading config file: open C:\Users\User\.docker\config.json: Access is denied.
env file C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\.env not found: GetFileAttributesEx ... The system cannot find the file specified.
EXIT_CODE: 1
```

```text
COMMAND: docker compose up --build --detach
WARNING: Error loading config file: open C:\Users\User\.docker\config.json: Access is denied.
WARNING: Error loading config file: open C:\Users\User\.docker\config.json: Access is denied.
env file C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\.env not found: GetFileAttributesEx ... The system cannot find the file specified.
EXIT_CODE: 1
```

## After ignored local `.env`

`docker compose config` rendered both `api` and `storefront`, the local development variables, `poc_default`, port mappings 8000/3000, API healthcheck, and bind-mounted sample product data.

```text
COMMAND: docker compose config
EXIT_CODE: 0
WARNINGS: Docker user config access denied in the sandbox; render still completed.
```

Initial sandboxed build:

```text
COMMAND: docker compose build
Image poc-storefront Building
Image poc-api Building
CreateFile C:\Users\User\.docker\buildx\instances: Access is denied.
EXIT_CODE: 1
```

Approved Docker build retry (full material build output):

```text
COMMAND: docker compose build
#1 [internal] load local bake definitions
#1 reading from stdin 1.21kB done
#1 DONE 0.0s
#2 [storefront internal] load build definition from Dockerfile
#2 transferring dockerfile: 89B done
#2 DONE 0.1s
#3 [storefront internal] load metadata for docker.io/library/nginx:1.27-alpine
#4 [api internal] load build definition from Dockerfile
#4 transferring dockerfile: 264B done
#4 DONE 0.2s
#5 [api internal] load metadata for docker.io/library/python:3.12-slim
#3 DONE 0.8s
#5 DONE 0.7s
#6 [api internal] load .dockerignore
#6 transferring context: 2B done
#6 DONE 0.0s
#7 [storefront internal] load .dockerignore
#7 transferring context: 2B done
#7 DONE 0.1s
#8 [api internal] load build context
#8 transferring context: 23.31kB done
#8 DONE 0.2s
#9 [storefront internal] load build context
#9 transferring context: 117B done
#9 DONE 0.1s
#10 [api 1/6] FROM docker.io/library/python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
#10 DONE 0.2s
#11 [api 2/6] WORKDIR /app
#11 CACHED
#12 [api 3/6] COPY requirements.txt .
#12 CACHED
#13 [api 4/6] RUN pip install --no-cache-dir -r requirements.txt
#13 CACHED
#14 [storefront 1/2] FROM docker.io/library/nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
#14 DONE 0.2s
#15 [api 5/6] COPY app ./app
#15 DONE 0.1s
#16 [storefront 2/2] COPY . /usr/share/nginx/html
#16 CACHED
#17 [storefront] exporting to image
#17 exporting manifest sha256:75b499547a6aef5a1fa635d6b8077cb62caf32e8c636a09866260cff1cdbb581 done
#17 naming to docker.io/library/poc-storefront:latest done
#17 DONE 0.9s
#18 [api 6/6] COPY data ./data
#18 DONE 0.4s
#19 [api] exporting to image
#19 exporting manifest sha256:a6c80bf877c4ebceb9485e18f725eae6e533bff63a3e5c84f50fe118f45d236e done
#19 naming to docker.io/library/poc-api:latest done
#19 DONE 1.5s
#20 [storefront] resolving provenance for metadata file
#20 DONE 0.1s
#21 [api] resolving provenance for metadata file
#21 DONE 0.0s
Image poc-storefront Built
Image poc-api Built
EXIT_CODE: 0
```

## Compose runtime attempt

```text
COMMAND: docker compose up --build --detach
Images rebuilt from cache successfully.
Network poc_default Created
Container poc-api-1 Created
Container poc-storefront-1 Created
Container poc-api-1 Starting
Error response from daemon: failed to set up container networking: driver failed programming external connectivity on endpoint poc-api-1 (...): Bind for 0.0.0.0:8000 failed: port is already allocated
EXIT_CODE: 1
```

Read-only Docker inspection found the port owner:

```text
COMMAND: docker ps --all --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"
EXIT_CODE: 0
f01e841e47da fashion-commerce-platform-poc-api-1 Up (healthy) 0.0.0.0:8000->8000/tcp
f8951802a1ea fashion-commerce-platform-poc-storefront-1 Up 0.0.0.0:3000->80/tcp
a88d097484e6 poc-api-1 Created
37dfb0e5bec4 poc-storefront-1 Created
```

```text
COMMAND: docker inspect --format "{{json .Config.Labels}}" fashion-commerce-platform-poc-api-1 fashion-commerce-platform-poc-storefront-1
EXIT_CODE: 0
OBSERVED LABEL: com.docker.compose.project.working_dir=C:\Users\User\Desktop\Platform\Fashion_Commerce_Two_Agent_Execution_Pack\fashion-commerce-platform-poc
OBSERVED LABEL: com.docker.compose.project.config_files=C:\Users\User\Desktop\Platform\Fashion_Commerce_Two_Agent_Execution_Pack\fashion-commerce-platform-poc\docker-compose.yml
```

Requests to ports 8000/3000 returned health 200, three products, and the expected page title, but they are explicitly excluded as runtime proof for this repository because Docker labels attribute them to the other checkout. No external containers were stopped or modified.

## Cleanup of this checkout's failed attempt

```text
COMMAND: docker compose down
Container poc-storefront-1 Stopping
Container poc-storefront-1 Stopped
Container poc-storefront-1 Removing
Container poc-storefront-1 Removed
Container poc-api-1 Stopping
Container poc-api-1 Stopped
Container poc-api-1 Removing
Container poc-api-1 Removed
Network poc_default Removing
Network poc_default Removed
EXIT_CODE: 0
```

Only resources under Compose project `poc` created by this checkout were removed. The separate running checkout was not changed.
