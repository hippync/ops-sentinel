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
> decision-point extraction layer, the sandbox app's endpoints, and all AWS infrastructure.
> Sections below describe the design those will implement — read them as specification, not
> as a description of running code. **No miss rate has been measured yet**; every number in
> the extraction section is a target.
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
      ▼  score: severity × confidence × reversibility
┌─────────────┐
│  EXTRACTION │  3-5 decision points from the trajectory — what was chosen, what else
└─────────────┘  was viable, what it rests on, what breaks if it's wrong
      │          reads OTel spans · gates nothing · cannot alter the proposal
      │
      ├── REJECT ──► decision register + page a human, nothing executes
      │
      ▼
┌─────────────┐
│  APPROVAL   │  fast-path (1 click) or strict gate — never skipped
└─────────────┘  cards render above the buttons, fast path included
      │
      ▼
┌─────────────┐
│  EXECUTOR   │  deterministic, NO LLM, minimum-privilege IAM
└─────────────┘
      │
      ▼  decision register (every decision, every rejection, every input)
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
│       ├── extraction/  decision points from the trajectory — gates nothing
│       ├── telemetry/   OTel spans, GenAI semantic conventions
│       ├── executor/    no LLM, min-privilege, post-approval only
│       ├── graph/       LangGraph orchestration + state
│       ├── schemas/     Pydantic contracts between stages
│       └── audit/       the decision register
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
├── .claude/             the AI-assisted build harness — checks, review agents, commands
├── CLAUDE.md            standing context for that harness: status, conventions, hard rules
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
| Tracing | **OpenTelemetry**, GenAI semantic conventions | The extraction layer needs a structured trajectory to read, and a standard one keeps the decision-point work from being tied to this pipeline's shape. Worth having for debugging on its own |
| Approval surface | **Slack app** | Out-of-process and asynchronous, which is what makes ADR-0002's durable-suspend argument real; Block Kit renders the decision cards without a UI to build. [ADR-0005](docs/adr/0005-approval-surface.md) |
| Decision register | **DynamoDB** | A decision point is an independently addressable item, not a line in a narrative — keyed lookup beats log search here. [ADR-0006](docs/adr/0006-audit-log-store.md) |
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

## Decision-point extraction

**Where it sits:** between the Validator and the approval gate. The Validator checks the *output*
against explicit rules; this layer exposes the *path*.

An approval gate that shows a human a proposed fix and two buttons is asking for **a signature
without a reading**. The approver formally owns a decision they have no practical means of
examining — documented responsibility with no epistemic basis behind it.

That is not a quirk of this project. Supervision infrastructure is built for **artifacts**: a
diff, a contract, a case file — something a person reads and signs. Agents produce
**trajectories**: tool calls, intermediate state, a final answer, and a log nobody opens.
Accountability still attaches to a named individual either way — so it survives the transition
intact, and the basis for it does not.

So instead of *"here is the proposed fix, approve or reject"*, the approver sees **3–5 extracted
decision points**, each answering four questions:

- **What was chosen** at this moment in the trajectory
- **What alternatives were viable** — the branches genuinely available and not taken
- **What it rests on** — the evidence or assumption the choice depends on
- **What breaks downstream** if it is wrong

### It is not a second gate

This is the constraint everything else hangs off, and it is what keeps
[ADR-0003](docs/adr/0003-no-llm-in-validator.md) intact. The extractor **cannot pass, reject,
re-score, or modify a proposal**, and has no edge to the Executor. It never touches
`proposal_hash` — cards are keyed *by* the hash, never part of the hashed content, for the same
reason `secrets.py` rejects rather than scrubs. Extraction failure **downgrades fast-path to
strict** rather than blocking the run. Cards render through `audit/redaction`, because decision
points quote attacker-influenced log content on its way to a human. And they appear on the fast
path too — a low-severity, high-confidence, reversible proposal is exactly the one approved
without reading.

### How the points are found

A deterministic rule set first, written in the Validator's idiom, over OpenTelemetry spans from
Triage and the Worker:

| Family | Fires on | Risk row |
|---|---|---|
| Irreversible action | No clean rollback exists | 7 |
| External write | A span that mutates rather than reads | 1 |
| Out-of-scope resource access | A resource absent from `affected_resource_ids` | 5 |
| Triage's `incident_type` call | Always — it selects the playbook constraining every later action | 5 |
| Diagnosis changed mid-run | Evidence reinterpreted between Worker iterations | 3 |

An LLM classifier over the remaining spans is built **only if** the rules alone leave the miss
rate too high — and its output is visually marked, so a reader always knows which points are
deterministic.

### The deliverable is the miss rate, not the cards

