# ADR-0002 — LangGraph for orchestration

**Status:** Accepted · **Date:** 2026-09-07

## Context
The pipeline is a multi-stage flow with conditional routing, a capped retry loop, and a hard
requirement that every decision be auditable. Options: plain Python functions, LangGraph, Step
Functions, or a framework like CrewAI.

## Decision
LangGraph, with pipeline state as an explicit typed object.

## Rationale
- The state machine is inspectable. Transitions *are* the audit trail, rather than something
  reconstructed from logs afterward — and the audit trail is a v1 deliverable.
- Graph topology enforces the safety invariant structurally: there is no edge from `worker` to
  `executor`. That's a property of the graph, not a convention someone might violate later.
- The iteration cap lives in the graph runtime — outside the Worker's own control, as risk row 3
  requires. A cap the agent enforces on itself isn't a cap.
- Continuity with `jobs-radar-qc`, whose LangGraph layer precedes this build.

## Consequences
- A framework dependency in the critical path. Mitigated because the Validator and Executor — the
  two components that actually matter for safety — are plain Python and testable without the graph.
- CrewAI and similar role-based frameworks were rejected: they optimize for autonomous agent
  collaboration, which is the opposite of this project's thesis.
