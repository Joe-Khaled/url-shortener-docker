# Final Project — Ship This Application 🐳🚀

| | |
|---|---|
| **Announced** | Sunday, September 27, 2026 (Session 4) |
| **Build week** | September 27 → October 4, 2026 |
| **Submission deadline** | Sunday, October 4, 2026 — before Demo Day starts |
| **Demo Day** | Sunday, October 4, 2026 |
| **Grading** | 100 points — **70 to complete the cohort** |

## Mission

You get a repository with little useful Docker setup. **You ship it.**

A reviewer will clone your fork, supply the configuration you
documented, and start everything with **one command**:

```bash
docker compose up --build
```

If that doesn't produce a working application, nothing else in the
submission matters much. Everything in this brief is about making that
one command work reliably, securely, and in a way you can explain.

## The application

[`starter/`](./starter) contains **Snip**, a small URL shortener. Read
[`starter/README.md`](./starter/README.md) first — it documents every
endpoint, every environment variable, and how the team runs it today
without Docker. Then read
[`starter/dev-notes.txt`](./starter/dev-notes.txt) — the handover notes
the previous developer left. They're honest, and every line is relevant.

Target architecture:

```
Browser
   │
   ▼
 Nginx          ← the only thing reachable from the host
   │  serves the built frontend
   │  proxies /api/* to the API
   ▼
  API           (FastAPI)
   ├── PostgreSQL   links + click counts — must persist
   └── Redis        rate limiting + stats cache
```

What you get:

- `api/` — working FastAPI code, `requirements.txt`, `.env.example`,
  and a **naive `Dockerfile`**. It exists, but it is not good. Treat it
  as something to review and replace, not something to keep.
- `frontend/` — a Vite project. `npm run build` turns it into static
  files in `dist/`. No Dockerfile.
- No Compose file, no Nginx config, no `.dockerignore`, no docs on how
  to run it in containers.

You may change application code if you need to, but you shouldn't need
to — the app already reads all its configuration from the environment.
If you do change it, say what and why in your README.

## How to submit

1. **Fork this repository** to your own GitHub account.
2. Copy the starter into the submission folder and work **only** in
   `final-project/submission/`. Leave `starter/` untouched.

   ```bash
   cd final-project
   cp -r starter/. submission/     # the "/." also copies dotfiles like .gitignore
   ```

3. Build, commit, and push to your fork as you go — a history of small
   commits is part of the story you tell on Demo Day.
4. Submit the link to your fork through the **DevOpsWithDavid**
   platform before the deadline.

Do not open a PR against this repo — submissions are per-student forks,
submitted via the platform.

---

## Requirements

### Images

- [ ] Dockerize every appropriate service. (Which ones need a custom
      image, and which can use an official image as-is? Decide and
      explain.)
- [ ] Sensible layering and build context — dependency installs are
      cached separately from source code changes.
- [ ] Multi-stage builds **where they materially help**. (Hint: which
      part of this app needs a toolchain to build that it doesn't need
      to run?)
- [ ] A `.dockerignore` for every build context.
- [ ] Small runtime images — no build tooling, caches, or source
      artifacts left behind where they aren't needed.

### Stack

- [ ] The whole multi-service stack defined in a Compose file
      (`compose.yaml`).
- [ ] Correct service discovery and networking — services talk to each
      other by name, and **only Nginx is published to the host**.
- [ ] PostgreSQL data in a **named volume**.
- [ ] **Meaningful** health checks where appropriate — you should be
      able to say what each one proves, and why it depends (or doesn't
      depend) on other services.
- [ ] Explicit, explainable base images — pinned tags, no `latest`, and
      you can say why you chose each one.

### Discipline

- [ ] Non-root runtime user where practical.
- [ ] Runtime configuration separated from images — the same image
      must be able to run with different config.
- [ ] **No real secrets committed.** Commit a `.env.example` with
      placeholders; the real `.env` stays out of git.
- [ ] A strong `README.md` with an architecture explanation.
- [ ] Evidence of `up`, `ps`, `logs`, and `down` working.

### Production thinking — explain at least three engineering decisions

In your README, explain **at least three** of the following, with your
actual reasoning (not a generic definition):

- Why a service is, or is not, exposed to the host
- Why data lives in a volume
- How configuration and secrets are supplied
- Why the runtime image and user were chosen
- How you would investigate a failing service

And demonstrate:

- The application works **end to end** — through the browser, via
  Nginx, into the API, down to PostgreSQL and Redis.
- Persistent data **survives container recreation**.

---

## Deliverables

Your `final-project/submission/` folder must contain:

