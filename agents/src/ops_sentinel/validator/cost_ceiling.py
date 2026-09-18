"""Risk row 4 — runaway infrastructure cost.

Enforces a fixed maximum instance count, independent of the Worker's reasoning. A scale
action above the ceiling is rejected.

This row is the documented EXCEPTION to "IAM is the last line of defense": AWS exposes
no IAM condition key constraining `desiredCount` on `ecs:UpdateService`, so this ceiling
cannot be enforced in the Executor's role. See
docs/adr/0007-row-4-cannot-live-in-iam.md. It is therefore designed to be checked twice
in code instead: here, and in the Executor's own re-check. ECS Service Auto Scaling max
capacity is a lagging correction, not a third block — it does not stop `UpdateService`
setting a higher count, and pulls it back down only when a scale-in alarm fires.

DESIGN FORK, resolved: the register's detection signal — "a scale/resize action with no
upper bound specified" — is UNCONSTRUCTIBLE and is not what this rule checks. Sprint 0's
typed payloads made `SetDesiredCountParams.desired_count` a required non-negative int, so
a scale action without a count cannot be built, let alone validated. What survives of the
signal is the half that can still go wrong: the bound the Worker *did* specify being one
this system is unwilling to pay for. The register's wording predates the typed payloads.

The register also offers "max-instance-count / max-spend-delta". Only the first is
computable here. A `FixProposal` carries no view of the service's *current* count, so a
delta cannot be derived; this rule bounds the absolute target count, in both directions.
A scale-down to a count still above the ceiling is rejected, correctly — the resulting
spend is what the row is about, not the direction of travel.

Run over BOTH the primary action and the rollback action. A rollback can itself be a
`set_desired_count`, and a proposal whose cheap primary action is undone by a rollback
scaling to 50 spends the same money.

Not covered: `desired_count: 0`. It is an availability harm, not a cost one, and this row
is cost — a rejection here would file "scaled the service to nothing" under runaway spend.
It passes.

Residual risk: a legitimate spike that genuinely needs more than the ceiling allows. The
uncovered scale-to-zero above, which the register's pre-mortem already records as bounded
by nothing. And because IAM cannot bound the count, if both code checks fail, spend is
bounded only by account-level limits and how quickly someone notices.
"""

from __future__ import annotations

from typing import Literal

from ops_sentinel.config import MAX_DESIRED_COUNT
from ops_sentinel.schemas import Action, RuleOutcome, SetDesiredCountParams

RISK_ROW = 4
RULE = "cost_ceiling"

_Subject = Literal["action", "rollback_action"]

__all__ = ["MAX_DESIRED_COUNT", "RISK_ROW", "RULE", "check"]


def check(action: Action, subject: _Subject = "action") -> RuleOutcome:
    """Return the outcome of the cost ceiling rule. Never raises on bad input."""
    params = action.params

    if not isinstance(params, SetDesiredCountParams):
        return _outcome(
            passed=True,
            detail=f"{action.action_type} sets no instance count; the ceiling does not apply",
            subject=subject,
        )

    if params.desired_count > MAX_DESIRED_COUNT:
        return _outcome(
            passed=False,
            detail=(
                f"Desired count {params.desired_count} on {action.target_resource_id} is "
                f"above the ceiling of {MAX_DESIRED_COUNT}; this count cannot be bounded "
                f"in IAM, so this rule and the Executor's re-check are the only controls "
                f"that act before the call"
            ),
            subject=subject,
        )

    return _outcome(
        passed=True,
        detail=(
            f"Desired count {params.desired_count} on {action.target_resource_id} is within "
            f"the ceiling of {MAX_DESIRED_COUNT}"
        ),
        subject=subject,
    )


def _outcome(*, passed: bool, detail: str, subject: _Subject) -> RuleOutcome:
    return RuleOutcome(
        rule=RULE, risk_row=RISK_ROW, passed=passed, detail=detail, subject=subject
    )
