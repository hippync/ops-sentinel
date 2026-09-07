# Ops Sentinel

A multi-agent AI-SRE system that compresses the investigation phase of an incident and hands the
on-call engineer a **validated**, ready-to-review fix — with an explicit, inspectable safety gate
between "an AI proposed something" and "something executes."

> **Status:** v1 in development. Portfolio project (Solutions Architect / AI Engineer track),
> one-semester timeline. See [`docs/sprints.md`](docs/sprints.md) for the current sprint.

---

## Purpose

On-call engineers lose roughly the first **45 minutes** of every incident to investigation —
correlating logs, checking recent deploys, digging through metrics — before they can even begin
deciding what to do.

The obvious fix is "point an LLM at it." The reason that isn't already solved is the second problem:
agentic tooling in real SDLC work fails not by being obviously wrong, but by **lacking
self-validation**. It produces plausible-looking output with no signal about whether it's safe to
trust. This is structural, not anecdotal — one study found 80% of organizations reported their AI
agents had already acted beyond intended scope, and a survey of 286 organizations found nearly a
third are running agents in production while governance lags behind.

Ops Sentinel's thesis: **the interesting engineering is not the diagnosis, it's the gate.** The
Validator is the portfolio piece. Everything else exists to give it something real to reject.

**What this is not:** a replacement for Datadog, Snyk, or any existing monitoring. Ops Sentinel
lives inside the **Operate & monitor** phase of the SDLC, consumes alerts that already exist, and
closes the loop back into **Deploy** through the same approval-gated path as every other change.

---

## The pipeline

```
CloudWatch Alarm
      │
      ▼  EventBridge
┌─────────────┐
│   TRIAGE    │  classify severity + incident type
└─────────────┘
      │
      ▼
┌─────────────┐
│   WORKER    │  investigate (logs, metrics, recent deploys) → propose a fix
└─────────────┘     ⤺ hard iteration cap, enforced outside the LLM
      │
      ▼
┌─────────────┐
│  VALIDATOR  │  ◄── the differentiator: deterministic rules, no LLM judgment
└─────────────┘     blast radius · secrets/PII · cost ceiling · rollback plan · injection
      │
      ├── REJECT ──► audit log + page a human, nothing executes
      │
      ▼  score: severity × confidence × reversibility
┌─────────────┐
│  APPROVAL   │  fast-path (1 click) or strict gate — never skipped
└─────────────┘
      │
      ▼
┌─────────────┐
│  EXECUTOR   │  deterministic, NO LLM, minimum-privilege IAM
└─────────────┘
      │
      ▼  audit trail (every decision, every rejection, every input)
```

**The strongest guarantee in the system doesn't depend on the Validator being correct.** The
Executor's IAM role is scoped at deploy time to its exact known action set — even a fully
manipulated agent cannot act outside that list. The Validator is defense in depth on top of that,
not the only thing standing between the LLM and your infrastructure.

---

## Repository structure

```
ops-sentinel/
├── agents/              Python — the pipeline itself
│   └── src/ops_sentinel/
│       ├── triage/      alert → severity + incident type
│       ├── worker/      investigate → propose (capped iterations)
│       ├── validator/   deterministic rule gate — one module per risk row
│       ├── executor/    no LLM, min-privilege, post-approval only
│       ├── graph/       LangGraph orchestration + state
│       ├── schemas/     Pydantic contracts between stages
│       └── audit/       structured decision log
├── sandbox-app/         Java 21 / Spring Boot 3 — the system under observation
│   └── src/main/java/com/opssentinel/orders/
│       ├── api/         Orders CRUD (normal traffic)
│       ├── domain/      JPA entities + repositories
│       ├── chaos/       admin-only failure injection (internal listener only)
│       └── config/      security, admin key, actuator
├── infra/               Terraform — ECS Fargate, RDS, ALB, CloudWatch, EventBridge, IAM
│   └── policies/        the Executor's minimum-privilege IAM policy (reviewed, not generated)
├── docs/                business case, risk register, architecture, sprints, ADRs
├── scripts/             local dev + demo drivers
└── .github/workflows/   CI
```

Monorepo, deliberately: the chaos triggers in `sandbox-app/` map 1:1 to rows in the risk register,
the Validator's tests consume incidents that app produces, and `infra/` provisions both the app and
the alarms that trigger the pipeline. Splitting these would create version skew between an injected
failure and the test asserting it's defended.

---

## Technology

