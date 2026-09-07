"""Shared fixtures.

`clean_proposal` is the baseline every rule test mutates away from: one valid proposal,
one crafted violation per rule. Keeping the baseline in one place means a schema change
breaks every rule test at once, loudly, instead of silently weakening them.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ops_sentinel.schemas import (
    Action,
    Evidence,
    FixProposal,
    Incident,
    IncidentType,
    Rollback,
    RollbackTaskDefinitionParams,
    Severity,
)

FIXED_TIME = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
SERVICE = "orders-api"


@pytest.fixture
def incident() -> Incident:
    return Incident(
        incident_id="inc-001",
        incident_type=IncidentType.ELEVATED_5XX,
        severity=Severity.HIGH,
        affected_resource_ids=[SERVICE],
        window_start=FIXED_TIME,
        window_end=FIXED_TIME,
        raw_alarm={"AlarmName": "orders-5xx"},
    )


@pytest.fixture
def clean_proposal() -> FixProposal:
    """A well-formed proposal: roll back to a named revision, undo by rolling forward."""
    return FixProposal(
        incident_id="inc-001",
        diagnosis="Revision 42 introduced a null dereference on GET /orders.",
        action=Action(
            target_resource_id=SERVICE,
            params=RollbackTaskDefinitionParams(target_revision=41),
        ),
        rollback=Rollback(
            description="Redeploy task definition revision 42 to restore the prior state.",
            action=Action(
                target_resource_id=SERVICE,
                params=RollbackTaskDefinitionParams(target_revision=42),
            ),
        ),
        confidence=0.91,
        evidence=[
            Evidence(
                source="cloudwatch:logs",
                reference="/ecs/orders-api",
                excerpt="NullPointerException at OrderController.get(OrderController.java:41)",
                observed_at=FIXED_TIME,
            )
        ],
    )
