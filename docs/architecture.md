# FreshTrack — Architecture

Last updated: 2026-10-09

**Status rule:** a part is marked **Built** only when it is merged to `main` and verified.
Everything else is **Planned**. Today, nothing is built yet.

---

## 1. What FreshTrack does (plain language)

A household writes down the food it buys: what it is, how much, where it is stored
(fridge, freezer or cupboard) and the date on the label. FreshTrack shows the list
with the soonest dates at the top. Every morning it emails the household the items
that are within 3 days of their date or already past it.

FreshTrack **organises reminders**. It never says whether food is safe to eat.

## 2. Version 1 scope

| In scope | Out of scope (ask Samson first) |
|---|---|
| Add an item: name, quantity, location, label date, date type (best before / expiration date) | Account registration |
| Active list, closest date first | Multiple households |
| Mark an item as used or discarded (it stays in the database as trial data) | Native mobile app |
| One morning email (America/Toronto) to one household address | Barcode or receipt scanning |
| Wording that distinguishes best before from expiration date | Recipes, automatic grocery ordering |

## 3. Components

| Component | What it is | Job | Status |
|---|---|---|---|
| **web** | Flask + HTML templates, no JavaScript framework | The pages people see. Has no database access; it calls the api. | Planned |
| **api** | Flask (JSON over HTTP) | All the rules, and the only component that reads or writes the database. | Planned |
| **expiry-checker** | Python script run by a Kubernetes CronJob | Every morning, asks for due items and sends one email. | Planned |
| **PostgreSQL** | Database | Stores items, including used and discarded ones. | Planned |
| **Mailpit** | Fake mail server (dev/test only) | Catches emails so no real email is sent while we test. | Planned |

Every app exposes `/health` (am I alive?) and `/ready` (can I reach what I need?
For the api, that means the database).

## 4. How the parts talk (planned)

```mermaid
flowchart LR
    user([Household member<br/>browser]) -->|HTTPS + basic auth<br/>before any public exposure| gw[Ingress / Gateway]
    gw --> web[web<br/>Flask + templates]
    web -->|HTTP JSON| api[api<br/>Flask]
    api -->|SQL| db[(PostgreSQL)]
    cron[expiry-checker<br/>CronJob, mornings Toronto time] -->|HTTP JSON:<br/>items due in 3 days| api
    cron -->|SMTP| mail[Mailpit in dev<br/>SES or Gmail on trial]
```

Kitchen analogy: **web** is the waiter, **api** is the kitchen, and **PostgreSQL** is the
walk-in fridge. Only the kitchen goes into the fridge. **expiry-checker** is the
morning prep cook who asks the kitchen "what needs using up?" and pins a note on
the board (the email).

### Flow A — adding an item
1. The user fills in the form on **web**.
2. **web** sends the data to **api** (`POST /items`).
3. **api** checks it (valid location, valid date type, date present) and saves it to **PostgreSQL**.
4. **web** shows the updated list.

### Flow B — the morning reminder
1. The Kubernetes CronJob starts **expiry-checker** each morning, America/Toronto time.
2. **expiry-checker** asks **api** for active items whose date is within 3 days or already past.
3. If there are any, it builds one email with separate "Best before" and "Expiration date" wording
   and sends it to the configured household address.
4. It exits. Success or failure shows in the Job status and logs.

## 5. Data model (planned, one table)

`items`

| Column | Type | Notes |
|---|---|---|
| id | integer, primary key | |
| name | text | e.g. "Greek yogurt" |
| quantity | text | Free text such as "2 cartons" or "500 g", kept simple for v1 |
| location | `fridge` / `freezer` / `cupboard` | Enforced by the database |
| label_date | date | The date printed on the package |
| date_type | `best_before` / `expiration` | Changes the reminder wording ("Best before" / "Expiration date") |
| status | `active` / `used` / `discarded` | Rows are never deleted |
| created_at | timestamp | |
| closed_at | timestamp, empty while active | When it was used or discarded |

The household email address is **not** stored in the database. It comes from config or a Secret.

## 6. Where it runs

| Environment | Purpose | Email | Status |
|---|---|---|---|
| Laptop (WSL Ubuntu) | Write and test code | Mailpit | Planned |
| Minikube (main lab, multi-node when useful) | Learn and practise Kubernetes, failure drills | Mailpit | Planned |
| k3s on AWS EC2, ca-central-1 (about 1 week) | Household trial and demo | Amazon SES sandbox or Gmail App Password (to decide) | Planned |

AWS infrastructure is defined in a separate repo, `terraform-aws-platform`.
**Cost rule:** destroy AWS resources after demo days.

## 7. Kubernetes objects: where each one fits FreshTrack (planned)

| Object | FreshTrack use |
|---|---|
| Namespace | `freshtrack` keeps all our objects in one labelled shelf |
| Pod, ReplicaSet, Deployment | web and api; practise rolling update and rollback |
| Service (ClusterIP) | Stable internal address for web and api |
| Service (headless) | Stable network identity for the PostgreSQL StatefulSet |
| StatefulSet, PVC, PV, StorageClass | PostgreSQL with storage that survives Pod restarts |
| ConfigMap | Non-secret settings: time zone, reminder window (3 days), api URL |
| Secret | Database password, SMTP credentials, household email address |
| Job | One-off database setup (create the table) and manual runs of the checker |
| CronJob | expiry-checker each morning, using `timeZone: America/Toronto` |
| Ingress or Gateway API | Entry point to web; TLS + basic auth before public exposure |
| ServiceAccount, RBAC | One identity per app, with only the permissions it needs (mostly none) |
| NetworkPolicy | Only web→api, checker→api and api→PostgreSQL are allowed; everything else is blocked |
| Probes | Liveness → `/health`, readiness → `/ready` |
| Requests and limits | Every container gets a fair, capped share of CPU and memory |
| HPA | web/api scale on CPU during a load-test drill (a household doesn't need it, so we'll say that honestly) |
| PodDisruptionBudget | Keeps at least one api Pod running while a node is drained |
| DaemonSet | Grafana Alloy on every node, collecting logs for Loki |
| Nodes, taints/tolerations, affinity | Multi-node Minikube: PostgreSQL pinned to a "data" node, web replicas spread across nodes |

