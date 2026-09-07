# Ops Sentinel — Business case

## Problem

On-call engineers lose roughly the first 45 minutes of every incident to investigation — correlating logs, checking recent deploys, digging through metrics — before they can even begin deciding what to do. Separately, agentic tooling used in real SDLC work today commonly fails not by being obviously wrong, but by lacking self-validation and guardrails: it produces plausible-looking output with no signal about whether it's safe to trust. Industry research backs this as a structural, not isolated, problem — one study found 80% of organizations reported their AI agents had already acted beyond intended scope, and a survey of 286 organizations found nearly a third are already running agents in production while governance lags behind.

## Solution

**Ops Sentinel** is a multi-agent AI-SRE system that compresses the investigation phase of an incident and hands the on-call engineer a validated, ready-to-review fix instead of a blank slate:

- **Triage agent** — classifies incoming alert severity/type
- **Worker agent** — investigates (logs, metrics, recent deploys) and proposes a fix
- **Validator** — the core differentiator: checks the proposal against explicit, inspectable rules (blast radius, cost ceiling, rollback plan, confidence) before a human ever sees it
- **Human approval gate** — nothing executes without sign-off
- **Executor** — deterministic, no LLM, minimum-privilege IAM, runs only after approval

## Where it fits

Ops Sentinel doesn't replace existing monitoring (Datadog, Snyk) or any SDLC phase — it lives inside **Operate & monitor**, consuming existing alerts and closing the loop back into **Deploy** through the same approval-gated path every other change goes through.

## Why this differentiator over existing AIOps features

Most auto-remediation features are black boxes: a rules engine or an LLM suggestion with no inspectable safety layer. Ops Sentinel's Validator is an explicit, readable gate between "AI proposed something" and "something executes" — a governance layer, not just a faster response time.

## Risk register (summary)

| Risk | Hard rule | Developer gap it closes |
|---|---|---|
| Blast radius too broad | Validator requires a single named resource ID; wildcards always route to strict approval | No consistent second check exists today beyond a tired on-call engineer |
| Secrets/PII in a proposal | Validator scrubs/rejects proposals matching credential or PII patterns | No automated gate exists before a human reads raw log content |
| Runaway LLM cost | Hard iteration cap; fail loudly on breach | Nothing currently stops an agent run from silently spinning |
| Runaway infra cost | Fixed max-instance/spend-delta ceiling, enforced outside the LLM | Manual fixes are bounded by judgment in the moment; automation needs that made explicit |
| Prompt injection via logs | Ingested content always treated as data, never instructions; tested explicitly in the demo | A known, cited industry failure mode, rarely tested in student/portfolio agent projects |
| Over-privileged execution | Executor's IAM role scoped to its exact known action set | Most ad hoc agent tooling grants broad access "just in case" |
| Fix causes a new incident | Validator rejects any proposal with no rollback plan attached | Manual fixes often skip a documented rollback too — this makes the omission blocking, not silent |
| Trust erosion (too strict or too loose) | Explicit, documented false-positive tolerance as a designed trade-off | No prior system exists to (dis)trust — this risk is new, introduced by automation itself |

*(Full register with detection signals and residual risk: see `ops-sentinel-risk-register.md`.)*

## Success criteria (v1)

- Full pipeline runs end-to-end on a real, self-triggered incident in a personal AWS sandbox
- **Time-to-diagnosis** measured from alert to validated fix proposal, framed against the ~45-minute manual baseline
- A recorded demo where the Validator blocks an unsafe fix
- A presentable audit trail of every decision

## Scope

**In (v1):** single sandbox app, Triage → Worker → Validator → human approval → Executor, one blocked-fix demo, audit log
**Out (v1):** auto-execution without approval, multiple parallel workers, production deployment, Spring Boot approval API (deferred to v2)

## Status

Portfolio project (Solutions Architect / AI Engineer track), one semester timeline, part-time alongside coursework and work. Business case is the first artifact; sandbox app selection and demo incident design are next.
