
### Services

| Service | Image | What it does | Networks | Published port |
|---|---|---|---|---|
| `frontend` | nginx-unprivileged (built from `frontend/`) | Serves the web page and forwards `/api/` requests to the API | `frontend` | `3000` → `8080` |
| `api` | python:3.11-slim (built from `api/`) | FastAPI app: creates links, redirects, counts clicks | `frontend`, `backend` | none |
| `db` | postgres:16-alpine | Stores the links permanently (volume `pgdata`) | `backend` | none |
| `cache` | redis:7-alpine | Temporary data, such as rate-limit counters | `backend` | none |

### Diagram

```text
Browser
   |  http://localhost:3000
   v
+----------+   network: frontend   +-------+   network: backend   +----+
| frontend | --------------------> |  api  | -------------------> | db |  (volume: pgdata)
| (nginx)  |   /api/* -> api:8000  |       |                      +----+
+----------+                       |       |                      +-------+
                                   |       | -------------------> | cache |
                                   +-------+                      +-------+
```

### Network paths

- Browser → `frontend`: the only path from outside, through port `3000`.
- `frontend` → `api`: over the `frontend` network, using the name `api`.
- `api` → `db` and `api` → `cache`: over the `backend` network, using the names `db` and `cache`.
- `frontend` cannot reach `db` or `cache`, because they share no network.

### What every service does

Let me explain it with realistic usecase:

1. **The manager opens the restaurant.** You type `docker compose up`. Docker Compose reads your file and builds every box (container) that the restaurant needs.
2. **The pantry and the notepad open first.** Postgres (the pantry) and Redis (the notepad) start before anyone else. Compose waits until both say "I'm ready" (the healthcheck) before moving on.
3. **The chef starts next.** The API (the chef) only starts after the pantry and the notepad are ready, because he needs them to cook. When he's ready too, he says "healthy".
4. **The waiter opens the door last.** nginx (the waiter) starts only after the chef is ready, so he never promises food that can't be made.
5. **The customer arrives.** The customer opens `localhost:3000` in the browser. He only knows one door: the waiter's door.
6. **The waiter shows the menu.** The page (HTML, CSS, JS) is the menu. The waiter already has it on his shelf, ready to hand over. This is the bread that was baked earlier in the workshop.
7. **The customer places an order.** When he clicks a button, the page sends a request to `/api/...` on the same door. The browser sees one address only, so there is no CORS problem.
8. **The waiter runs to the kitchen.** nginx sees the order starts with `/api/`, so he doesn't answer it himself. He calls "api!" and Docker finds the chef by his name tag, which is the service name.
9. **The chef cooks.** The API reads or saves the links in the pantry (Postgres, kept forever in the `pgdata` volume). It also uses the notepad (Redis) for quick things, like counting requests per minute.
10. **The answer goes back.** The chef gives the result to the waiter, and the waiter gives it to the customer. The customer never sees the kitchen.
11. **Secrets stay in a locked drawer.** Passwords live in the `.env` file, which is not in git and not in the images. The compose file only has references like `${DB_PASSWORD}`.
12. **Everyone wears a safe uniform.** The chef and the waiter both run as non-boss users (non-root). If a thief got in, he couldn't do much damage.
13. **Only one door faces the street.** Only the frontend has a published port. The chef, the pantry, and the notepad can only be reached from inside the restaurant.

---

## Quick start

### Prerequisites

- Docker Engine 24+ and Docker Compose v2 (`docker compose version` should work)
- Git
- Port `3000` free on your machine

### 1. Clone the repository

```bash
git clone https://github.com/Joe-Khaled/docker-cohort-1.git
cd docker-cohort-1/final-project/submission
```

### 2. Create the `.env` file

```bash
cp .env.example .env
```

The defaults work as they are for a local run. For anything beyond local testing, open `.env` and change `DB_PASSWORD`.

### 3. Build and start everything

```bash
docker compose up --build -d
```

The first build takes a few minutes. Compose starts the services in this order: `db` and `cache`, then `api`, then `frontend`.

### 4. Check that everything is healthy

```bash
docker compose ps
```

db, cache and api should show healthy. frontend shows Up (it has no healthcheck, see Health checks). The API can take about 10-20 seconds to get healthy.

### 5. Open the app

Go to **http://localhost:3000** in your browser.

The status bar at the top of the page should show the backend, Postgres, and Redis as ready. Paste a URL, click shorten, and click the short link to test the redirect.

### Useful commands

```bash
docker compose logs -f api     # follow the API logs
docker compose down            # stop and remove containers (data is kept)
docker compose down -v         # stop and also delete the database data
```

