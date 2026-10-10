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
