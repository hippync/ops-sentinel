---
description: Draft an ADR in this repo's house format
argument-hint: <the decision to be made>
---

Draft an ADR for: **$1**

Read two or three existing ADRs first — `docs/adr/0007-row-4-cannot-live-in-iam.md` and
`docs/adr/0009-extraction-evaluation-harness.md` are the strongest examples of the house voice.
Match their structure and their standard of honesty. Number the new one after the highest existing
ADR in `docs/adr/`.

## Structure

```
# ADR-NNNN — <title>

**Status:** Proposed · **Date:** <today>

## Context and problem statement
## Decision drivers
## Considered options        <- each with why it was REJECTED, not just what it was
## Decision
## Consequences              <- including what this costs, not only what it buys
## Residual risk
```

## The standard this repo holds ADRs to

- **Every option gets a real rejection reason.** An ADR listing alternatives it never seriously
  considered is post-hoc rationalization, and the repo's own review already caught that once
  (ADR-0002).
- **Name what the decision costs.** ADR-0007 is the precedent: it establishes that a control
  *cannot* be enforced where the architecture claimed it would be. That is the most valuable ADR
  in the repo because it names a gap before a reviewer could.
- **Check the sequencing.** If this decision depends on an ADR that is not yet accepted, say so
  explicitly and state what changes if that one lands differently.
- **No number you have not measured.** Targets and protocols are fine, labelled as such.
- **Verify claims about external systems.** If the ADR asserts something about AWS, IAM, or a
  library, check it and cite the source — do not assert it from memory. ADR-0007 exists because
  someone actually checked whether the condition key existed.

## Two hard constraints

**Leave `Status: Proposed`.** You do not accept ADRs. Accepting one is the author's decision and
the date on it should be the date they made it.

**Do not choose the numbers.** If the decision needs a threshold, a rate, or a limit, present the
trade-offs and leave the value as `<TBD — author>`. Risk row 8 and ADR-0009 both require these
chosen by a human, before measurement.

When the draft is done, say which existing ADRs it supersedes, contradicts, or depends on, and
whether `docs/sprints.md` or the risk register need a corresponding change.
