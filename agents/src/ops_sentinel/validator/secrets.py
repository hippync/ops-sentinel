"""Risk row 2 — credentials and PII.

Scrubs or rejects any proposal containing raw log content matching secret or PII
patterns, *before* it is shown to a human.

Residual risk: novel secret formats not covered by the pattern set.
"""

from ops_sentinel.schemas import FixProposal, RuleOutcome

RISK_ROW = 2


def check(proposal: FixProposal) -> RuleOutcome:
    raise NotImplementedError("Sprint 1")