---

## Configuration

All settings live in one `.env` file at the project root, next to `compose.yml`. Create it with `cp .env.example .env`. The real `.env` is in `.gitignore` and never committed.

Compose uses the file in two ways:

- **`env_file`:** every variable is passed into the `api` container.
- **`${...}` substitution:** Compose reads the values while parsing `compose.yml`, for example to set up Postgres and the port mapping.

| Variable | Default | Read by | Secret? | Purpose |
|---|---|---|---|---|
| `APP_ENV` | `production` | api | No | Runtime mode, shown in the startup log |
| `LOG_LEVEL` | `INFO` | api | No | How detailed the logs are |
| `DB_NAME` | `snip` | api, db | No | Database name. Compose passes it to Postgres as `POSTGRES_DB` |
| `DB_USER` | `postgres` | api, db | No | Database user. Passed to Postgres as `POSTGRES_USER` |
| `DB_PASSWORD` | `change-me` | api, db | **Yes** | Database password. Passed to Postgres as `POSTGRES_PASSWORD` |
| `DB_PORT` | `5432` | api | No | Port the API uses to reach Postgres |
| `REDIS_PORT` | `6379` | api | No | Port the API uses to reach Redis |
| `REDIS_PASSWORD` | empty | api | **Yes**, if set | Redis password. Empty means no password |
| `RATE_LIMIT_PER_MINUTE` | `10` | api | No | Max requests per minute per client |
| `FRONTEND_PORT` | `3000` | Compose only | No | Port on your machine mapped to nginx |

### Set by `compose.yml` (do not put in `.env`)

| Variable | Value | Why |
|---|---|---|
| `DB_HOST` | `db` | Service name of Postgres on the Docker network |
| `REDIS_HOST` | `cache` | Service name of Redis on the Docker network |

> Inside Docker, `localhost` means the container itself, so the API must use the service names to reach the other containers.

### About secrets

- `DB_PASSWORD` is the main secret. Change it from the default before any real deployment.
- `.env` is excluded from git (`.gitignore`) and from the API image (`api/.dockerignore`), so passwords are never committed or baked into an image.
- `compose.yml` contains only references like `${DB_PASSWORD}`, never real values.
- The frontend has no runtime variables. The browser calls `/api` on the same address, so nothing needs to be configured there.
- A `.env` file is fine for local use. In production, use your platform's secret store (Docker secrets, Kubernetes Secrets, or a cloud secret manager).

---

## Engineering decisions

### 1. Multi-stage builds

**Decision:** Both images use two stages. The frontend builds with `node:20-alpine` and serves with `nginxinc/nginx-unprivileged`. The API installs its dependencies in a builder stage and copies only the installed packages into the final image.

**Why:** After `npm run build`, the frontend is only static files, so Node, `node_modules`, and the source code are not needed at runtime. Leaving them behind makes the image much smaller and gives an attacker fewer tools to work with. The dependency files are copied before the source code, so changing code does not reinstall every package, which keeps rebuilds fast.

### 2. Network separation and a single published port

**Decision:** There are two networks. `db` and `cache` are only on `backend`. `frontend` is only on the `frontend` network. The `api` joins both. Only the frontend publishes a port (`3000:8080`).

**Why:** The goal is least exposure. The browser can only reach nginx, never Postgres, Redis, or the API directly. nginx cannot reach the database either, so an attacker who breaks into the web layer still has to go through the API to get to the data.

### 3. Postgres has a named volume, Redis does not

**Decision:** The `pgdata` volume is mounted at `/var/lib/postgresql/data` for Postgres. Redis has no volume.

**Why:** The short links are permanent data and must survive restarts and container recreation. Redis only holds temporary data, such as rate-limit counters, so losing it on restart is harmless and keeps Redis simple.

---

## Health checks

Docker runs a command inside each container at a fixed interval. A service is `healthy` only after the command passes. `depends_on` with `condition: service_healthy` uses this to control startup order: `db` and `cache`, then `api`, then `frontend`.

| Service | Check | Why it's the right check |
|---|---|---|
| `db` | `pg_isready -U $DB_USER -d $DB_NAME` | A running Postgres process is not the same as a database that accepts connections. `pg_isready` waits for the real "accepting connections" state, and it ships with the image. |
| `cache` | `redis-cli ping` | A `PONG` reply proves Redis is alive and answering commands, not just that the port is open. |
| `api` | Python `urllib` request to `http://127.0.0.1:8000/api/ready` | It goes through the app itself, so it fails if the server hangs. `/api/ready` also reports Postgres and Redis, so the API is healthy only when it can really do its job. Python is used because the slim image has no `curl`. |

