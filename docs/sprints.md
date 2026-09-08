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
- [x] **Decide [#1 approval surface](https://github.com/hippync/ops-sentinel/issues/1)** —
      [ADR-0005](adr/0005-approval-surface.md): Slack, which resolves that half of ADR-0002's
      conditionality in its favour
- [ ] **Decide [ADR-0004 runtime](adr/0004-pipeline-runtime.md)** — now the *only* remaining
      blocker on ADR-0002; orchestration code should not be written before it lands
- [ ] Document the false-positive tolerance (risk row 8) — decided now, not justified later
- [ ] **~20 evaluation scenarios** as recorded alarm payloads, each with its one critical
      decision **labeled in a commit that precedes any extraction rule** ([ADR-0009](adr/0009-extraction-evaluation-harness.md)).
      Same fixtures `replay-alarm.sh` needs; the labels are what make the miss rate mean
      anything, and the commit order is the only evidence they weren't fitted to the rules
- [ ] Pick the two numbers ADR-0009 leaves open — the miss rate that gates building the LLM
      classifier, and the operational form of the kill criterion. Both chosen **before** the
      first measurement, in the same discipline risk row 8 already uses

**Done when:** every rule rejects its violation and passes the clean case, a recorded alarm
payload can be replayed from the command line, and the scenario labels are committed.

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
- [ ] **OpenTelemetry instrumentation** on the graph, Triage and Worker, using the GenAI
      semantic conventions ([ADR-0008](adr/0008-decision-point-extraction.md) component 1).
      Lands here because this is when spans first exist, and it pays for itself in debugging
      whether or not the extraction layer survives its kill criterion
- [ ] Record the ~20 scenarios' span sets to fixture files — ADR-0009 measures extraction over
      fixed spans so the published number carries no trajectory variance

**Done when:** a replayed alarm produces a validated-or-rejected proposal end to end, and
emits a recorded span set for each evaluation scenario.

---

## Sprint 3 — Approval + Executor + audit, still no AWS *(Oct 20 – Nov 2)*

- [ ] Slack approval app per [ADR-0005](adr/0005-approval-surface.md), with fast-path and strict
      paths — request-signature verification and approval bound to `proposal_hash`, not a
      message ID. CLI approval retained as the dev/test/harness path
- [ ] `ApprovalRecord`: who, when, which proposal hash
- [ ] Executor with a **fake AWS backend** — dispatch table, no LLM
- [ ] Executor re-verifies the approval record; a mismatch is a logged **security event**
- [ ] Decision register per [ADR-0006](adr/0006-audit-log-store.md), covering the full run and
      written through `audit/redaction.py` — local JSON-lines sink here, DynamoDB in Sprint 5
- [ ] **Demo-able milestone: the Validator blocks an unsafe fix, end to end, on a laptop**

### The extraction layer's first real test

- [ ] `DecisionPoint` / `DecisionRegisterEntry` contracts
- [ ] **Rule-based extractor** — the five families in [ADR-0008](adr/0008-decision-point-extraction.md).
      Deterministic, cheap, and written in the Validator's idiom
- [ ] Renderer: decision cards as Block Kit sections above the buttons, fast path included
- [ ] Integration test: `extract` has **no outgoing edge to `executor`** — the topological form
      of "the extractor is not a gate"
- [ ] Harness runner over the recorded span sets; publish the first miss rate to a committed
      results file so it moves in diffs
- [ ] **Kill-criterion checkpoint at ~10 scenarios.** If the extractor consistently surfaces
      everything or nothing useful, drop the layer and keep the OTel work and the harness. The
      retro must distinguish *the hypothesis is wrong* from *this pipeline is too small to test
      it* — they have opposite implications

**Done when:** success criteria 3 and 4 are met without a single AWS resource existing, and the
extraction layer has either a measured miss rate or a recorded kill decision. From here on,
everything else is upside.

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
- [ ] DynamoDB decision register table ([ADR-0006](adr/0006-audit-log-store.md)) — PITR on, no
      TTL, conditional writes, and **outside the `terraform destroy` cycle**: the demo's trail
      is the artifact and must survive teardown
- [ ] Apply the Executor IAM role from the reviewed policy; nothing broader. `dynamodb:PutItem`
      goes to the **pipeline's** task role — adding it to the Executor policy would fail
      `check_iam_scope.py`, correctly
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
- [ ] Decision register rendered presentably (redacted)
- [ ] **LLM classifier ([ADR-0008](adr/0008-decision-point-extraction.md) component 4) — only if
      Sprint 3's rules-only miss rate breached the threshold committed to in Sprint 1.** Output
      marked `surfaced_by: classifier` and visually distinguished from the deterministic points
- [ ] **Publish the final miss rate and the miss-rate/points-surfaced curve**, with ADR-0009's
      open caveats stated alongside it — single labeler, recorded rather than live trajectories,
      ~7 scenarios per incident type. A number without its caveats is the failure mode this
      project argues against
- [ ] Architecture diagram, README polish, repo made public
- [ ] Retro: which risk rows held, which needed tuning, the realised false-positive rate, and
      what the extraction result was — including whether the taxonomy question is any less open

---

## Buffer and cut-lines

Cut in this order:

1. **Sprint 5 in full** — the pipeline is already demoable from Sprint 3. This is now a
   cut-line rather than a load-bearing dependency, which is the point of the resequence
2. **The LLM classifier** (ADR-0008 component 4) — it is already conditional on the rules-only
   miss rate, so cutting it just resolves that condition early. The rules-only number is still
   a publishable result
3. **Chaos #2 (OOM)** — #1 and #3 cover rollback and injection, the two demo-critical stories
4. **A polished approval UI** — the CLI approval path proves the gate exists, and ADR-0005 keeps
   it as a first-class path rather than a fallback

**Never cut:** the Validator's rules, the injection test, the IAM scoping and its drift
check, or the blocked-fix demo. Those four *are* the project. A working pipeline with a
weak gate is the exact failure mode this project exists to argue against.

**Also never cut, and for the same reason:** the OTel instrumentation and the evaluation harness.
If the extraction layer is killed, those two are what make the kill a *result* rather than an
abandonment — and both are useful to Ops Sentinel on their own. Shipping decision cards with no
measured miss rate is not a reduced version of this work; it is the version this project exists
to argue against.

---

## Tracking

Sprint checkboxes here are the source of truth. Open decisions are issues labelled
`decision`; anything touching a risk register row carries `risk-row-N` so the mapping from
register to code stays visible. Commits are per-module from Sprint 1 on — on a portfolio
repo the history is part of the artifact.
