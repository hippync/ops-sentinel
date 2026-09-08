# ADR-0005 — Approval surface: Slack

**Status:** Accepted · **Date:** 2026-09-08 · **Resolves:** [issue #1](https://github.com/hippync/ops-sentinel/issues/1)

**Unblocks half of [ADR-0002](0002-langgraph-orchestration.md).** [ADR-0004](0004-pipeline-runtime.md)
is still Proposed and still blocks it — see "What this does not decide."

## Context

The approval gate needs a human surface that captures who approved, when, and which exact
`proposal_hash`, and that distinguishes the fast path from strict review. Three candidates were
carried in issue #1: a CLI prompt, a Slack app, or a minimal web page. The Spring Boot approval
API was explicitly deferred out of v1.

This was never only a UI choice. It is the input to ADR-0002: that ADR's load-bearing argument
for LangGraph is durable suspend/resume across an approval that may take hours and span process
death. An in-process CLI prompt does not produce that requirement, and the framework dependency
would then rest on two weaker supporting reasons.

[ADR-0008](0008-decision-point-extraction.md) added a second requirement after issue #1 was
opened: the surface must render 3–5 decision points above the buttons, not just a proposal and
an approve/reject pair.

## Considered options

| Option | Durable pause is real | Renders decision points | Cost |
|---|---|---|---|
| CLI prompt | No — in-process, dies with the process | Poorly; a terminal is not a review surface | Trivial |
| **Slack app** | **Yes** — genuinely out-of-process and asynchronous | Block Kit carries structured cards natively | An inbound webhook, and the security work that implies |
| Minimal web page | Yes | Yes, with full control | Hosting, auth, and a UI to build and maintain |

## Decision

A Slack app. Approval is an interactive message; the decision-point cards from ADR-0008 render
as Block Kit sections above the approve/reject actions.

**The CLI approval is retained** as the development, test, and evaluation-harness path — not as
a fallback that quietly becomes the real one. `docs/sprints.md` lists a polished approval UI as
cut-line #3 on the grounds that "a CLI approval proves the gate exists"; that remains true, and
the CLI is what [ADR-0009](0009-extraction-evaluation-harness.md)'s harness drives, because a
harness that needs a Slack workspace is not reproducible by a reader.

## Rationale

- **It makes the durable-suspend requirement real rather than hypothetical.** The pipeline
  suspends, the process may die, an engineer approves ninety minutes later from a phone, and the
  run resumes with its state intact. That is the requirement ADR-0002 was accepted against.
- **It is where on-call already is.** An incident response surface that requires opening a new
  place to look during an incident is a surface people route around, which is risk row 8's
  failure mode in a different costume.
- **Block Kit is a structured rendering target.** ADR-0008's cards are typed objects with
  fields; Slack renders them without a UI to build. This is the single largest reason to prefer
  Slack over a web page given a one-semester budget.

## Consequences

**Negative, and load-bearing:**

- **The interaction endpoint is a new inbound attack surface** — a publicly reachable URL that
  causes infrastructure changes when it receives the right payload. Two controls are mandatory,
  not optional hardening:
  1. Verify Slack's request signature (`X-Slack-Signature` / `X-Slack-Request-Timestamp`) on
     every interaction payload, with the timestamp window enforced to blunt replay.
  2. **Bind the approval to `proposal_hash`, never to a message or callback ID.** The
     `ApprovalRecord` already carries `proposal_hash`, and the Executor already re-verifies it.
     A forged or replayed interaction payload must therefore fail the Executor's existing check
     rather than needing a new one — this reuses the trust boundary the architecture already
     asserts instead of adding a parallel one.
- **Slack identity is not the approver's identity.** The `ApprovalRecord.approver` field must
  record a resolved, stable user ID, and the mapping from Slack user to a named human is part of
  the audit trail's meaning. A display name is not an identity.
- **The pipeline now depends on a third-party service** in the approval path. Fail-closed
  applies: if Slack is unreachable, the run stays suspended and pages through the existing path.
  The worst outcome remains the status quo — a human investigating from scratch.
- Workspace setup (app manifest, signing secret, request URL) is real work that is not
  interesting, and it needs a publicly routable endpoint before Sprint 5's infrastructure exists.
  Sprint 3 uses a tunnel for development; the endpoint moves behind the ALB in Sprint 5.

**Positive:**

- ADR-0002's conditionality is half-resolved in the direction that keeps the decision sound.
- The demo is more legible: an approval arriving in Slack with its decision points attached is a
  better recorded artifact than a terminal prompt.

## What this does not decide

[ADR-0004](0004-pipeline-runtime.md) — where the pipeline runs — remains Proposed, and still
blocks ADR-0002. If it resolves to Step Functions, AWS provides the durable pause and LangGraph
collapses to a node body regardless of what this ADR chose. `docs/sprints.md` ties the two
decisions together in Sprint 1; only one of them is made here.
