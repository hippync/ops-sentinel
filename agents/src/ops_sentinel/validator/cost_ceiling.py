"""Risk row 4 — runaway infrastructure cost.

Enforces a fixed max-instance-count / max-spend-delta, independent of the Worker's
own reasoning. A scale or resize action with no upper bound is rejected.

Residual risk: a legitimate spike that genuinely needs more than the ceiling allows.
"""

from ops_sentinel.schemas import FixProposal, RuleOutcome

RISK_ROW = 4
MAX_DESIRED_COUNT = 4  # TODO(sprint-1): move to config, document the choice


def check(proposal: FixProposal) -> RuleOutcome:
    raise NotImplementedError("Sprint 1")
