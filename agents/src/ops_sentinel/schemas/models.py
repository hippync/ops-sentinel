"""Pipeline data contracts.

Every stage boundary is typed. A malformed proposal fails here rather than deep inside
the Validator.

Two properties in this module are load-bearing for the safety argument:

* `Action.params` is a discriminated union, so an action's payload is validated against
  its own action type rather than being an untyped bag handed to boto3.
* `FixProposal.proposal_hash` is COMPUTED, not a field. A hash the Worker can set is not
  a hash the Executor can verify.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IncidentType(StrEnum):
    ELEVATED_5XX = "elevated_5xx"
    OOM_RESTART_LOOP = "oom_restart_loop"
    LATENCY_REGRESSION = "latency_regression"
    UNKNOWN = "unknown"
    """UNKNOWN short-circuits to a human. The pipeline never guesses at an incident
    class it has no playbook for."""


class ActionType(StrEnum):
    """The v1 action set.

    This enum and `infra/policies/executor-policy.json` must stay in agreement; CI
    asserts it. Note that one IAM action (`ecs:UpdateService`) covers all three of
    these — see docs/adr/0007-row-4-cannot-live-in-iam.md for what that costs us.
    """

    ROLLBACK_TASK_DEFINITION = "ecs:rollback_task_definition"
    RESTART_SERVICE = "ecs:restart_service"
    SET_DESIRED_COUNT = "ecs:set_desired_count"


class ApprovalPath(StrEnum):
    FAST_PATH = "fast_path"
    STRICT = "strict"


# --------------------------------------------------------------------------------------
# Action payloads — a typed shape per action type, not a dict[str, object]
# --------------------------------------------------------------------------------------


class RollbackTaskDefinitionParams(BaseModel):
    action_type: Literal[ActionType.ROLLBACK_TASK_DEFINITION] = (
        ActionType.ROLLBACK_TASK_DEFINITION
    )
    target_revision: int = Field(gt=0)
    """The specific task-definition revision to roll back to. Named, never 'previous'."""


class RestartServiceParams(BaseModel):
    action_type: Literal[ActionType.RESTART_SERVICE] = ActionType.RESTART_SERVICE


class SetDesiredCountParams(BaseModel):
    action_type: Literal[ActionType.SET_DESIRED_COUNT] = ActionType.SET_DESIRED_COUNT
    desired_count: int = Field(ge=0)
    """Bounded by config.MAX_DESIRED_COUNT in the Validator, by Service Auto Scaling max
    capacity in the infrastructure, and re-checked in the Executor. It cannot be bounded
    in IAM."""


ActionParams = Annotated[
    RollbackTaskDefinitionParams | RestartServiceParams | SetDesiredCountParams,
    Field(discriminator="action_type"),
]


class Action(BaseModel):
    target_resource_id: str = Field(min_length=1)
    """A single named resource ID. Wildcards and tag patterns are rejected by
    blast_radius (risk row 1)."""
    params: ActionParams

    @property
    def action_type(self) -> ActionType:
        return self.params.action_type


# --------------------------------------------------------------------------------------
# Ingested content
# --------------------------------------------------------------------------------------


class Evidence(BaseModel):
    """A specific log line or metric datapoint the diagnosis relies on.

    `excerpt` is UNTRUSTED, ATTACKER-INFLUENCED content. Two consequences:

    1. It is never concatenated into an instruction position (risk row 5).
    2. It is the carrier for any secret or PII in the pipeline, and it reaches the audit
       log — which is a demo deliverable. It must be redacted at every rendering
       boundary; see ops_sentinel.audit.redaction.
    """

    source: str
    reference: str
    excerpt: str
    observed_at: datetime


class Incident(BaseModel):
    incident_id: str
    incident_type: IncidentType
    severity: Severity
    affected_resource_ids: list[str] = Field(min_length=1)
    """The Validator checks a proposed action's target against this set. An action
    naming a resource absent here is not derivable from the incident (risk row 5)."""
    window_start: datetime
    window_end: datetime
    raw_alarm: dict[str, object]


class Rollback(BaseModel):
    """Required on every proposal. A proposal without one is rejected (risk row 7).

    `action` is a path to the same Executor as the primary action, so the Validator runs
    the same rules over it. An unchecked rollback is an unchecked action.
    """

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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def proposal_hash(self) -> str:
        """Derived from the proposal's content, so it cannot be set by whoever built it.

        The Executor compares this against the hash in the ApprovalRecord. If the hash
        were a plain field, a compromised Worker could simply set it to match, and the
        Executor's central security check would be theater.
        """
        payload = self.model_dump(mode="json", exclude={"proposal_hash"})
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RuleOutcome(BaseModel):
    rule: str
    risk_row: int
    passed: bool
    detail: str
    subject: Literal["action", "rollback_action", "proposal"] = "proposal"
    """Which part of the proposal this outcome refers to. The same rule runs over both
    the primary action and the rollback action, and the audit log must distinguish
    them."""


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
    """One record per pipeline run. A v1 deliverable, shown in the demo.

    `iterations_used` lives here and in graph state — never in the Worker's own output
    type. A limit reported by the thing it limits is not a limit (design principle 6).

    Contains `Evidence.excerpt`, i.e. raw ingested log content. Render it through
    ops_sentinel.audit.redaction, never directly.
    """

    run_id: str
    incident: Incident
    proposal: FixProposal | None
    verdict: Verdict | None
    approval: ApprovalRecord | None
    execution_result: dict[str, object] | None
    terminal_state: str
    iterations_used: int