| # | Deliverable | Notes |
|---|---|---|
| 1 | **`compose.yaml`** | Starts the whole stack with `docker compose up --build` |
| 2 | **Dockerfiles** | One per service that needs a custom image |
| 3 | **`.dockerignore`** | One per build context |
| 4 | **Nginx configuration** | Serves the frontend, proxies `/api/` |
| 5 | **`.env.example`** | Every variable a reviewer needs to set, placeholder values only |
| 6 | **Application code** | Copied from `starter/`, plus any changes you explain |
| 7 | **`README.md`** | See [README requirements](#readme-requirements) |
| 8 | **`evidence/`** | Screenshots or terminal output — see [Evidence](#evidence) |

A layout like this is a reasonable starting point — adapt it if you
have a reason to, and explain the reason:

```
submission/
├── README.md
├── compose.yaml
├── .env.example
├── .gitignore
├── api/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── ...
├── frontend/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── ...
├── nginx/
│   └── ...
└── evidence/
    └── ...
```

### README requirements

Your `submission/README.md` must cover:

1. **Architecture** — every service, what it does, how they connect,
   and which network paths exist. A diagram (ASCII is fine) helps.
2. **Quick start** — the exact commands a reviewer runs, from `git
   clone` to a working app in the browser, including how to create the
   `.env` from `.env.example`.
3. **Configuration** — every variable, which service reads it, and
   which ones are secrets.
4. **Engineering decisions** — at least three from the list above,
   with your reasoning.
5. **Health checks** — what each one checks, and why that's the right
   thing to check.
6. **Persistence test** — the steps you ran and what you observed.
7. **Operations / troubleshooting** — how you would investigate a
   failing service in this stack, plus **at least one real problem you
   hit during the build week** and how you debugged it (symptoms →
   evidence → root cause → fix → verification).

### Evidence

Put screenshots or pasted terminal output in `evidence/` (and link them
from your README) showing:

- [ ] `docker compose up --build` completing, all services starting
- [ ] `docker compose ps` with every service running and health checks
      reporting **healthy**
- [ ] `docker compose logs` (or per-service logs) from a working stack
- [ ] The app working in the browser at the Nginx address — create a
      link, follow it, see the click count go up
- [ ] **Persistence:** links still present after
      `docker compose down` → `docker compose up`
- [ ] Only Nginx published to the host (e.g. the `PORTS` column of
      `docker compose ps`)
- [ ] `docker compose down` shutting everything down cleanly

## Expected outcome — how your submission will be tested

The reviewer will do roughly this, on a clean machine, with nothing but
Docker installed:

```bash
git clone <your-fork>
cd <your-fork>/final-project/submission
cp .env.example .env            # then fill values as your README says
docker compose up --build
```

Then they will check that:

1. Every service starts, and `docker compose ps` shows them healthy.
2. The app loads in the browser at the address your README gives, and
   the status bar at the top shows `backend ready · postgres ok · redis ok`.
3. Creating a short link and following it works, and the click count
   increases.
4. PostgreSQL and Redis are **not** reachable from the host.
5. After `docker compose down` and `docker compose up`, the links are
   still there.
6. Nothing sensitive is in the images or in git history:
   `docker history`, `docker inspect`, and a look at your commits.
7. Your README answers their questions before they have to ask.

If a step requires knowledge that isn't in your README, that's a
documentation bug.

---

## Evaluation — 100 points

| Area | Weight | What we look at |
|---|---|---|
| Functionality | **25** | One-command startup; the app works end to end; data persists across recreation |
| Dockerfile quality | **20** | Base image choice, layer ordering and caching, multi-stage where it helps, `.dockerignore`, image size, exec-form commands |
| Networking & Compose | **15** | Service discovery by name, only Nginx published, named volume, health checks, sensible `depends_on` |
| Security | **15** | Non-root, no secrets in images or git, config outside images, minimal exposure, no unnecessary privileges or mounts |
| Reliability / production thinking | **10** | Meaningful health checks, restart behavior, graceful shutdown, resource awareness, behaviour when a dependency fails |
| Documentation | **10** | Architecture, reproducible quick start, configuration reference, evidence |
| Explanation & reasoning | **5** | Engineering decisions are explained and defensible |

**Completion threshold: 70 / 100.** This demonstrates practical
competence — not attendance.

## Demo Day — Sunday, October 4

Be ready to:

- Show the application running
- Explain the architecture
- Walk through the important Docker and Compose decisions
- Demonstrate persistence and networking
- Describe one problem you hit and how you debugged it
- Answer implementation questions about any file you submitted

## Optional stretch goals

Not required for the 100 points, but good material for Demo Day:

- Resource limits on services, and what happens when one is exceeded
- Supplying secrets as files (`*_FILE` variables + Compose `secrets:`)
  instead of plain environment variables
- Scanning your images (e.g. `docker scout`, Trivy) and acting on what
  you find
- Showing what the app does when Redis is stopped, and explaining why
  that's the right behaviour

## Ground rules

**Use AI to learn and debug. Understand every artifact you submit, and
defend it.** On Demo Day you may be asked why any line in any file is
there, and what would happen if it were removed.

There is no reference implementation during build week. Bring me
**evidence and questions** — what you ran, what you saw, what you
expected — and I will help you narrow it down.
