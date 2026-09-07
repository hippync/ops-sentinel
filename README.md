# Ops Sentinel

A multi-agent AI-SRE system that compresses the investigation phase of an incident and hands the
on-call engineer a **validated**, ready-to-review fix — with an explicit, inspectable safety gate
between "an AI proposed something" and "something executes."

> ### Build status — Sprint 1 of 6
>
> **Working today:** typed stage contracts, an unforgeable content-derived `proposal_hash`,
> the `rollback` Validator rule (risk row 7) with tests, and a CI check that fails if the
> Executor's IAM policy drifts from its action set.
>
> **Not built yet:** the remaining five Validator rules, Triage, Worker, Executor, the
> sandbox app's endpoints, and all AWS infrastructure. Sections below describe the design
> those will implement — read them as specification, not as a description of running code.
>
> Portfolio project (Solutions Architect / AI Engineer track), one semester, part-time.
> Current sprint: [`docs/sprints.md`](docs/sprints.md).

---

## Purpose

On-call engineers lose roughly the first **45 minutes** of every incident to investigation —
correlating logs, checking recent deploys, digging through metrics — before they can even begin
deciding what to do.

That 45 minutes is *industry motivation, and it is never used as this project's denominator.*
It describes a human meeting a novel incident in an unfamiliar production system; Ops Sentinel
handles three known incident types in a purpose-built sandbox with a playbook for each. Comparing
them would inflate the headline and collapse under the first question. The measured baseline is
**the author solving the same sandbox incident by hand** — a smaller number, and a defensible one.

The obvious fix is "point an LLM at it." The reason that isn't already solved is the second problem:
agentic tooling in real SDLC work fails not by being obviously wrong, but by **lacking
self-validation**. It produces plausible-looking output with no signal about whether it's safe to
trust.

Industry data suggests this is structural rather than anecdotal — reported rates of agents acting
beyond their intended scope are high, and adoption in production is running ahead of governance.

> **On the numbers:** earlier drafts of this README quoted two specific statistics without
> citations. They have been removed pending sources I can link. A project whose thesis is
> "don't trust plausible-looking claims without a verification step" cannot ship uncited
> figures in its own problem statement.

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
Executor's IAM role is scoped at deploy time to its known action set, so a fully manipulated agent
still cannot reach outside it. The Validator is defense in depth on top of that, not the only thing
standing between the LLM and your infrastructure.

**With two caveats this project states rather than glosses.** `ecs:UpdateService` is a single IAM
action covering all three action types, so IAM cannot tell a rollback from a restart from a scale —
the guarantee is real but coarser than one-action-per-action-type. And AWS exposes no IAM condition
key for `desiredCount`, so the **cost ceiling (row 4) cannot live in IAM at all**; it is enforced in
the Validator, in ECS Service Auto Scaling max capacity, and in the Executor's re-check instead.
[ADR-0007](docs/adr/0007-row-4-cannot-live-in-iam.md) has the verification and the sources. A
reviewer who finds a gap like this unaided discounts everything else in the register.

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
├── scripts/             local dev + demo drivers, and the IAM drift check CI runs
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
| Orchestration | **Python 3.12 + LangGraph** | Durable suspend/resume across the human approval pause, which may span hours and process death — the hard part of this graph is the pause, not the five-node topology. Conditional on [ADR-0004](docs/adr/0004-pipeline-runtime.md); see [ADR-0002](docs/adr/0002-langgraph-orchestration.md) |
| Contracts | **Pydantic v2** | Stage boundaries are typed and validated; a malformed proposal fails at the boundary, not deep in the Validator |
| Validator | **Plain Python, no LLM** | A safety gate judged by an LLM is not a safety gate. Every rule is readable, unit-testable, and deterministic |
| Executor | **boto3, no LLM** | Fixed action set, scoped IAM role, runs only on approved proposals |
| Sandbox app | **Java 21 + Spring Boot 3, Spring Data JPA** | A second portfolio surface, deliberately: the pipeline only needs a service that fails on command, but a realistic one produces realistic incidents — a null dereference in a repository call is a more credible bad deploy than a hardcoded 500 |
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
| 2 | No **credentials or PII** in the proposal | The gate **rejects**; redaction happens at rendering. Scrubbing would change the proposal's hash and break the Executor's verification chain |
| 3 | Worker **iteration cap** | Fail loudly and page a human; never continue silently |
| 4 | **Cost ceiling** — max instance count | Reject scale actions with no upper bound. Cannot be enforced in IAM ([ADR-0007](docs/adr/0007-row-4-cannot-live-in-iam.md)) — so enforced three times: Validator, ECS autoscaling max capacity, Executor re-check |
| 5 | Action must be **derivable from structured incident data** | Target must be in `affected_resource_ids`; action type must be in the playbook for the incident type. Tested with a crafted injection case |
| 6 | Executor IAM scoped to its **known action set** | Enforced at deploy time, independent of the Validator; drift from the enum fails CI |
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
- [ ] **Time-to-diagnosis** measured from alert to validated proposal, reported as an absolute
      number against a **self-timed manual baseline on the same sandbox incident**
- [ ] A recorded demo where the **Validator blocks an unsafe fix**
- [ ] A presentable audit trail of every decision

### Scope

**In (v1):** single sandbox app · Triage → Worker → Validator → human approval → Executor · one blocked-fix demo · audit log
**Out (v1):** auto-execution without approval · multiple parallel workers · production deployment

---

## Getting started

These run today, on a clean checkout:

```bash
# Agents — 17 tests, ruff, and mypy --strict all pass
cd agents
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q && ruff check . && mypy src

# Sandbox app — compiles and runs its unit tests (no database needed)
cd sandbox-app && ./mvnw -B verify

# Risk row 6 drift check — fails if the IAM policy and the ActionType enum disagree
python3 scripts/check_iam_scope.py
```

**Not yet runnable**, and deliberately not listed as if it were: `./mvnw spring-boot:run`
(needs Postgres and the endpoints from Sprint 2) and `terraform plan` (no `.tf` files
until Sprint 3).

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
