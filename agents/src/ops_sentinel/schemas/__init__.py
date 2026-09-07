"""Typed contracts between pipeline stages.

Every stage boundary is validated here. A malformed proposal fails at the boundary
rather than deep inside the Validator. See docs/architecture.md section 2.
"""

from ops_sentinel.schemas.models import (
    ActionType,
    Action,
    ApprovalPath,
    ApprovalRecord,
    AuditRecord,
    Evidence,
    FixProposal,
    Incident,
    IncidentType,
    Rollback,
    RuleOutcome,
    Severity,
    Verdict,
)

__all__ = [
    "Action",
    "ActionType",
    "ApprovalPath",
    "ApprovalRecord",
    "AuditRecord",
    "Evidence",
    "FixProposal",
    "Incident",
    "IncidentType",
    "Rollback",
    "RuleOutcome",
    "Severity",
    "Verdict",
]