Anyone can wire an LLM to traces and produce plausible-looking cards. Almost nobody can state how
often their system misses what mattered — and *"plausible-looking output with no signal about
whether it's safe to trust"* is this project's own problem statement, so shipping this layer
unmeasured would be the sharpest available self-inflicted wound.

So: **a published miss rate on a reproducible harness**, plus the curve between that rate and the
number of points surfaced. ~20 seeded incident scenarios, each with one critical decision labeled
*before* any extraction rule is written, run against recorded alarm payloads and the fake
executor — in CI, with no AWS account and no Slack workspace, so a reader can reproduce the
number. [ADR-0009](docs/adr/0009-extraction-evaluation-harness.md) has the protocol, including
the parts that are still open.

**Kill criterion:** if after ~10 scenarios the extractor consistently surfaces either everything
or nothing useful, the hypothesis is wrong for this domain and the layer is dropped. The OTel
instrumentation and the evaluation harness stay — they are worth having independently.

**Downstream effect:** the audit log becomes a **decision register rather than an approval
history** — what was decided and on what basis, not a list of who clicked yes.

**Open, and deliberately unresolved:** whether a decision-point taxonomy transfers across domains
(incident response → credit → legal). Only answerable empirically.

See [ADR-0008](docs/adr/0008-decision-point-extraction.md).

---

## Framework alignment

Where this work sits relative to three frameworks. Nothing here is audited and nothing below
claims compliance.

**NIST AI RMF** — the anchor. Voluntary, free, four functions: Govern, Map, Measure, Manage. Two
describe this repo.

*Govern* covers the Validator, the risk register, and the IAM scoping — eight risk rows, each with
a detection signal and a hard rule enforced outside the LLM.
[ADR-0003](docs/adr/0003-no-llm-in-validator.md)'s "no LLM in the safety gate" is the governance
commitment; the CI drift check on the Executor's policy stops it decaying into an intention.

*Measure* covers the evaluation harness: it asks for documented test results on what you claim
about a system, and [ADR-0009](docs/adr/0009-extraction-evaluation-harness.md)'s miss rate —
recall against decisions labeled before any extraction rule was written, reproducible in CI
without an AWS account — is that shape. Map and Manage are thin: scope is fixed by the sandbox, and
post-deployment monitoring doesn't exist yet.

**OSFI Guideline E-23** (model risk management, in force 1 May 2027) — the institutional context.
E-23 governs a model lifecycle whose stages — rationale, development, review, approval — assume a
decision that can be attributed and documented. An autonomous multi-step agent doesn't produce
one. It produces a trajectory, and the approval record captures who clicked yes, not what was
decided or on what basis. That is the gap
[ADR-0008](docs/adr/0008-decision-point-extraction.md) describes, reached independently. The
decision register ([ADR-0006](docs/adr/0006-audit-log-store.md)) is this project's answer: every
decision point an addressable item, not a line in a narrative.

**AIUC-1** — the agent-specific layer; Accountability and Reliability are the relevant pillars. It
positions itself as operationalizing ISO 42001, NIST AI RMF, MITRE ATLAS, the EU AI Act and the
OWASP Top Ten rather than replacing them, so it complements the NIST anchor instead of duplicating
it. It also requires recurring technical testing rather than one annual review, which converges
with the seeded-scenario harness: a fixture corpus re-run in CI is the shape that requirement asks
for.

**Limits.** Each framework asks for more than this repo does. AI RMF's Map and Manage expect
impact analysis and production monitoring; neither exists here. E-23 expects independent review by
someone who did not build the model; this project has one author. AIUC-1 certification
requires an accredited third-party audit and adversarial testing against a live agent; nothing
here has been tested by anyone but its author. And the mapping above is the author's own reading,
not an assessment — nobody has checked it.

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
- [ ] A presentable decision register covering every decision
- [ ] **A published miss rate for decision-point extraction**, on a harness a reader can run —
      plus the curve between that rate and the number of points surfaced. Stated as a measurement
      with its caveats, or reported as a kill decision. Not stated at all until measured

### Scope

**In (v1):** single sandbox app · Triage → Worker → Validator → extraction → human approval → Executor · one blocked-fix demo · decision register · a measured extraction miss rate
**Out (v1):** auto-execution without approval · multiple parallel workers · production deployment · cross-domain taxonomy claims

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
| [Agentic workflow](docs/agentic-workflow.md) | How this repo is built with AI assistance — and the two places that assistance is refused |
| [ADR-0008](docs/adr/0008-decision-point-extraction.md) | The extraction layer — why, and the six constraints that keep it from becoming a second gate |
| [ADR-0009](docs/adr/0009-extraction-evaluation-harness.md) | How the miss rate is measured, and what is still open about it |
| [ADRs](docs/adr/) | Why each significant choice was made |
