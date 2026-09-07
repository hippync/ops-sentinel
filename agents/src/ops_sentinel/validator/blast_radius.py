"""Risk row 1 — blast radius.

Rejects any action not scoped to a single, named resource ID. Wildcards and tag patterns
never fast-path; they route to strict approval.

Run over BOTH the primary action and the rollback action — the rollback is a path to the
same Executor, so an unchecked rollback is an unchecked action.

Residual risk: two resources sharing an ID by config error.
"""

from __future__ import annotations

from ops_sentinel.schemas import Action, RuleOutcome

RISK_ROW = 1
RULE = "blast_radius"


def check(action: Action, subject: str = "action") -> RuleOutcome:
    raise NotImplementedError("Sprint 1")
