# FreshTrack — Engineering Journal

Each entry: Problem → Decision → Implementation → Verification → Troubleshooting → Lesson → Next step.

---

## Entry 1 — 2026-10-09 — Project kick-off

**Problem**
Households throw food away because they forget what is in the fridge, freezer or
cupboard, buy the same item twice, or find food after its label date has passed.
I need a portfolio project that solves a real problem for a real user (my household)
and lets me practise DevOps, Kubernetes and SRE end to end.

**Decision**
- Build FreshTrack v1 with a small scope: add items, a sorted active list,
  mark used/discarded, and one morning email listing items due within 3 days or past.
- Four parts: web (Flask templates), api (Flask), expiry-checker (CronJob), PostgreSQL.
  Mailpit for dev and test email.
- No user accounts in v1. TLS + basic auth at the edge before any public exposure.
- Minikube is the main lab. AWS k3s only for the ~1 week trial, then destroy.

**Implementation**
- Created the project folder with `CLAUDE.md` (working rules and scope).
- Initialised a Git repository on branch `main`.
- Created `docs/architecture.md` (every component marked Planned) and this journal.

**Verification**
- `git status` shows branch `main`, no commits yet, files untracked.

**Troubleshooting**
- Tool check: Git 2.43, Python 3.12.3 and gh 2.45 are present. `docker --version`
  returned nothing, and minikube, kubectl and helm are not installed. To fix in a later step.

**Lesson** *(Samson: write this in your own words)*
-

**Next step**
- Review `docs/architecture.md` and settle the open decisions.
- Add `.gitignore`, make the first commit, and create the GitHub repo.

---

## Entry 2 — 2026-10-10 — api skeleton with /health and /ready

**Problem**
The DevOps work (Dockerfile, CI, Kubernetes probes) needs a real application to package.
Every app must expose `/health` (liveness) and `/ready` (readiness, checks the database).

**Decision**
- Start the api with only `/health` and `/ready`, with no food items yet.
- `/health` never checks the database; `/ready` does (2-second connection timeout, `SELECT 1`).
- On failure, `/ready` logs the reason but returns only `{"status": "not ready"}` (no internal details).
- Database address comes only from the `DATABASE_URL` environment variable.
- Versions checked on PyPI (2026-10-10): Flask 3.1.3, psycopg 3.3.6, gunicorn 26.2.0, pytest 9.1.1.

**Implementation**
- Branch `feat/api-skeleton`.
- `api/app.py`, `api/tests/test_health.py` (4 tests), `api/tests/conftest.py`,
  `api/requirements.in` (runtime), `api/requirements-dev.in` (adds pytest).
- Local virtual environment `api/.venv` (git-ignored).

**Verification**
- `.venv/bin/pytest -v`: 4 passed in 0.26s.
- `git status` confirmed `.venv/`, `__pycache__/` and `.pytest_cache/` are ignored.

**Troubleshooting — failure drill (Predict → Break → Observe → Fix → Verify)**
- Predict: if `/health` checks the database, Kubernetes restarts the Pods during a database outage.
  I first predicted that test 3 would fail; the correct answer was test 1, because it is the only test that calls `/health`.
- Break: changed `/health` to call `database_is_reachable(...)`.
- Observe: `test_health_is_always_ok` FAILED, the other 3 passed.
- Fix: restored the original `/health` and its explanatory comments.
- Verify: 4 passed.
- Side note: `gh` CLI login is invalid (HTTP 401). Pushing works over SSH. Re-login is needed before using `gh pr create`.

**Lesson** *(Samson: write this in your own words)*
-

**Next step**
- Open the pull request for `feat/api-skeleton` (do not merge until CI exists).
- Samson builds the CI pipeline: Check → Build → Prove → Scan → Ship, starting with lint + test.
