"""Risk row 1 — blast radius.

Rejects any action not scoped to a single, named resource ID. Wildcards and tag
patterns never fast-path; they route to strict approval.

Residual risk: two resources sharing an ID by config error.
"""

from ops_sentinel.schemas import FixProposal, RuleOutcome

RISK_ROW = 1


def check(proposal: FixProposal) -> RuleOutcome:
    raise NotImplementedError("Sprint 1")
