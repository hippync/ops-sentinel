# ADR-0007 — Risk row 4's cost ceiling cannot be enforced in IAM

**Status:** Accepted · **Date:** 2026-09-07

## Context

The architecture makes a strong claim: *"the last line of defense is IAM, not code —
even a fully manipulated agent cannot act outside its known action set."* The draft
Executor policy carried a TODO to bound `desiredCount` changes in IAM, so that risk
row 4's cost ceiling would not depend on the Validator being correct.

That TODO is not achievable. Verified against the AWS Service Authorization Reference
and the ECS roadmap:

- There is **no IAM condition key** constraining the `desiredCount` parameter of
  `ecs:UpdateService`.
- The eight service-specific condition keys ECS added in February 2025 cover task CPU
  and memory, compute compatibility, container privileges, network configuration, and
  tag propagation. **None applies to `UpdateService`.**
- A request for exactly this capability is open and unimplemented:
  [aws/containers-roadmap#2527](https://github.com/aws/containers-roadmap/issues/2527),
  "Fine-grained IAM permission control for ECS UpdateService API."

A second, related finding fell out of the same check: `ecs:UpdateService` is a **single
IAM action that grants all three** of our `ActionType`s, plus the ability to point the
service at any task-definition revision in the account. IAM cannot tell a rollback from
a restart from a scale.

## Decision

1. **State the exception rather than gloss it.** The "IAM is the last line of defense"
   claim now names risk row 4 as its exception, everywhere it appears.
2. **Enforce the ceiling three times instead of once**, since no single enforcement
   point is both authoritative and outside the LLM's control:
   - the Validator's `cost_ceiling` rule rejects the proposal;
   - **ECS Service Auto Scaling max capacity** rejects the effect, in infrastructure,
     independent of any code in this repo. `application-autoscaling:*` is *not* granted
     to the Executor, so the agent cannot raise its own ceiling;
   - the Executor re-checks before the boto3 call.
3. **Track the coarseness of row 6 explicitly.** `infra/policies/action-mapping.json`
   records that one IAM action covers three ActionTypes, and
   `scripts/check_iam_scope.py` fails CI if the policy and the enum drift apart.

## Consequences

- Row 6's guarantee is genuinely weaker than "one IAM action per ActionType," and the
  docs now say so. A reviewer who finds this unaided discounts everything else in the
  register; a project that names its own exception reads as rigorous.
- The Validator matters *more* than the original framing implied, since for row 4 it is
  one of only two real controls rather than a redundant check on top of IAM.
- If AWS implements #2527, revisit: the ceiling should move into IAM and this ADR should
  be superseded.

## Sources

- [Actions, resources, and condition keys for Amazon ECS](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelasticcontainerservice.html)
- [Amazon ECS adds support for additional IAM condition keys (Feb 2025)](https://aws.amazon.com/about-aws/whats-new/2025/02/amazon-ecs-additional-iam-condition-keys)
- [aws/containers-roadmap#2527 — fine-grained IAM for UpdateService](https://github.com/aws/containers-roadmap/issues/2527)
