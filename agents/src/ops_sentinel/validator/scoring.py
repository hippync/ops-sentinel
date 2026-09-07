"""Risk row 8 — approval-path scoring.

Scores a proposal on three axes rather than emitting a single approve/reject bit:

    severity      how bad if the fix is wrong
    confidence    how sure the Worker is, from diagnostic signal strength
    reversibility whether a clean rollback exists

    low severity + high confidence + reversible -> FAST_PATH (single click)
    high severity OR irreversible               -> STRICT, regardless of confidence

The false-positive tolerance is a documented, designed trade-off — chosen before the
demo, not justified after it. See docs/sprints.md, Sprint 1.
"""

from ops_sentinel.schemas import ApprovalPath, FixProposal, Incident

RISK_ROW = 8
CONFIDENCE_FAST_PATH_MIN = 0.85  # TODO(sprint-1): document this choice in an ADR


def approval_path(proposal: FixProposal, incident: Incident) -> ApprovalPath:
    raise NotImplementedError("Sprint 1")
