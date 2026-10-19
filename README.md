FreshTrack
A household food expiry tracker — know what's in the fridge and when it expires, before it becomes waste.
FreshTrack is a portfolio project built to production-shaped standards: a small Flask API,
a hardened Docker image, and a CI pipeline that doesn't just build the image — it proves
it, by booting it, checking its health, and scanning the finished artifact before anything
is allowed to ship.
Status (October 2026)
Done
API service (Flask, served by gunicorn) with a /health endpoint and pytest coverage
Hardened single-stage Dockerfile (details below)
GitHub Actions CI that builds, boots, health-checks and vulnerability-scans the image on
  every change — latest verified run green, 0 vulnerabilities
Architecture and build journal documented in docs/
Next, in order
Publish the image to a registry (GitHub Container Registry) from CI on every green build
Deploy to Kubernetes with Helm, rolled out by Argo CD onto AWS infrastructure provisioned
   with Terraform (terraform-aws-platform)
The deployment design — the full Kubernetes object set, probes and resource limits — is
written up in docs/architecture.md.
Run it locally
docker build -t freshtrack-api ./api
docker run --rm -p 8000:8000 freshtrack-api
curl http://localhost:8000/health
Run the tests
pip install -r api/requirements-dev.txt
pytest api/tests
The CI pipeline
.github/workflows/ci.yml runs, in order:
Lint and test — the codebase and the pytest suite
Filesystem scan — Trivy over the repository
Build — the Docker image, tagged with the commit SHA
Boot and health-check — the built image is started and must answer on /health
Image scan (the gate) — Trivy over the finished image; the build fails on any
   fixable HIGH or CRITICAL vulnerability, and on any secret found in the image
The gate has been deliberately exercised: an outdated base image that passed lint, tests,
the filesystem scan, the build and the health check was still caught and failed by the
image scan. A gate that has never failed anything is a decoration, not a control.
Security choices in the image
Base image pinned by digest — python:3.12.15-slim-trixie, so the foundation cannot
  drift silently between builds
Locked, hash-checked dependencies — wheels only, every package verified against its
  hash at install time (--require-hashes)
Runs as a non-root user (UID 10001, no login shell, no home directory) — the numeric
  ID lets Kubernetes enforce runAsNonRoot
No gunicorn control socket — the orchestrator manages the process, so the admin
  socket is disabled rather than left listening
Repository layout
api/                  Flask API, Dockerfile, locked requirements, tests
.github/workflows/    CI pipeline (ci.yml)
docs/                 architecture.md — design; journal.md — build journal
Why this project exists
FreshTrack is the application half of a two-repo portfolio: this repo proves the
application and its delivery pipeline; the
terraform-aws-platform repo
provisions the AWS foundation it will run on. The working style throughout is borrowed
from 19 years in food-industry quality assurance: verify both the pass and the fail,
keep the evidence, and never claim a control works until it has been exercised.

Built by Samson Olajide 