| Layer | Choice | Why |
|---|---|---|
| Orchestration | **Python 3.12 + LangGraph** | Explicit state machine with inspectable transitions — the audit trail falls out of the graph rather than being bolted on |
| Contracts | **Pydantic v2** | Stage boundaries are typed and validated; a malformed proposal fails at the boundary, not deep in the Validator |
| Validator | **Plain Python, no LLM** | A safety gate judged by an LLM is not a safety gate. Every rule is readable, unit-testable, and deterministic |
| Executor | **boto3, no LLM** | Fixed action set, scoped IAM role, runs only on approved proposals |
| Sandbox app | **Java 21 + Spring Boot 3, Spring Data JPA** | Covers the Java/Spring side of the job search alongside .NET/C#, and absorbs the Spring Boot API that was previously deferred to v2 |
| Data | **Postgres (RDS)** | Orders persistence for the sandbox app |
| Runtime | **ECS Fargate + ALB** | Real deploys, real rollbacks — chaos trigger #1 is an actual bad task-definition rollout, not a script |
| Signals | **CloudWatch** (Container Insights, logs, alarms) | The real trigger source; the pipeline reads state here, never via actuator |
| Trigger | **EventBridge** | Alarm state change → pipeline invocation |
| IaC | **Terraform** | The minimum-privilege IAM scope is a reviewed artifact in version control, not console clicks |
| Testing | **pytest** (agents) · **JUnit 5** (sandbox) | Injection defense and every Validator rule are explicit test cases |

---

## The Validator's rules

Each rule maps to a numbered row in [`docs/ops-sentinel-risk-register.md`](docs/ops-sentinel-risk-register.md).
All are deterministic and enforced outside the LLM's control.

| # | Rule | Behavior on breach |
|---|---|---|
| 1 | Action must target a **single named resource ID** | Wildcards/tag patterns never fast-path — always strict approval |
| 2 | No **credentials or PII** in the proposal | Scrub or reject before a human ever reads it |
| 3 | Worker **iteration cap** | Fail loudly and page a human; never continue silently |
| 4 | **Cost ceiling** — max instance count / spend delta | Reject scale actions with no upper bound |
| 5 | Ingested content is **data, never instructions** | Explicitly tested with a crafted injection case |
| 6 | Executor IAM scoped to its **exact action set** | Enforced at deploy time, independent of the Validator |
| 7 | **Rollback plan required** | Reject any proposal without a defined rollback step |
| 8 | Documented **false-positive tolerance** | A designed trade-off, tracked over time — not an accident |

### Approval-path scoring

Every proposal is scored on three axes rather than a single approve/reject bit:

- **Severity** — how bad if the fix is wrong
- **Confidence** — how sure the Worker is, based on diagnostic signal strength
- **Reversibility** — whether a clean rollback exists

`low severity + high confidence + reversible` → **fast-path** (single-click, pre-validated)
`high severity OR irreversible` → **strict gate**, regardless of confidence

---

## The sandbox app

Deliberately small — a handful of Orders endpoints. It exists to generate real, controllable
incidents, not to be interesting itself.

**Normal traffic:** `GET /orders` · `POST /orders` · `GET /orders/{id}` · `GET /actuator/health`

**Chaos triggers** (admin API key, internal listener only — never on the public ALB):

| # | Trigger | How it's induced | Risk row exercised |
|---|---|---|---|
| 1 | Bad deploy → elevated 5xx | A real ECS deployment of a broken task-definition revision | Blast radius / rollback required |
| 2 | Memory leak → OOM restarts | `POST /admin/chaos/leak` appends to a static list until the container genuinely OOMs | Cost ceiling / runaway infra |
| 3 | Injected log line | `POST /admin/chaos/log-injection` logs a crafted ERROR designed to read as an instruction | Prompt-injection defense |

Applying the same risk discipline to the sandbox app itself — not just to the AI watching it — is
part of the story, not an afterthought.

---

## Success criteria (v1)

- [ ] Full pipeline runs end-to-end on a real, self-triggered incident in a personal AWS sandbox
- [ ] **Time-to-diagnosis** measured from alert to validated proposal, framed against the ~45-min manual baseline
- [ ] A recorded demo where the **Validator blocks an unsafe fix**
- [ ] A presentable audit trail of every decision

### Scope

**In (v1):** single sandbox app · Triage → Worker → Validator → human approval → Executor · one blocked-fix demo · audit log
**Out (v1):** auto-execution without approval · multiple parallel workers · production deployment

---

## Getting started

```bash
# Agents
cd agents && python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest

# Sandbox app
cd sandbox-app && ./mvnw spring-boot:run

# Infra (sandbox env)
cd infra/terraform/envs/sandbox && terraform init && terraform plan
```

See [`docs/architecture.md`](docs/architecture.md) for the full design and
[`docs/sprints.md`](docs/sprints.md) for the delivery plan.

---

## Documentation

| Document | What it covers |
|---|---|
| [Business case](docs/ops-sentinel-business-case.md) | Problem, solution, differentiator, scope |
| [Risk register](docs/ops-sentinel-risk-register.md) | 8 risks → detection signal → hard rule → residual risk |
| [Sandbox app spec](docs/ops-sentinel-sandbox-app-spec.md) | The system under observation |
| [Architecture](docs/architecture.md) | Components, data flow, state, trust boundaries |
| [Sprints](docs/sprints.md) | Semester delivery plan |
| [ADRs](docs/adr/) | Why each significant choice was made |
