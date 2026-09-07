"""Contract tests — the properties the safety argument leans on."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ops_sentinel.schemas import (
    Action,
    FixProposal,
    RestartServiceParams,
    RollbackTaskDefinitionParams,
    SetDesiredCountParams,
)


def test_action_rejects_empty_target_resource_id() -> None:
    """Risk row 1's first line of defense lives in the schema itself."""
    with pytest.raises(ValidationError):
        Action(target_resource_id="", params=RestartServiceParams())


def test_action_params_are_typed_per_action_type() -> None:
    """A set-desired-count action without a count must not be constructible."""
    with pytest.raises(ValidationError):
        Action.model_validate(
            {"target_resource_id": "orders-api", "params": {"action_type": "ecs:set_desired_count"}}
        )


def test_negative_desired_count_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SetDesiredCountParams(desired_count=-1)


def test_proposal_hash_is_derived_not_supplied(clean_proposal: FixProposal) -> None:
    """The Executor's central check is only real if the hash cannot be forged.

    A compromised Worker that sets proposal_hash to a value matching an old approval
    must not be able to make the Executor accept it.
    """
    forged = FixProposal.model_validate(
        {**clean_proposal.model_dump(), "proposal_hash": "0" * 64}
    )
    assert forged.proposal_hash == clean_proposal.proposal_hash
    assert forged.proposal_hash != "0" * 64


def test_proposal_hash_changes_with_content(clean_proposal: FixProposal) -> None:
    tampered = clean_proposal.model_copy(deep=True)
    tampered.action = Action(
        target_resource_id="orders-api",
        params=RollbackTaskDefinitionParams(target_revision=1),
    )
    assert tampered.proposal_hash != clean_proposal.proposal_hash


def test_proposal_has_no_iterations_field(clean_proposal: FixProposal) -> None:
    """Design principle 6: a limit reported by the thing it limits is not a limit.

    iterations_used belongs to graph state and the AuditRecord, never to the Worker's
    own output type.
    """
    assert "iterations_used" not in FixProposal.model_fields
