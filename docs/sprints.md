# Ops Sentinel — Delivery plan

**Timeline:** one semester, part-time alongside coursework and work
**Cadence:** 2-week sprints · **Capacity assumption:** ~8–10 focused hours per sprint week

> **Resequenced 2026-09-07 after review.** The original plan spent Sprints 2 and 3 — four
> weeks, a third of the semester — on the Java app and AWS wiring before the pipeline
> existed end to end. AWS wiring is the classic semester-eater, and it sat *upstream* of
> the project's actual deliverable.
>
> **The pipeline is now built against recorded alarm payloads and a fake executor first.**
> Sprints 0 → 1 → 2 → 3 produce a complete, tested, demoable system with **zero AWS spend**.
> Sprints 4 and 5 then make it real. Infrastructure became an *upgrade* rather than a
> dependency that can sink the project — which is what the cut-line list already implied:
> **infrastructure is cuttable, the gate is not.**

**Sequencing principle:** the Validator is the portfolio piece, so it is built and tested
before the Worker that feeds it. A Validator with hand-written fixtures is demonstrable on
its own; a Worker with nothing checking it is not.

---

## Sprint 0 — Foundation *(Sep 8 – Sep 21)* — complete

- [x] Business case, risk register, sandbox app spec
- [x] Repo scaffold, README, architecture doc
- [x] Pydantic contracts: `Incident`, `FixProposal`, `Verdict`, `ApprovalRecord`, `AuditRecord`
- [x] `proposal_hash` computed, not settable — the Executor's check is real
- [x] Typed action payloads (discriminated union per `ActionType`)
- [x] ADR-0001 monorepo · ADR-0002 LangGraph · ADR-0003 no-LLM Validator
- [x] **ADR-0007: verified that risk row 4 cannot be enforced in IAM** — no condition key
      exists for `desiredCount` on `ecs:UpdateService`
- [x] Executor minimum-privilege IAM policy + `scripts/check_iam_scope.py` drift check in CI
- [x] CI: path-filtered pytest/ruff/mypy, Maven verify, IAM drift check
- [ ] **Answer the pre-mortem question** from the risk register: if every check failed at
      once, is the worst outcome bounded by IAM scoping alone? ADR-0007 changed the inputs
      to this question — row 4 is now *not* IAM-bounded, so answer it again with that known

**Done when:** the pre-mortem has a documented answer under ADR-0007's revised assumptions.

---

## Sprint 1 — The Validator + the replay harness *(Sep 22 – Oct 5)*

The differentiator, plus the thing that makes every later sprint independent of AWS.

- [x] `rollback.py` + tests — risk row 7
- [ ] `blast_radius.py` + tests — risk row 1 (runs over the rollback action too)
- [ ] `secrets.py` + tests — risk row 2 (rejects; redaction lives in `audit/redaction.py`)
- [ ] `cost_ceiling.py` + tests — risk row 4
- [ ] `injection.py` + tests — risk row 5, including the playbook constraint
- [ ] `scoring.py` — severity × confidence × reversibility → fast-path or strict
- [ ] `audit/redaction.py` — `Evidence.excerpt` reaches the audit log even on rejection
- [ ] **`scripts/replay-alarm.sh` + recorded alarm payload fixtures** *(pulled forward from
      Sprint 4)* — the whole pipeline can now be developed and demoed without AWS
