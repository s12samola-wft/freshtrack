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
- PR #2 was merged on 2026-10-10, but the workflow file was invalid, so lint and test never ran
  (see Troubleshooting 6).
- After the fix in PR #3, CI was green on the PR (run `38034944465`) and on `main` after the merge
  (run `38035053448`, commit `6f6db79`).

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

5. *SonarCloud quality gate failed: security hotspot on `pip install` without `--only-binary`.*
   - Why: a source package (sdist) runs its own build scripts during install, so it can execute code on the runner.
   - Fix: `pip install --only-binary :all:` (ready-made wheels only), fixed in code rather than marked "Safe".

6. *An invalid workflow was merged to `main`, and lint and test never ran.*
   - Why: a step was missing its `- ` before `run:`, and YAML read the `: ` inside `:all: ruff` as a key/value pair.
     GitHub could not read the file, so each push only showed a failed run named after the file path
     (`.github/workflows/ci.yml`) instead of `CI`, and no job started.
   - Fix (PR #3): split the pip step into its own `- run:` and quoted the commands.

7. *SonarCloud quality gate failed: security hotspot on installing from unlocked requirements.*
   - Why: without exact versions and hashes, every install can pick up a different (or tampered) package.
   - Fix: `pip-compile` 7.6.1 with `--generate-hashes --strip-extras` creates `requirements*.txt` from the
     `.in` files; CI installs with `--require-hashes`.
   - Note: SonarCloud runs through Automatic Analysis (its GitHub app), not as a step in `ci.yml`.

**Lesson**
- CI is the quality-control gate, not a formality: it caught 3 issues that both the author and I missed.
- Reproduce a CI failure locally with the same tool version before fixing it; fix, review the diff, re-verify, then push.
- A failed step hides the steps after it, so "1 error" in CI can mean more problems underneath.
- Manual fixes after an incident (the drill) can leave small leftovers; automated checks find them.
- Clear commit messages matter: "add" tells a reviewer nothing.
- No green is not the same as passed: before merging, I check that the jobs actually ran.

**Next step**
- Record the result of the second CI run, then squash-merge the PR once it is green.
- Decide on `!cancelled()` for the format step.
- Add the Trivy repo scan (secrets, vulnerable dependencies, misconfiguration) to the CHECK stage.

---

## Entry 4 — 2026-10-16 — Simpler CI: one job with security scans before the build

**Problem**
- The CI only checked style and tests. Nothing looked for risky code, vulnerable packages
  or committed secrets, and no Docker image exists yet to scan.
- A first proposal (three jobs, check → test → scan, linked with `needs:`) was too hard to explain:
  each job runs on a clean runner, so every job repeated the same setup (download code, install
  Python, install packages), and the real checks were hidden among the copies.

**Decision**
- One job, `checks`, with named steps that run top to bottom: CHECK (Ruff) → TEST (pytest) →
  SCAN (bandit, then Trivy). A failed step stops the steps after it, so the order still works as stages.
- Scanners:
  - bandit 1.9.4 (2026-02-25): risky patterns in our own Python code. Tests are excluded because they use `assert` on purpose.
  - Trivy 0.75.0 (2026-10-01): known vulnerabilities in our packages and secrets in our files, in one tool.
    The same tool will scan the Docker image after the BUILD stage, so I learn one scanner and use it twice.
  - Considered pip-audit (packages) + gitleaks (secrets, including Git history). Kept as alternatives.
    pip-audit depends on `pip` itself, so the lock would need `--allow-unsafe`.
- Trivy runs from its official image **pinned by digest**, not through `aquasecurity/trivy-action`:
  - In March 2026, `trivy-action` tags were hijacked and malicious Trivy releases were published
    (advisory GHSA-69fq-xp46-6x23). The advisory says images referenced by digest were not affected.
  - Version 0.75.0 because it includes the fix for GHSA-mcj4-mphf-j9ff (fixed in 0.71.1), is about 2 weeks old
    (release cooldown; 0.76.0 was 1 day old), and is an immutable GitHub release.
  - Digest `sha256:af6acf9a6b85dfe389a1941505c0ce9efef52a4719635e1a962f022a3d855daa`, the same on
    ghcr.io and Docker Hub (checked 2026-10-15).
- Kept: `permissions: contents: read`, `persist-credentials: false`, actions pinned to verified SHAs
  (`checkout` v7.0.1, `setup-python` v7.0.0, the same as Entry 3), `--only-binary :all: --require-hashes`,
  `timeout-minutes: 10`.
- Concurrency changed: `cancel-in-progress` only for `pull_request` events, so a run on `main` is never cancelled.
- Removed the pip cache to keep the file short.
- Triggers in PR #4: unchanged (`pull_request` and `push` to `main`).
- Follow-up (same day): `push` now runs on every branch (`branches: ["**"]`), so CI gives feedback
  as soon as a branch is pushed, before any PR exists.
  - Trade-off: once a PR is open, each push starts two runs for the same code (`push` and `pull_request`).
    They are in different concurrency groups (`refs/heads/<branch>` vs `refs/pull/<n>/merge`), so neither
    cancels the other. Accepted: a run takes about 30 seconds and the repo is small.
  - Alternative considered: keep `push` on `main` only and open a draft PR early (the Entry 3 decision).

**Implementation**
- Branch `ci/simple-pipeline`, PR #4.
- `api/requirements-dev.in`: added `bandit==1.9.4`; regenerated `api/requirements-dev.txt`
  (bandit plus pyyaml, stevedore, rich, markdown-it-py, mdurl, all with hashes; other pins unchanged).
- `.github/workflows/ci.yml`: rewritten as one job with a plain-English comment and a `name:` per step.

**Verification**
- Before pushing: the YAML parses, and every step has exactly one `uses:` or `run:`.
- Prediction: green. Result: green.
- PR #4: CI run `38850082116` green (about 30 seconds), SonarCloud quality gate passed.
- Merged on 2026-10-16 (squash commit `4337fc3`). Run `38851009996` (`push` to `main`) green.
- Trivy's log listed only `api/requirements.txt` as a package file.

**Troubleshooting**
1. *An uncommitted edit would have been lost.*
   - The planned tidy-up included `git reset --hard origin/main`, which discards uncommitted changes, and
     `api/requirements-dev.in` had an uncommitted edit.
   - Fix: `git restore` the file on purpose, tidy up, then redo the edit on the new branch.
2. *The lock file header showed `--no-index`, which I did not type.*
   - No pip config or environment variable sets it, and the new packages were still downloaded from PyPI,
     so it had no effect. Cause not found; only the header comment is affected.
3. *Trivy scanned `api/requirements.txt` but not `api/requirements-dev.txt`.*
   - Result: the runtime packages (what will ship in the image) are checked; the dev-only tools
     (pytest, Ruff, bandit) are not. Acceptable for now, because the dev tools never go into the image.
4. *Does pushing a feature branch run CI?*
   - Not by itself. The run for `ci/simple-pipeline` came from the `pull_request` event; there was no `push` run.
   - In the Entry 3 history, `push` runs on a feature branch did appear, named `.github/workflows/ci.yml`:
     with an invalid file, GitHub cannot read the `on:` filters or the `name:`.

**Lesson**
- Simple beats clever when I have to explain it: one job with named steps reads like a checklist.
- Each job runs on a clean runner. Separate jobs give separate results, but each one has to set itself up again.
- Anything that can move (a tag, a "latest" image) can be swapped by an attacker. A SHA or a digest cannot.
- Before choosing a tool's version, I read its security advisories, not just its release list.
- Before `git reset --hard`, I run `git status`: it throws away uncommitted work without asking.

**Next step**
- Failure drills for this pipeline (Predict → Break → Observe → Fix → Verify): Ruff, pytest, bandit, Trivy secret.
- Update `docs/architecture.md` section 9 (it still describes three parallel jobs).
- Then the BUILD stage: Dockerfile for the api, and a Trivy image scan.
