"""Contract smoke tests — the stage boundaries must reject malformed data."""

import pytest
from pydantic import ValidationError

from ops_sentinel.schemas import Action, ActionType, Rollback


def test_action_rejects_empty_target_resource_id() -> None:
    """Risk row 1's first line of defense lives in the schema itself."""
    with pytest.raises(ValidationError):
        Action(action_type=ActionType.RESTART_SERVICE, target_resource_id="")


def test_rollback_requires_a_description() -> None:
    """Risk row 7: a rollback plan that says nothing is not a rollback plan."""
    with pytest.raises(ValidationError):
        Rollback(
            description="",
            action=Action(
                action_type=ActionType.ROLLBACK_TASK_DEFINITION,
                target_resource_id="orders-api",
            ),
        )