- [ ] **Decide [#1 approval surface](https://github.com/hippync/ops-sentinel/issues/1) and
      [ADR-0004 runtime](adr/0004-pipeline-runtime.md)** — both block ADR-0002, and
      orchestration code should not be written before they land
- [ ] Document the false-positive tolerance (risk row 8) — decided now, not justified later

**Done when:** every rule rejects its violation and passes the clean case, and a recorded
alarm payload can be replayed from the command line.

---

## Sprint 2 — Triage + Worker, against recorded payloads *(Oct 6 – Oct 19)*

No AWS. No Java. Recorded payloads and read-only tool stubs only.

- [ ] LangGraph state object and graph topology
- [ ] Triage: alarm → `Incident`; `unknown` routes straight to a human
- [ ] Worker read-only tool interfaces + recorded-response fakes
- [ ] Worker → `FixProposal` with required rollback and evidence references
- [ ] **Iteration cap enforced in the graph runtime**, not the prompt (risk row 3)
- [ ] **Integration test asserting graph topology**: no path from `worker` to `executor`
      bypasses `validator` and `approval`. This is the single most load-bearing claim in
      the architecture and nothing currently enforces it

**Done when:** a replayed alarm produces a validated-or-rejected proposal end to end.

---

## Sprint 3 — Approval + Executor + audit, still no AWS *(Oct 20 – Nov 2)*

- [ ] Approval surface per issue #1, with fast-path and strict paths
- [ ] `ApprovalRecord`: who, when, which proposal hash
- [ ] Executor with a **fake AWS backend** — dispatch table, no LLM
- [ ] Executor re-verifies the approval record; a mismatch is a logged **security event**
- [ ] Audit log covering the full run, rendered through `audit/redaction.py`
- [ ] **Demo-able milestone: the Validator blocks an unsafe fix, end to end, on a laptop**

**Done when:** success criteria 3 and 4 are met without a single AWS resource existing.
From here on, everything else is upside.

---

## Sprint 4 — Sandbox app *(Nov 3 – Nov 16)*

Something real to break.

- [ ] Spring Boot 3 / Java 21 Orders API — `GET /orders`, `POST /orders`, `GET /orders/{id}`
- [ ] Spring Data JPA + Postgres, Flyway migration
- [x] Chaos config fails closed — blank key with chaos enabled refuses to boot
- [ ] Admin API key filter; `/admin/**` enforced in-app as well as at the listener
- [ ] Chaos #2 `POST /admin/chaos/leak` — static list appended until genuine OOM
- [ ] Chaos #3 `POST /admin/chaos/log-injection` — crafted ERROR line
- [ ] Dockerfile + local `docker-compose` for app + Postgres

---

## Sprint 5 — Infrastructure, and make the demo real *(Nov 17 – Nov 30)*

- [ ] Terraform: VPC, ECS Fargate, RDS, ALB (public listener = Orders only)
- [ ] **Fargate tasks in public subnets with tight security groups — no NAT gateway** (~$32/mo)
- [ ] ECS Service Auto Scaling **max capacity** — row 4's infrastructure enforcement point
- [ ] Internal listener for chaos via SSM port-forward, not the public route
- [ ] CloudWatch alarms (5xx rate, memory) → EventBridge → pipeline
- [ ] Apply the Executor IAM role from the reviewed policy; nothing broader
- [ ] Chaos #1: deploy a deliberately broken task-definition revision, confirm the alarm fires
- [ ] Swap the fake executor for boto3; re-run the Sprint 3 demo against real infrastructure
- [ ] `terraform destroy` in the demo runbook

**Done when:** success criterion 1 is met — the full pipeline runs on a real self-triggered
incident. **If this sprint slips entirely, the project still ships** on Sprint 3's evidence.

---

## Sprint 6 — Demo, measurement, writeup *(Dec 1 – Dec 14)*

- [ ] **Time the author solving the same sandbox incident manually** — the honest baseline
- [ ] Measure time-to-validated-proposal against it; keep the industry ~45 min as motivation only
- [ ] **Recorded demo: the Validator blocks an unsafe fix** — the centerpiece
- [ ] Recorded demo: chaos #3 injection fails to influence the proposed action
- [ ] Audit trail rendered presentably (redacted)
- [ ] Architecture diagram, README polish, repo made public
- [ ] Retro: which risk rows held, which needed tuning, the realised false-positive rate

---

## Buffer and cut-lines

Cut in this order:

1. **Sprint 5 in full** — the pipeline is already demoable from Sprint 3. This is now a
   cut-line rather than a load-bearing dependency, which is the point of the resequence
2. **Chaos #2 (OOM)** — #1 and #3 cover rollback and injection, the two demo-critical stories
3. **A polished approval UI** — a CLI approval proves the gate exists

**Never cut:** the Validator's rules, the injection test, the IAM scoping and its drift
check, or the blocked-fix demo. Those four *are* the project. A working pipeline with a
weak gate is the exact failure mode this project exists to argue against.

---

## Tracking

Sprint checkboxes here are the source of truth. Open decisions are issues labelled
`decision`; anything touching a risk register row carries `risk-row-N` so the mapping from
register to code stays visible. Commits are per-module from Sprint 1 on — on a portfolio
repo the history is part of the artifact.
