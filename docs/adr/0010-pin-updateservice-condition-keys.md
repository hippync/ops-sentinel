# ADR-0010 — Pin the `UpdateService` condition keys that exist

**Status:** Proposed · **Date:** 2026-09-15

**Depends on:** [ADR-0007](0007-row-4-cannot-live-in-iam.md), as revised on the same date.

## Context and problem statement

ADR-0007 established that no IAM condition key constrains `desiredCount` on
`ecs:UpdateService`. Its 2026-09-15 revision corrected a second claim: `UpdateService`
*does* accept condition keys for other parameters — 13 of them, per the AWS service
reference.

With none of them pinned, the Executor's `UpdateService` grant lets a fully manipulated
agent point the `orders-api` service at any task definition in the account, and so run it
under that task definition's task role. That is a gap in this repo's policy, not a limit of
IAM. The risk register's pre-mortem answer depends on closing it.

The question is which of the 13 keys to pin now, before any Terraform exists to give most
of them a value.

## Decision drivers

- **Row 6 is the guarantee meant to hold when code fails.** A key that could be pinned and
  is left open is privilege the Executor does not need.
- **Nothing may be pinned to a guessed value.** Subnet IDs, capacity providers and task
  sizes do not exist yet. A pin to an invented value either denies legitimate calls or reads
  as a control nobody checked.
- **A pin nobody guards will erode.** CI has to notice a pin being widened, not only removed.
- **IAM evaluation claims must be verified.** Where behaviour is read from documentation
  rather than observed, it is labelled that way.

## Considered options

1. **Pin nothing; rely on the Validator and the Executor's re-check.** Rejected: both are
   code, and the pre-mortem assumes both have failed. Leaving the family swap open when a
   key exists to close it is the "just in case" privilege row 6 exists to prevent.
2. **Pin all 13 keys now.** Rejected: most have no real value until Terraform lands, so the
   pins would be guesses. How `ecs:subnet` evaluates a request naming several subnets is
   also unverified.
3. **Move `UpdateService` to a separate actuator role that enforces its own checks.**
   Rejected *for this decision*: it changes the Executor's design and depends on
   [ADR-0004](0004-pipeline-runtime.md). It stays open as one way to bound spend, which no
   condition key can do.
4. **Pin the keys whose correct value is known today, give every other key a written
   reason, and make CI guard the exact values.** Chosen.

## Decision

Pin two keys on the Executor's `ecs:UpdateService` statement:

| Key | Pin | Why now |
|---|---|---|
| `ecs:task-definition` | `ArnLikeIfExists` `task-definition/orders-api:*` | Closes the swap to another family and its task role |
| `ecs:enable-execute-command` | `StringEqualsIfExists` `"false"` | The Executor has no action that needs it — **unless** chaos access turns out to use ECS Exec, which is undecided (see Consequences) |

The other 11 stay unpinned, each for a stated reason:

| Key | Why not pinned yet |
|---|---|
| `ecs:subnet` | No subnet IDs until Terraform; multi-subnet evaluation unverified |
| `ecs:capacity-provider` | No capacity provider defined yet; may bear on spend and availability, so pin in Sprint 5 |
| `ecs:task-cpu`, `ecs:task-memory` | Task size not set until Terraform; may bear on spend, so pin in Sprint 5 |
| `ecs:enable-service-connect`, `ecs:namespace`, `ecs:enable-vpc-lattice` | None configured; each may widen network exposure, so pin off in Sprint 5 once Terraform confirms they are unused |
| `ecs:enable-ebs-volumes` | No volumes planned; pin off in Sprint 5 |
| `ecs:auto-assign-public-ip` | Tasks get public IPs by design (no NAT gateway); changing it affects only this service's availability, already a residual |
| `ecs:propagate-tags`, `ecs:enable-ecs-managed-tags` | Tagging only; no safety effect identified |

`scripts/check_iam_scope.py` guards the pins. `required_conditions` in
`infra/policies/action-mapping.json` lists each operator, key and value, and every `Allow`
statement granting `ecs:UpdateService` must carry them exactly. `Allow` statements using
`NotAction` fail outright.

The policy change was made alongside this ADR, so the diff and the decision can be reviewed
together. Rejecting the ADR means removing one `Condition` block and one
`required_conditions` entry.

## Consequences

- **The drift check fails on the weakenings a reviewer would try:** a removed pin, a
  widened value, a swapped operator, a second `Allow` statement without the pins, and
  `NotAction`. `agents/tests/unit/test_check_iam_scope.py` covers each, so the check is
  itself tested.
- **The family pin constrains the name, not the task role.** An `orders-api` revision can
  carry whatever task role it was registered with. The pin holds because the Executor
  cannot register revisions: `ecs:RegisterTaskDefinition` and `iam:PassRole` are not
  granted, and the drift check fails CI if either is added.
- **Any revision inside the family stays reachable,** including a known-bad one such as
  chaos #1's. IAM cannot tell a good revision from a bad one.
- **`IfExists` behaviour is read from the documentation, not observed.** Restart and scale
  calls omit the task definition and are meant to pass. If ECS instead fills in an omitted
  key from the service's current configuration, calls could be denied. Sprint 5 confirms
  both directions with real calls.
- **The execute-command pin may conflict with the chaos access path.** The sandbox app spec
  plans "SSM port-forward" to the internal listener. If that is done through ECS Exec, the
  service needs `enableExecuteCommand=true` and this pin must go. The access path is
  undecided; Sprint 5 settles it before the Executor role is applied.
- **The check reads the policy template, not the deployed policy.** `REGION` and `ACCOUNT`
  are compared as literal placeholders. Nothing yet checks that a Terraform-rendered policy
  keeps the pins.
- **Cost:** the policy and `action-mapping.json` must change together, and every new pin
  needs a matching entry and a test case.
- **This does not bound spend.** No `UpdateService` key constrains `desiredCount`; ADR-0007
  still governs row 4.

## Residual risk

- A rollback to a known-bad revision in the family, or `desiredCount` set to 0: the
  availability of one sandbox service.
- A wider security group attached to the service. `UpdateService` has no security-group
  key; this is bounded only by keeping permissive security groups out of the account.
- The 11 unpinned keys stay open until Sprint 5.
- Until the denied-call tests run, the pins are only as good as the documented IAM
  evaluation.

## Sources

- [ECS service reference (machine-readable)](https://servicereference.us-east-1.amazonaws.com/v1/ecs/ecs.json) — the 13 `UpdateService` keys; no resource-level support for `DescribeTaskDefinition`
- [How Amazon ECS works with IAM](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security_iam_service-with-iam.html) — condition key definitions and value types
- [Actions, resources, and condition keys for Amazon ECS](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelasticcontainerservice.html)
