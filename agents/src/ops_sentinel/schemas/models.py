"""Pipeline data contracts.

Draft for Sprint 0. Field-level constraints here are the first line of defense;
the Validator's rules (see ops_sentinel.validator) are the second.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IncidentType(StrEnum):
    ELEVATED_5XX = "elevated_5xx"
    OOM_RESTART_LOOP = "oom_restart_loop"
    LATENCY_REGRESSION = "latency_regression"
    UNKNOWN = "unknown"
    """UNKNOWN short-circuits to a human. The pipeline never guesses at an
    incident class it has no playbook for."""


class ActionType(StrEnum):
    """The v1 action set. This list *is* the Executor's IAM policy —
    see infra/policies/executor-policy.json (risk row 6)."""

    ROLLBACK_TASK_DEFINITION = "ecs:rollback_task_definition"
    RESTART_SERVICE = "ecs:restart_service"
    SET_DESIRED_COUNT = "ecs:set_desired_count"


class ApprovalPath(StrEnum):
    FAST_PATH = "fast_path"
    STRICT = "strict"


class Evidence(BaseModel):
    """A specific log line or metric datapoint the diagnosis relies on.

    Ingested content lives here as *data*. It is never concatenated into an
    instruction position (risk row 5)."""

    source: str
    reference: str
    excerpt: str
    observed_at: datetime


class Incident(BaseModel):
    incident_id: str
    incident_type: IncidentType
    severity: Severity
    affected_resource_ids: list[str] = Field(min_length=1)
    """The Validator checks a proposed action's target against this set.
    An action naming a resource absent here is not derivable from the incident."""
    window_start: datetime
    window_end: datetime
    raw_alarm: dict[str, object]


class Action(BaseModel):
    action_type: ActionType
    target_resource_id: str = Field(min_length=1)
    """A single named resource ID. Wildcards and tag patterns are rejected by
    blast_radius (risk row 1)."""
    parameters: dict[str, object] = Field(default_factory=dict)
    max_instances: int | None = None
    """Required for SET_DESIRED_COUNT; enforced against the ceiling (risk row 4)."""


class Rollback(BaseModel):
    """Required on every proposal. A proposal without one is rejected (risk row 7)."""

    description: str = Field(min_length=1)
    action: Action
    verified: bool = False


class FixProposal(BaseModel):
    incident_id: str
    diagnosis: str
    action: Action
    rollback: Rollback
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(min_length=1)
    iterations_used: int
    """Set by the graph runtime, never self-reported by the Worker (risk row 3)."""
    proposal_hash: str


class RuleOutcome(BaseModel):
    rule: str
    risk_row: int
    passed: bool
    detail: str


class Verdict(BaseModel):
    proposal_hash: str
    passed: bool
    outcomes: list[RuleOutcome]
    approval_path: ApprovalPath
    reversible: bool
    decided_at: datetime


class ApprovalRecord(BaseModel):
    proposal_hash: str
    approved: bool
    approver: str
    approved_at: datetime
    path: ApprovalPath


class AuditRecord(BaseModel):
    """One record per pipeline run. A v1 deliverable, shown in the demo."""

    run_id: str
    incident: Incident
    proposal: FixProposal | None
    verdict: Verdict | None
    approval: ApprovalRecord | None
    execution_result: dict[str, object] | None
    terminal_state: str
