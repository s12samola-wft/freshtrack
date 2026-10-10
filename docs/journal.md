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

**Lesson**
- Write the plan down before building: an honest architecture doc (Planned vs Built) and a journal
  make every decision traceable, like batch records in food production.
- `.gitignore` is a safety net, not a lock. If a secret is ever committed, rotate it first, then clean history.

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

**Lesson**
- Liveness (`/health`) answers "should Kubernetes restart me?"; readiness (`/ready`) answers
  "can I serve traffic now?". Putting a database check in liveness causes restart loops
  (CrashLoopBackOff) during a database outage, and restarts cannot fix the database.
- To predict which test breaks, ask: which tests call the code I changed?

**Next step**
- Open the pull request for `feat/api-skeleton` (do not merge until CI exists).
- Samson builds the CI pipeline: Check → Build → Prove → Scan → Ship, starting with lint + test.

---

## Entry 3 — 2026-10-10 — CI check stage (lint ∥ test)

**Problem**
There was no CI. PR #1 (api skeleton) was merged after local tests only, so nothing
automatically stopped broken or messy code from reaching `main`.

**Decision**
- Start the pipeline with stage 1 of Check → Build → Prove → Scan → Ship: `lint` and `test` as two parallel jobs.
- Triggers: `pull_request` and `push` to `main` only. Pushing a feature branch alone does not run CI;
  open a (draft) PR for early feedback. This avoids running CI twice for the same commit.
- Least privilege: `permissions: contents: read`, `persist-credentials: false`.
- Fixed runner `ubuntu-24.04`, `timeout-minutes: 5`, `concurrency` with `cancel-in-progress`.
- Actions pinned to full commit SHAs, verified on 2026-10-10 with the GitHub releases API and `git ls-remote`:
  `actions/checkout` v7.0.1 = `3d3c42e5aac5ba805825da76410c181273ba90b1`,
  `actions/setup-python` v7.0.0 = `5fda3b95a4ea91299a34e894583c3862153e4b97`.
- Ruff 0.17.0 (latest on PyPI on 2026-10-10), same version locally and in CI.

**Implementation**
- Branch `ci/check-stage`, file `.github/workflows/ci.yml` (typed by me, with a comment per stage).
- Ruff installed in `api/.venv` to reproduce CI locally.

**Verification**
- First CI run: `test` passed; `lint` failed at `ruff check` (see Troubleshooting).
- Locally after the fix: `ruff check api/` → All checks passed; `ruff format --check api/` → 3 files
  already formatted; `pytest` → 4 passed.
- Second CI run on commit `fea1ee9`: *pending, to be recorded.*

**Troubleshooting**

1. *`git add` did nothing; `git status` showed `../.github/`.*
   - Why: I ran Git from inside `api/`. Git paths are relative to the current folder, so
     `.github/workflows/ci.yml` pointed to a file that does not exist there.
   - Fix: `cd ~/Projects/freshtrack` (or `cd "$(git rev-parse --show-toplevel)"`), then `git add`.

2. *CI lint failed: `I001 Import block is un-sorted or un-formatted` in `api/tests/test_health.py`.*
   - Why: the test file was written without running Ruff first. CI caught what the author missed.
   - Fix: reproduced locally with the same Ruff version, then `ruff check --fix api/`.

3. *Hidden problems: the `ruff format --check` step was skipped.*
   - Why: steps in a job run in order and stop at the first failure. Jobs are independent, so `test` still passed.
   - Running `ruff format --check` locally showed 2 more problems: a line longer than 88 characters
     in the test file, and an extra blank line in `api/app.py` left over from the Entry 2 failure drill.
   - Fix: `ruff format api/`, reviewed with `git diff`, re-ran lint and tests.
   - Possible improvement: `if: ${{ !cancelled() }}` on the format step, so one CI run shows all lint problems.

4. *History note:* commit `209fbb8` ("add") accidentally added a stray `..` line to `ci.yml`, removed
   again in `3fa88a8`. Squash-merging the PR will combine these into one clean commit on `main`.

**Lesson**
- CI is the quality-control gate, not a formality: it caught 3 issues that both the author and I missed.
- Reproduce a CI failure locally with the same tool version before fixing it; fix, review the diff, re-verify, then push.
- A failed step hides the steps after it, so "1 error" in CI can mean more problems underneath.
- Manual fixes after an incident (the drill) can leave small leftovers; automated checks find them.
- Clear commit messages matter: "add" tells a reviewer nothing.

**Next step**
- Record the result of the second CI run, then squash-merge the PR once it is green.
- Decide on `!cancelled()` for the format step.
- Add the Trivy repo scan (secrets, vulnerable dependencies, misconfiguration) to the CHECK stage.
