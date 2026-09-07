# ADR-0003 — No LLM in the Validator

**Status:** Accepted · **Date:** 2026-09-07

## Context
The Validator decides whether a proposed fix is safe enough for a human to review. An LLM-judged
validator would be more flexible and handle cases no rule anticipated.

## Decision
The Validator contains no model calls. Every rule is deterministic Python: readable, unit-tested,
and enforced outside the Worker's control.

## Rationale
- A validator judged by an LLM inherits every failure mode it exists to catch — including prompt
  injection from the very log content it's inspecting (risk row 5). It would be theater.
- Determinism makes the gate defensible. "Rejected: no rollback plan attached" is inspectable and
  arguable. "The model scored this 0.4" is not.
- This is the differentiator. Most auto-remediation is a black box; an explicit, readable gate is
  the entire argument of the project.

## Consequences
- The Validator will reject some safe proposals that a more flexible judge would pass. This is the
  accepted trade-off, tracked explicitly as risk row 8 with a documented false-positive tolerance
  chosen before the demo, not justified after it.
- New action types require new rules. That's the intent: adding capability should require a
  deliberate safety review.
