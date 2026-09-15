# ADR-0007 — Risk row 4's cost ceiling cannot be enforced in IAM

**Status:** Accepted · **Date:** 2026-09-07 · **Revised:** 2026-09-15

## Context

The architecture makes a strong claim: *"the last line of defense is IAM, not code —
even a fully manipulated agent cannot act outside its known action set."* The draft
Executor policy carried a TODO to bound `desiredCount` changes in IAM, so that risk
row 4's cost ceiling would not depend on the Validator being correct.

That TODO is not achievable. Verified against the AWS Service Authorization Reference
and the ECS roadmap:

- There is **no IAM condition key** constraining the `desiredCount` parameter of
  `ecs:UpdateService`.
- `UpdateService` does accept 13 condition keys for other parameters — among them
  `ecs:task-definition`, `ecs:subnet`, `ecs:auto-assign-public-ip` and
  `ecs:enable-execute-command`. None constrains the count.
- A request for exactly this capability is open and unimplemented:
  [aws/containers-roadmap#2527](https://github.com/aws/containers-roadmap/issues/2527),
  "Fine-grained IAM permission control for ECS UpdateService API."

A second, related finding fell out of the same check: `ecs:UpdateService` is a **single
IAM action that grants all three** of our `ActionType`s. IAM cannot tell a rollback from
a restart from a scale.

## Decision

1. **State the exception rather than gloss it.** The "IAM is the last line of defense"
   claim now names risk row 4 as its exception, everywhere it appears.
2. **Check the ceiling twice in code, and name the infrastructure backstop for what it
   is.** No single enforcement point is both authoritative and outside the LLM's control:
   - the Validator's `cost_ceiling` rule rejects the proposal;
   - the Executor re-checks before the boto3 call;
   - **ECS Service Auto Scaling max capacity** is a lagging correction, not a block. It
     does not stop `UpdateService` setting a count above it, and pulls the count back
     down only when a scale-in alarm fires. `application-autoscaling:*` is *not* granted
     to the Executor, so the agent cannot move the bounds it is corrected back to.
3. **Track the coarseness of row 6 explicitly.** `infra/policies/action-mapping.json`
   records that one IAM action covers three ActionTypes, and
   `scripts/check_iam_scope.py` fails CI if the policy and the enum drift apart.

Pinning the condition keys that *do* exist is a separate decision:
[ADR-0010](0010-pin-updateservice-condition-keys.md), Proposed.

## Consequences

- Row 6's guarantee is genuinely weaker than "one IAM action per ActionType," and the
  docs now say so. A reviewer who finds this unaided discounts everything else in the
  register; a project that names its own exception reads as rigorous.
- The Validator matters *more* than the original framing implied: for row 4, it and the
  Executor's re-check are the only automated controls that act before the call, and both
  are code. Neither is built yet.
- **Spend is not bounded by IAM or by this repo's infrastructure** once every check has
  failed. The pre-mortem answer in `docs/ops-sentinel-risk-register.md` records this and
  leaves the choice of an account-level bound open.
- `set_desired_count` writes a count that Service Auto Scaling may later overwrite: a
  count above maximum capacity is pulled down on the next scale-in, and one below minimum
  capacity is raised on the next scale-out. The agent and the scaler act on the same
  number, and v1 does not resolve that tension.
- If AWS implements #2527, revisit: the ceiling should move into IAM and this ADR should
  be superseded.

## Revision — 2026-09-15

The original version of this ADR made two claims that were wrong. Both were found while
answering the risk register's pre-mortem question:

1. *"None [of the February 2025 condition keys] applies to `UpdateService`."* The
   Service Authorization Reference lists 13 condition keys for `UpdateService`, including
   `ecs:subnet` and `ecs:auto-assign-public-ip` from the February 2025 set. The core
   finding — no key for `desiredCount` — stands.
2. *"ECS Service Auto Scaling max capacity rejects the effect."* It does not. The ECS
   documentation states that a desired count set above maximum capacity is adjusted only
   when an alarm initiates a scale-in activity, and that a scale-out activity does not
   adjust it.

The original also said `UpdateService` lets the service point at "any task-definition
revision in the account." That was a gap in the policy, not a limit of IAM;
[ADR-0010](0010-pin-updateservice-condition-keys.md) proposes narrowing it to one family.

## Sources

- [Actions, resources, and condition keys for Amazon ECS](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelasticcontainerservice.html)
- [ECS service reference (machine-readable)](https://servicereference.us-east-1.amazonaws.com/v1/ecs/ecs.json) — the form checked for the 2026-09-15 revision
- [Automatically scale your Amazon ECS service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html) — desired count outside minimum and maximum capacity
- [Amazon ECS adds support for additional IAM condition keys (Feb 2025)](https://aws.amazon.com/about-aws/whats-new/2025/02/amazon-ecs-additional-iam-condition-keys)
- [aws/containers-roadmap#2527 — fine-grained IAM for UpdateService](https://github.com/aws/containers-roadmap/issues/2527)
