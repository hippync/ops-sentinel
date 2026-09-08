# ADR-0006 — Audit log store: DynamoDB, as a decision register

**Status:** Accepted · **Date:** 2026-09-08 · **Resolves:** [issue #2](https://github.com/hippync/ops-sentinel/issues/2)

## Context

The audit trail is a v1 success criterion shown in the demo, not a debugging aid. Issue #2
carried three candidates — CloudWatch Logs Insights, S3 + Athena, or Postgres — and named the
deciding factor: *how presentable a full run's trail is to a reviewer, not query power.*

**DynamoDB was not among those three.** It is chosen here because
[ADR-0008](0008-decision-point-extraction.md) changed what the store has to hold, and this ADR
states that plainly rather than presenting DynamoDB as if it had been on the list all along.

**What changed.** Before ADR-0008, a run produced one `AuditRecord` — a narrative: alarm,
classification, iterations, verdict, approval, result. Read start to finish, once, by a human
looking at a demo. After ADR-0008, a run also produces a set of `DecisionPoint` records, each
one independently addressable: *this* decision, in *this* run, on *this* proposal, surfaced by
*this* rule, with the approver's action attached. The audit log stops being an approval history
and becomes a **decision register**. That is a keyed-lookup access pattern over small structured
items, which is a different shape from "search a log" or "scan Parquet in S3."

## Considered options

| Option | Fits a narrative trail | Fits a keyed decision register | Cost / effort |
|---|---|---|---|
| CloudWatch Logs Insights | Yes | Poorly — decision points become log lines to search for, not items to fetch | ~$0, already in the stack |
| S3 + Athena | Yes | Poorly — scan-oriented, minutes to query, awkward for single-item reads | Low $, real setup |
| Postgres | Yes | Yes | RDS already provisioned for the sandbox app — but couples the pipeline's audit trail to the app it is watching |
| **DynamoDB** | Yes | **Yes** — item-per-record, composite key, single-digit-ms reads | On-demand, negligible at demo volume |

Postgres is the closest runner-up and its rejection is a judgment call, not a slam dunk: an RDS
instance already exists in the Sprint 5 plan. It is rejected because that instance is the
sandbox app's database — the system Ops Sentinel *watches*. Putting the audit trail of an
incident into the database of the service having the incident is a coupling that fails at
exactly the wrong moment.

## Decision

A single DynamoDB table.

- **Partition key** `run_id` — every record for one pipeline run lives in one partition, so
  rendering a full trail is one `Query`.
- **Sort key** `record_type#id` — `INCIDENT`, `PROPOSAL#<proposal_hash>`,
  `VERDICT#<proposal_hash>`, `DECISION#<nn>`, `APPROVAL#<proposal_hash>`, `EXECUTION`.
  Prefix queries fetch just the decision points, or just the approval, without reading the run.
- **On-demand billing.** Demo volume is a few hundred items per semester.
- **Point-in-time recovery on. No TTL.** An audit record that expires is not an audit record,
  and the cost of retaining a few hundred small items indefinitely is zero.

**Every write goes through [`ops_sentinel.audit.redaction`](../../agents/src/ops_sentinel/audit/redaction.py).**
This is issue #2's stated constraint and it is not negotiable: `Evidence.excerpt` carries raw
ingested log content — where secrets and PII enter the pipeline — and it reaches the record
**even when the proposal is rejected**. The store is written by one function that redacts, never
by callers assembling items themselves.

**The table is written by the pipeline's task role, never the Executor's.**
[`scripts/check_iam_scope.py`](../../scripts/check_iam_scope.py) fails CI on any IAM action the
`ActionType` enum does not require, so adding `dynamodb:PutItem` to
`infra/policies/executor-policy.json` would break the build — correctly. Risk row 6's guarantee
is that the Executor cannot act outside its known action set; writing audit records is not in
that set and must not be added to it.

## Consequences

**Negative:**

- **Append-only is a convention here, not a property.** `PutItem` overwrites an existing item
  silently. Writes must use `ConditionExpression: attribute_not_exists(sk)` so a second write to
  the same key fails rather than rewriting history. This is the residual risk on this decision
  and it is stated rather than assumed away — an audit store that can be quietly edited is worth
  less than one that cannot.
- One more AWS service in the stack, and one more thing to `terraform destroy`. Unlike the rest
  of the sandbox it should **survive** teardown, since the demo's audit trail is the artifact —
  so the table lives outside the environment's destroy cycle and `infra/README.md` must say so.
- Local development and [ADR-0009](0009-extraction-evaluation-harness.md)'s harness need a store
  that is not AWS. Both write through the same redaction function to a local JSON-lines sink;
  the store is an interface with two implementations, and the fake one is what CI exercises.

**Positive:**

- Rendering a full run for the demo is one `Query` on `run_id`, in order.
- A decision point is individually addressable, which is what makes "the audit log is a decision
  register rather than an approval history" a structural claim instead of a rhetorical one.
- No schema migration as `DecisionPoint` gains fields over Sprints 3–6, which matters on a
  project where the shape of that record is explicitly still being learned.

## Open question

Whether the register should be queryable *across* runs — "show me every decision where the
approver overrode a surfaced alternative" — which is the question that makes the register
interesting beyond a single demo, and which this key design does not support without a GSI.
Deliberately not added now: it is speculative until ADR-0009 produces enough runs to ask it.