## 8. Security and privacy (planned)

- No user accounts in v1. The grocery list is still personal, so access is restricted.
- **Before any internet exposure:** TLS + basic authentication at the Ingress/Gateway.
- Secrets live in OpenBao/Vault and are synced into Kubernetes by External Secrets
  Operator. Reloader restarts Pods when a secret changes. Secrets are never baked
  into images and never committed.
- Hardened images: pinned base image digest, hash-locked dependencies, non-root user, small image.
- NetworkPolicies limit who can talk to whom.

## 9. Delivery pipeline (planned)

**Check → Build → Prove → Scan → Ship.** Like a food factory: inspect the ingredients,
cook, taste, get QC release, dispatch. Each stage is a gate; a failure stops everything after it.

| # | Stage | Factory version | What it does | What it catches |
|---|---|---|---|---|
| 1 | CHECK (3 parallel jobs) | Incoming raw-material inspection | Lint (Ruff), Test (pytest against a real PostgreSQL), Repo scan (Trivy: secrets, vulnerable libraries, misconfiguration) | Messy or broken code, wrong logic or SQL, leaked secrets, vulnerable dependencies, unsafe Dockerfile/K8s settings |
| 2 | BUILD | Production | Build the Docker image for web, api and expiry-checker side by side | Dockerfile errors, missing dependencies |
| 3 | PROVE | Taste test on the line | Start the container and call `/health` (the checker runs a dry run) | An image that builds but won't start |
| 4 | SCAN | QC release testing | Trivy image scan: fail on fixable HIGH/CRITICAL, report everything | Vulnerabilities in the base image and OS packages |
| 5 | SHIP | Dispatch | Push to Docker Hub tagged with the git SHA, **only on `main`** | (release step) |

```
          ┌─ Lint (Ruff)        ─┐
PR/push → ├─ Test (pytest + DB) ─┼─→ [ Build → Prove → Scan → Ship* ]  × 3 apps (matrix)
          └─ Repo scan (Trivy)  ─┘        (*Ship only on main)
SonarCloud runs alongside. It must pass before merge but doesn't block the release path.
```

**Security**
- Workflow token is read-only by default (`permissions: contents: read`).
- Every action is pinned to a full commit SHA, verified against its real release tag.
- The Docker Hub token is used only in the Ship step, only on `main`. Pull requests never see it.
- An image is scanned before it is pushed, so a vulnerable image never reaches the registry.

**Speed (target under 2 minutes on a warm cache; to be measured, not assumed)**
- CHECK jobs run in parallel; the 3 apps build in parallel (matrix).
- Build → Prove → Scan → Ship run in one job per app, so the image is never passed between jobs.
- Caches for Python packages, Docker layers and the Trivy database.
- `concurrency: cancel-in-progress` and `timeout-minutes` on every job.

**Limits (what CI does not catch):** logic with no test, wrong settings inside the
cluster, and runtime failures such as the database being down. Probes, Argo CD and monitoring cover those.

**Deploy (CD):** CI pushes the image. The new tag is written into Git (method to be chosen),
and Argo CD sees the change and syncs the cluster. In short: CI pushes, GitOps pulls.

## 10. Observability (planned)

Prometheus (metrics), Grafana (dashboards), Loki + Grafana Alloy (logs),
Alertmanager (alerts). A first useful alert: "the morning reminder Job failed."

## 11. Tools and their alternatives

| Role | We use | Alternative |
|---|---|---|
| Source control | Git + GitHub | GitLab |
| CI/CD | GitHub Actions | GitLab CI, Jenkins |
| Code quality | Ruff + SonarCloud | SonarQube Community |
| Image scan | Trivy | Grype |
| Registry | Docker Hub | Harbor |
| Local cluster | Minikube | kind |
| Cloud cluster | k3s on AWS EC2 | EKS |
| Cloud infrastructure | Terraform | OpenTofu |
| Server configuration | Ansible | cloud-init |
| Packaging | Helm | Kustomize |
| GitOps | Argo CD | Flux |
| Secrets | OpenBao/Vault + External Secrets Operator + Reloader | Sealed Secrets, SOPS |
| Monitoring | Prometheus, Grafana, Loki, Alloy, Alertmanager | VictoriaMetrics |

Versions are chosen when each tool is introduced, after checking its official docs.

## 12. Open decisions

| # | Question | Current proposal |
|---|---|---|
| 1 | Does expiry-checker read the database directly, or ask the api? | **Decided (2026-10-09):** it asks the api. Only the api touches the database, so the "due within 3 days" rule lives in one place |
| 2 | Ingress or Gateway API? | Decide at the networking stage after checking current docs (community ingress-nginx is retired) |
| 3 | Trial email: Amazon SES sandbox or Gmail App Password? | Decide before the AWS trial |
| 4 | Morning email time | Proposal: 07:00 America/Toronto |
| 5 | Send an email on days with nothing due? | Proposal: no email. The Job still logs "0 items due" |
| 6 | Label wording: "expiry" vs Canada's "expiration date" | **Decided (2026-10-09):** "Expiration date" (stored as `expiration`) |
