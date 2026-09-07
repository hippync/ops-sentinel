"""Typed contracts between pipeline stages.

Every stage boundary is validated here. A malformed proposal fails at the boundary
rather than deep inside the Validator. See docs/architecture.md section 2.
"""

from ops_sentinel.schemas.models import (
    Action,
    ActionParams,
    ActionType,
    ApprovalPath,
    ApprovalRecord,
    AuditRecord,
    Evidence,
    FixProposal,
    Incident,
    IncidentType,
    RestartServiceParams,
    Rollback,
    RollbackTaskDefinitionParams,
    RuleOutcome,
    SetDesiredCountParams,
    Severity,
    Verdict,
)

__all__ = [
    "Action",
    "ActionParams",
    "ActionType",
    "ApprovalPath",
    "ApprovalRecord",
    "AuditRecord",
    "Evidence",
    "FixProposal",
    "Incident",
    "IncidentType",
    "RestartServiceParams",
    "Rollback",
    "RollbackTaskDefinitionParams",
    "RuleOutcome",
    "Severity",
    "SetDesiredCountParams",
    "Verdict",
]