### Why `frontend` has no healthcheck

Nothing depends on the frontend, because it is the last service in the chain. nginx serving static files either runs or dies, and `restart: unless-stopped` already restarts it if it dies. A healthcheck there would only add information, not behavior.

### Timing

- `db` and `cache` are checked every 5s with 10 retries, because everything waits for them.
- `api` is checked every 10s with 5 retries and a `start_period` of 10s, so its first connection attempts to the database are not counted as failures.

A service is marked `unhealthy` only after all retries fail in a row.

---

## Persistence test

**Goal:** show that saved links survive when the containers are removed and recreated, because Postgres stores its data in the named volume `pgdata`.

### Steps I ran

1. Started the stack:

   ```bash
   docker compose up
   ```

2. Opened `http://localhost:3000`, shortened a URL, and saw the new link in the links list.
3. Stopped and removed the containers (without `-v`):

   ```bash
   docker compose down
   ```

4. Started the stack again:

   ```bash
   docker compose up
   ```

5. Opened `http://localhost:3000` again.

### What I observed

The link I created before `docker compose down` was still in the links list after the restart.

### Why it works

`docker compose down` removes the containers and networks, but it keeps named volumes. The `db` container is recreated from scratch, but `pgdata` is mounted again at `/var/lib/postgresql/data`, so Postgres finds its old data and continues from it.

Screenshots: see Evidence → Persistence.
---

## Operations / troubleshooting

### How I investigate a failing service

Always in this order, from the big picture to the details:

1. **See the state of all services**

   ```bash
   docker compose ps -a
   ```

   Look for `unhealthy`, `Exit`, or `Restarting`. This tells me which service is the problem.

2. **Read its logs**

   ```bash
   docker compose logs --tail=50 <service>
   ```

   The error message is usually here. Use `-f` to follow live.

3. **Check the healthcheck result**

   ```bash
   docker inspect --format '{{json .State.Health}}' $(docker compose ps -q <service>)
   ```

   This shows the exact command that failed and its output.

4. **Go inside the container**

   ```bash
   docker compose exec <service> sh
   ```

   Test things by hand, for example call the API from inside, or check the files.

5. **Check the final config**

   ```bash
   docker compose config
   ```

   Shows the merged file after `.env` substitution, so wrong values or indentation show up.

> Because services wait for each other, I start from the **bottom of the chain**: if `frontend` does not start, I check `api`; if `api` is not healthy, I check `db` and `cache`. The root cause is usually the first unhealthy service.

### Problem 1: Postgres crashed in a loop

**Symptoms:** `docker compose up` failed with `dependency failed to start: container submission-db-1 is unhealthy`. The api and frontend never started.

**Evidence:** The `db` logs repeated the same error many times:

```text
initdb: error: directory "/var/lib/postgresql/data" exists but is not empty
```

The loop happened because of `restart: unless-stopped`, which kept restarting the crashing container.

**Root cause:** The `pgdata` volume still had old files from an earlier run, when it was mounted at the wrong path (`/var/lib/postgresql`). Postgres did not recognize them as a valid database, and refused to initialize on top of them.

**Fix:** Removed the old volume and recreated it, and kept the mount at the correct path:

```bash
docker compose down -v
docker compose up --build
```

```yaml
volumes:
  - pgdata:/var/lib/postgresql/data
```

**Verification:** `docker compose ps` showed `db` as `healthy`, and the api and frontend started after it. I then ran the persistence test (create a link, `down`, `up`, link still there).

---

## Evidence

### `docker compose up --build` completing

![compose up --build](evidence/01-compose-up-build.png)

### `docker compose ps`: all services running, only nginx published

![compose ps](evidence/02-compose-ps.png)

### `docker compose logs`

api-1       | INFO:     127.0.0.1:42144 - "GET /api/ready HTTP/1.1" 200 OK
[04/Oct/2026:17:23:35 +0000] "GET /api/ready HTTP/1.1" 200 58 "http://localhost:3000/"
cache-1     | 1:M 04 Oct 2026 17:21:06.584 * Ready to accept connections tcp
db-1     | 2026-10-04 17:33:23.703 UTC [1] LOG:  database system is ready to accept connections


### App working in the browser

![Link created](evidence/03-link-created.png)
![Click count increased](evidence/04-click-count.png)

### Persistence: before and after `down` → `up`

![Before down](evidence/05-before-down.png)
![After up](evidence/06-after-up.png)

### `docker compose down`

![compose down](evidence/07-compose-down.png)