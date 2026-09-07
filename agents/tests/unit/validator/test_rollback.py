"""Risk row 7 — the rollback rule.

Presence of a Rollback object is guaranteed by the schema. These tests cover the half
the schema cannot: whether the rollback is plausibly an inverse of its own action.
"""

from __future__ import annotations

import pytest

from ops_sentinel.schemas import Action, FixProposal, RollbackTaskDefinitionParams
from ops_sentinel.validator import rollback


def test_clean_proposal_passes(clean_proposal: FixProposal) -> None:
    outcome = rollback.check(clean_proposal)
    assert outcome.passed
    assert outcome.risk_row == 7
    assert outcome.subject == "rollback_action"


@pytest.mark.parametrize("placeholder", ["TBD", "todo", "n/a", "-", "revert", "None."])
def test_placeholder_description_is_rejected(
    clean_proposal: FixProposal, placeholder: str
) -> None:
    """The omission this row exists to make blocking is the one a human skims past."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.rollback.description = placeholder
    outcome = rollback.check(proposal)
    assert not outcome.passed
    assert "placeholder" in outcome.detail


def test_thin_description_is_rejected(clean_proposal: FixProposal) -> None:
    proposal = clean_proposal.model_copy(deep=True)
    proposal.rollback.description = "roll back"
    outcome = rollback.check(proposal)
    assert not outcome.passed
    assert "too thin" in outcome.detail


def test_rollback_targeting_a_different_resource_is_rejected(
    clean_proposal: FixProposal,
) -> None:
    """A rollback pointing elsewhere is a second action, not an undo."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.rollback.action = Action(
        target_resource_id="payments-api",
        params=RollbackTaskDefinitionParams(target_revision=7),
    )
    outcome = rollback.check(proposal)
    assert not outcome.passed
    assert "payments-api" in outcome.detail


def test_rollback_repeating_the_action_is_rejected(clean_proposal: FixProposal) -> None:
    """A no-op rollback passes a presence check; it must not pass this one."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.rollback.action = proposal.action.model_copy(deep=True)
    outcome = rollback.check(proposal)
    assert not outcome.passed
    assert "no-op" in outcome.detail


def test_rejection_never_raises(clean_proposal: FixProposal) -> None:
    """The gate must return a verdict, not an exception. A crashing validator fails open."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.rollback.description = "   "
    assert rollback.check(proposal).passed is False
