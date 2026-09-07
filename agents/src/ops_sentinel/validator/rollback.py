"""Risk row 7 — cascading failure: every proposal must carry a real rollback.

The schema already guarantees a `Rollback` object exists. That is presence, not
substance, and presence is the easy half. This rule checks that the rollback is
*plausibly an inverse of the action it accompanies*:

* it targets the same resource — a rollback pointing somewhere else is not a rollback;
* it is not a verbatim repeat of the primary action — a "rollback" that re-applies the
  fix is a no-op that would pass a presence check;
* its description says something — placeholder text is the failure mode a human skims
  past, which is exactly the omission this row exists to make blocking.

Residual risk (unchanged from the register): rollback plans can be wrong or untested.
This rule raises the floor; it does not verify the plan actually works.
"""

from __future__ import annotations

from ops_sentinel.schemas import FixProposal, RuleOutcome

RISK_ROW = 7
RULE = "rollback"

_PLACEHOLDERS = frozenset(
    {"tbd", "todo", "n/a", "na", "none", "-", "rollback", "revert", "fix", "?"}
)
_MIN_DESCRIPTION_WORDS = 3


def check(proposal: FixProposal) -> RuleOutcome:
    """Return the outcome of the rollback rule. Never raises on bad input."""
    rollback = proposal.rollback
    description = rollback.description.strip()

    if description.lower().rstrip(".") in _PLACEHOLDERS:
        return _fail(f"Rollback description is a placeholder: {description!r}")

    if len(description.split()) < _MIN_DESCRIPTION_WORDS:
        return _fail(
            f"Rollback description is too thin to review "
            f"({len(description.split())} words, need {_MIN_DESCRIPTION_WORDS}): {description!r}"
        )

    if rollback.action.target_resource_id != proposal.action.target_resource_id:
        return _fail(
            f"Rollback targets {rollback.action.target_resource_id!r} but the action targets "
            f"{proposal.action.target_resource_id!r}; a rollback must undo its own action"
        )

    if rollback.action.params == proposal.action.params:
        return _fail(
            f"Rollback repeats the primary action verbatim "
            f"({proposal.action.action_type}); that is a no-op, not a rollback"
        )

    return RuleOutcome(
        rule=RULE,
        risk_row=RISK_ROW,
        passed=True,
        detail=(
            f"Rollback {rollback.action.action_type} on "
            f"{rollback.action.target_resource_id} inverts {proposal.action.action_type}"
        ),
        subject="rollback_action",
    )


def _fail(detail: str) -> RuleOutcome:
    return RuleOutcome(
        rule=RULE, risk_row=RISK_ROW, passed=False, detail=detail, subject="rollback_action"
    )
