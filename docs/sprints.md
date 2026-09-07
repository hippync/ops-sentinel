# Ops Sentinel — Delivery plan

**Timeline:** one semester, part-time alongside coursework and work
**Cadence:** 2-week sprints · **Capacity assumption:** ~8–10 focused hours per sprint week
**Build start:** October, after the LangGraph layer of `jobs-radar-qc` is done (per the sandbox app spec)

**Sequencing principle:** the Validator is the portfolio piece, so it gets built and tested *before*
the Worker that feeds it. A Validator with hand-written proposal fixtures is demonstrable on its
own; a Worker with nothing to check it is not.

---

## Sprint 0 — Foundation *(Sep 8 – Sep 21)* — in progress

Repo, contracts, and the decisions that are expensive to change later. No agent code yet.

- [x] Business case, risk register, sandbox app spec
- [x] Repo scaffold, README, architecture doc
- [ ] **Answer the pre-mortem question** from the risk register: if every check failed at once, is
      the worst outcome already bounded by IAM scoping alone? If not a confident yes, shrink the
      Executor scope *before* v1 code starts
- [ ] Draft the Executor's minimum-privilege IAM policy → `infra/policies/executor-policy.json`
- [ ] Pydantic contracts: `Incident`, `FixProposal`, `Verdict`, `ApprovalRecord`, `AuditRecord`
- [ ] ADR-0001 monorepo · ADR-0002 LangGraph · ADR-0003 no-LLM Validator
- [ ] CI: pytest + ruff + mypy on `agents/`, Maven build on `sandbox-app/`

**Done when:** contracts are typed and committed, CI is green, the IAM scope is written down, and
the pre-mortem has a documented answer.

---

## Sprint 1 — The Validator *(Sep 22 – Oct 5)*

The differentiator, built first, against hand-written proposal fixtures. No LLM anywhere in this sprint.

- [ ] `blast_radius.py` + tests — risk row 1
- [ ] `secrets.py` + tests — risk row 2
- [ ] `cost_ceiling.py` + tests — risk row 4
- [ ] `rollback.py` + tests — risk row 7
- [ ] `injection.py` + tests — risk row 5 (action must be derivable from structured incident fields)
- [ ] `scoring.py` — severity × confidence × reversibility → fast-path or strict gate
- [ ] Fixture set: one clean proposal + one crafted violation per rule
- [ ] **Choose and document the false-positive tolerance** (risk row 8) — decided now, not justified later

**Done when:** `pytest agents/tests/unit/validator` proves each rule rejects its violation and passes
the clean case. The Validator is demonstrable standalone at this point.

---

## Sprint 2 — Sandbox app *(Oct 6 – Oct 19)*

Something real to break.

- [ ] Spring Boot 3 / Java 21 Orders API — `GET /orders`, `POST /orders`, `GET /orders/{id}`
- [ ] Spring Data JPA + Postgres, Flyway migration
- [ ] Admin API key filter; chaos endpoints bound to the internal listener only
- [ ] Chaos #2 `POST /admin/chaos/leak` — static list appended until genuine OOM
- [ ] Chaos #3 `POST /admin/chaos/log-injection` — crafted ERROR line
- [ ] JUnit: chaos endpoints reject requests without an admin key
- [ ] Dockerfile + local `docker-compose` for app + Postgres

**Done when:** the app runs locally, chaos triggers fire on demand, and unauthenticated chaos calls
are rejected by a test.

---

## Sprint 3 — Infrastructure *(Oct 20 – Nov 2)*

- [ ] Terraform: VPC, ECS Fargate service, RDS Postgres, ALB (public listener = Orders only)
- [ ] Internal listener for chaos, reachable via SSM port-forward — **not** the public route
- [ ] CloudWatch: Container Insights, log groups, alarms for 5xx rate and memory
- [ ] EventBridge rule: alarm state change → pipeline invocation
- [ ] Apply the Executor IAM role from Sprint 0's reviewed policy — nothing broader
- [ ] Chaos #1: deploy a deliberately broken task-definition revision and confirm the alarm fires

**Done when:** a chaos trigger in AWS produces a real CloudWatch alarm that reaches EventBridge.
This is the riskiest sprint — AWS wiring absorbs time unpredictably. If it slips, Sprint 4 can start
against recorded alarm payloads.

---

## Sprint 4 — Triage + Worker *(Nov 3 – Nov 16)*

- [ ] LangGraph state object and graph topology
- [ ] Triage: alarm → `Incident`; `unknown` routes straight to a human
- [ ] Worker read-only tools: CloudWatch metrics, log filter, ECS deployment history
- [ ] Worker → `FixProposal` with required rollback and evidence references
- [ ] **Iteration cap enforced in the graph runtime**, not the prompt (risk row 3)
- [ ] Integration test: no path from `worker` to `executor` bypasses `validator` and `approval`

**Done when:** a real alarm produces a validated-or-rejected proposal end to end, minus execution.

---

## Sprint 5 — Approval + Executor + audit *(Nov 17 – Nov 30)*

- [ ] Approval surface (per ADR-0005) with fast-path and strict paths
- [ ] `ApprovalRecord`: who, when, which proposal hash
- [ ] Executor: dispatch table → boto3, no LLM
- [ ] Executor re-verifies the approval record; a mismatch is logged as a **security event**
- [ ] Audit log covering the full run (per ADR-0006)
- [ ] End-to-end: chaos #1 → alarm → triage → worker → validator → approval → rollback executed

**Done when:** success criterion 1 is met — the full pipeline runs on a real self-triggered incident.

---

## Sprint 6 — Demo, measurement, writeup *(Dec 1 – Dec 14)*

- [ ] **Time-to-diagnosis measured** from alarm to validated proposal, framed against the ~45-min baseline
- [ ] **Recorded demo: the Validator blocks an unsafe fix** — the centerpiece, not a footnote
- [ ] Recorded demo: chaos #3 injection attempt fails to influence the proposed action
- [ ] Audit trail rendered presentably
- [ ] Architecture diagram, README polish, repo made public
- [ ] Retro: which risk rows held, which needed tuning, what the false-positive rate actually was

**Done when:** all four v1 success criteria are checked off in the README.

---

## Buffer and cut-lines

One semester, part-time, with an AWS-dependent middle. If time compresses, cut in this order:

1. **Chaos #2 (OOM)** — chaos #1 and #3 already cover rollback and injection, the two demo-critical stories
2. **A polished approval UI** — a CLI approval is sufficient to prove the gate exists
3. **Terraform module structure** — flat config in `envs/sandbox` is acceptable for v1

**Never cut:** the Validator's rules, the injection test, the IAM scoping, or the blocked-fix demo.
Those four *are* the project. A working pipeline with a weak gate is the exact failure mode this
project exists to argue against.

---

## Tracking

Sprint checkboxes here are the source of truth. GitHub Issues use the templates in
[`.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/); anything touching a risk register row
carries the `risk-row-N` label so the mapping from register to code stays visible.
