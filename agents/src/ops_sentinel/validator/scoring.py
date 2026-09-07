"""Risk row 8 — approval-path scoring.

Scores a proposal on three axes rather than emitting a single approve/reject bit:

    severity      how bad if the fix is wrong
    confidence    how sure the Worker is, from diagnostic signal strength
    reversibility whether a clean rollback exists

    low severity + high confidence + reversible -> FAST_PATH (single click)
    high severity OR irreversible               -> STRICT, regardless of confidence

`CONFIDENCE_FAST_PATH_MIN` is the documented false-positive trade-off. It is a judgment
call, it is chosen before the demo rather than justified after it, and the realised
false-positive rate is reported in the Sprint 6 retro whatever it turns out to be.
"""

from __future__ import annotations

from ops_sentinel.config import CONFIDENCE_FAST_PATH_MIN
from ops_sentinel.schemas import ApprovalPath, FixProposal, Incident

RISK_ROW = 8
RULE = "scoring"

__all__ = ["CONFIDENCE_FAST_PATH_MIN", "RISK_ROW", "RULE", "approval_path"]


def approval_path(proposal: FixProposal, incident: Incident) -> ApprovalPath:
    raise NotImplementedError("Sprint 1")
