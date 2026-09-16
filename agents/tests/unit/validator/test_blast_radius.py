"""Risk row 1 — the blast radius rule.

A non-empty `target_resource_id` is guaranteed by the schema (`min_length=1`). These tests
cover the half the schema cannot: whether that string names *one* resource rather than a
set of them. They also cover the rollback action, which is a path to the same Executor and
which no rule checked before this one.
"""

from __future__ import annotations

import pytest

from ops_sentinel.schemas import FixProposal
from ops_sentinel.validator import blast_radius

ARN = "arn:aws:ecs:us-east-1:123456789012:service/ops-sentinel-sandbox/orders-api"


def test_clean_proposal_action_passes(clean_proposal: FixProposal) -> None:
    outcome = blast_radius.check(clean_proposal.action)
    assert outcome.passed
    assert outcome.risk_row == 1
    assert outcome.subject == "action"


def test_rollback_action_passes_with_its_own_subject(clean_proposal: FixProposal) -> None:
    """The rollback is an unchecked path to the same Executor unless this rule runs over it.

    The audit log has to be able to tell the two outcomes apart, which is what `subject` is for.
    """
    outcome = blast_radius.check(clean_proposal.rollback.action, "rollback_action")
    assert outcome.passed
    assert outcome.subject == "rollback_action"


def test_whitespace_only_target_is_rejected(clean_proposal: FixProposal) -> None:
    """`min_length=1` accepts a space. A blank target names nothing."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action.target_resource_id = "   "
    outcome = blast_radius.check(proposal.action)
    assert not outcome.passed
    assert "blank" in outcome.detail


@pytest.mark.parametrize("target", ["*", "orders-*", "orders-?", "orders-[12]"])
def test_wildcard_target_is_rejected(clean_proposal: FixProposal, target: str) -> None:
    """The register's headline case: a pattern match instead of a specific resource ID."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action.target_resource_id = target
    outcome = blast_radius.check(proposal.action)
    assert not outcome.passed
    assert "wildcard" in outcome.detail


@pytest.mark.parametrize("target", ["tag:env=prod", "env=prod"])
def test_tag_pattern_target_is_rejected(clean_proposal: FixProposal, target: str) -> None:
    """A tag selector resolves to however many resources carry the tag — unknowable here."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action.target_resource_id = target
    outcome = blast_radius.check(proposal.action)
    assert not outcome.passed
    assert "tag pattern" in outcome.detail


@pytest.mark.parametrize("target", ["orders-api,payments-api", "orders-api payments-api"])
def test_multiple_resources_are_rejected(clean_proposal: FixProposal, target: str) -> None:
    """Two named resources is still not "a single, named resource ID"."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action.target_resource_id = target
    outcome = blast_radius.check(proposal.action)
    assert not outcome.passed
    assert "more than one resource" in outcome.detail


def test_full_arn_is_accepted(clean_proposal: FixProposal) -> None:
    """An ARN names exactly one resource; rejecting it would over-reach past the row.

    This is the form infra/policies/executor-policy.json pins.
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action.target_resource_id = ARN
    assert blast_radius.check(proposal.action).passed


def test_rejection_carries_the_offending_value(clean_proposal: FixProposal) -> None:
    """The audit log must be readable without the source beside it.

    Asserts the rejection as well as the value: the pass detail also quotes the target, so
    checking only `detail` would leave this test green even with the wildcard guard removed.
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action.target_resource_id = "orders-*"
    outcome = blast_radius.check(proposal.action)
    assert not outcome.passed
    assert "orders-*" in outcome.detail


def test_check_never_raises(clean_proposal: FixProposal) -> None:
    """The gate must return a verdict, not an exception. A crashing validator fails open."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.action.target_resource_id = "*, tag:env=prod  [weird]"
    assert blast_radius.check(proposal.action).passed is False
