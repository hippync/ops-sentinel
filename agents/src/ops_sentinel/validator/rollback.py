"""Risk row 7 — cascading failure.

Rejects any proposal with no defined rollback step. Manual fixes often skip a
documented rollback too; this makes the omission blocking rather than silent.

Residual risk: rollback plans can themselves be wrong or untested.
"""

from ops_sentinel.schemas import FixProposal, RuleOutcome

RISK_ROW = 7


def check(proposal: FixProposal) -> RuleOutcome:
    raise NotImplementedError("Sprint 1")
