"""Risk row 4 — runaway infrastructure cost.

Enforces a fixed maximum instance count, independent of the Worker's reasoning. A scale
action with no upper bound, or one above the ceiling, is rejected.

This row is the documented EXCEPTION to "IAM is the last line of defense": AWS exposes
no IAM condition key constraining `desiredCount` on `ecs:UpdateService`, so this ceiling
cannot be enforced in the Executor's role. See
docs/adr/0007-row-4-cannot-live-in-iam.md. It is therefore designed to be checked twice
in code instead: here, and in the Executor's own re-check. ECS Service Auto Scaling max
capacity is a lagging correction, not a third block — it does not stop `UpdateService`
setting a higher count, and pulls it back down only when a scale-in alarm fires.

Residual risk: a legitimate spike that genuinely needs more than the ceiling allows. And
because IAM cannot bound the count, if both code checks fail, spend is bounded only by
account-level limits and how quickly someone notices.
"""

from __future__ import annotations

from ops_sentinel.config import MAX_DESIRED_COUNT
from ops_sentinel.schemas import FixProposal, RuleOutcome

RISK_ROW = 4
RULE = "cost_ceiling"

__all__ = ["MAX_DESIRED_COUNT", "RISK_ROW", "RULE", "check"]


def check(proposal: FixProposal) -> RuleOutcome:
    raise NotImplementedError("Sprint 1")
