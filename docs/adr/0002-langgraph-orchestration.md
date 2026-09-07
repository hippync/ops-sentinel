# ADR-0002 — LangGraph for orchestration

**Status:** Accepted · **Date:** 2026-09-07 · **Revised:** 2026-09-07 after review

**Depends on:** [ADR-0004](0004-pipeline-runtime.md) (runtime) and
[ADR-0005](0005-approval-surface.md) (approval surface). See "Conditionality" below —
this decision is not fully safe until those land.

## Context

The pipeline is five nodes, near-linear, with one capped retry loop. On topology alone
that is a `match` statement and a `while` loop, and adding a framework to the critical
path would be unjustifiable. Options: plain Python, LangGraph, Step Functions, or a
role-based agent framework.

## Decision

LangGraph, with pipeline state as an explicit typed object.

## Rationale

**The load-bearing reason is the approval gate, not the topology.** The pipeline
suspends for a human — potentially for hours, plausibly across process death — and then
resumes mid-flow with its state intact. That is durable suspend/resume, which is what
`interrupt()` plus a checkpointer provides and what a `while` loop does not. The hard
part of this graph is the pause, not the branching.

Two supporting reasons, neither sufficient alone:

- Graph topology enforces the safety invariant structurally: there is no edge from
  `worker` to `executor`. That is a property of the compiled graph, asserted in a test,
  rather than a convention someone can violate later.
- The iteration cap lives in the graph runtime, outside the Worker's own control, as
  risk row 3 requires.

**A reason that was previously overstated and is now withdrawn:** the earlier version of
this ADR claimed "the audit trail falls out of the graph rather than being bolted on."
It does not. `AuditRecord` is a domain object assembled by hand either way. What the
graph actually gives is per-node state that is convenient to attach to that record —
true, and smaller.

**A reason that was previously unstated:** LangGraph is a hiring-signal technology, and
this is a portfolio project. That is a legitimate input. Leaving it out and dressing the
decision as pure architecture is what makes an ADR read as post-hoc rationalization.

## Conditionality

If [ADR-0005](0005-approval-surface.md) resolves to an in-process CLI approval, the
durable-suspend argument evaporates and this decision rests only on the two supporting
reasons — which may not clear the bar for a framework dependency. If
[ADR-0004](0004-pipeline-runtime.md) resolves to Step Functions, there are two
orchestrators and LangGraph collapses to a node body.

**Therefore: 0004 and 0005 are decided before any orchestration code is written.** The
original sequencing — accepting the orchestration library before the runtime it runs on —
was backwards, and this note records the correction rather than hiding it.

## Consequences

- A framework dependency in the critical path, version-pinned with an upper bound
  because LangGraph 0.x breaks between minors and the demo date is fixed.
- Mitigated: the Validator and Executor — the two components that carry the safety
  argument — are plain Python and fully testable without the graph.
- Role-based frameworks (CrewAI and similar) were rejected outright: they optimize for
  autonomous agent collaboration, which is the opposite of this project's thesis.
