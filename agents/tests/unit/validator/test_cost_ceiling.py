"""Risk row 4 — the cost ceiling rule.

`desired_count` is a required non-negative int in the schema, so the register's literal
detection signal — a scale action "with no upper bound specified" — is unconstructible
here. These tests cover what is left of the row: whether the bound the Worker *did*
specify is one this system is willing to pay for. They also cover the rollback action,
which can itself be a scale and is a path to the same Executor.

The ceiling is read from the module rather than written as a literal. It is the author's
judgment call, and a test that hard-codes it would have to be edited to change it.
"""

from __future__ import annotations

import pytest

from ops_sentinel.schemas import Action, FixProposal, SetDesiredCountParams
from ops_sentinel.validator import cost_ceiling

CEILING = cost_ceiling.MAX_DESIRED_COUNT


def _scale(target: str, count: int) -> Action:
    return Action(target_resource_id=target, params=SetDesiredCountParams(desired_count=count))


def test_clean_proposal_action_passes(clean_proposal: FixProposal) -> None:
    """A rollback-task-definition action sets no count, so the ceiling does not apply."""
    outcome = cost_ceiling.check(clean_proposal.action)
    assert outcome.passed
    assert outcome.risk_row == 4
    assert outcome.subject == "action"


def test_non_scale_action_is_not_rejected_for_lacking_a_count(
    clean_proposal: FixProposal,
) -> None:
    """Rejecting an action that cannot exceed the ceiling would over-reach past the row."""
    outcome = cost_ceiling.check(clean_proposal.rollback.action, "rollback_action")
    assert outcome.passed
    assert "sets no instance count" in outcome.detail


def test_scale_within_the_ceiling_passes(clean_proposal: FixProposal) -> None:
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action = _scale(proposal.action.target_resource_id, CEILING - 1)
    outcome = cost_ceiling.check(proposal.action)
    assert outcome.passed


def test_scale_at_the_ceiling_passes(clean_proposal: FixProposal) -> None:
    """The ceiling is the maximum permitted count, not the first forbidden one."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action = _scale(proposal.action.target_resource_id, CEILING)
    assert cost_ceiling.check(proposal.action).passed


def test_scale_above_the_ceiling_is_rejected(clean_proposal: FixProposal) -> None:
    """The row's headline case, and one IAM cannot express (ADR-0007)."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action = _scale(proposal.action.target_resource_id, CEILING + 1)
    outcome = cost_ceiling.check(proposal.action)
    assert not outcome.passed
    assert outcome.subject == "action"


@pytest.mark.parametrize("count", [5, 40, 4000])
def test_rejection_names_the_count_and_the_ceiling(
    clean_proposal: FixProposal, count: int
) -> None:
    """The audit log must be readable without the source beside it.

    Asserts the rejection as well as the values: the pass detail quotes both the count and
    the ceiling too, so a detail-only assertion would stay green with the guard removed.
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action = _scale(proposal.action.target_resource_id, CEILING + count)
    outcome = cost_ceiling.check(proposal.action)
    assert not outcome.passed
    assert str(CEILING + count) in outcome.detail
    assert f"ceiling of {CEILING}" in outcome.detail


def test_rollback_scale_above_the_ceiling_is_rejected(clean_proposal: FixProposal) -> None:
    """An unchecked rollback is an unchecked action: it reaches the same Executor.

    A proposal whose primary action is cheap and whose rollback scales to 50 spends the
    same money, and `subject` is what lets the audit log say which one did it.
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.rollback.action = _scale(proposal.action.target_resource_id, CEILING + 1)
    outcome = cost_ceiling.check(proposal.rollback.action, "rollback_action")
    assert not outcome.passed
    assert outcome.subject == "rollback_action"


def test_scale_to_zero_passes(clean_proposal: FixProposal) -> None:
    """Zero is an availability harm, not a cost one, and this row is cost.

    The register's pre-mortem lists `desiredCount` set to 0 as unbounded and unmitigated.
    It stays that way: rejecting it here would make row 4's detail read as a cost
    rejection for an action that costs nothing. See the module's residual risk.
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action = _scale(proposal.action.target_resource_id, 0)
    assert cost_ceiling.check(proposal.action).passed


def test_check_never_raises(clean_proposal: FixProposal) -> None:
    """The gate must return a verdict, not an exception. A crashing validator fails open."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action = _scale("   ", 2**31)
    assert cost_ceiling.check(proposal.action).passed is False
