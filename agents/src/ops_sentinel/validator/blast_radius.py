"""Risk row 1 — blast radius.

Rejects any action not scoped to a single, named resource ID.

DESIGN FORK, resolved: this rule REJECTS. It does not downgrade to strict approval.

The register and the architecture table also say pattern matches "always route to strict
approval, never fast-path". That is a second, incompatible disposition for the same input,
and it is not expressible here: a `RuleOutcome` is `passed` plus `detail`, and the approval
path is computed by `scoring.py` from severity × confidence × reversibility (row 8). A rule
that returned "passed, but never fast-path" would need a channel that does not exist. So the
gate rejects, and any softer disposition is scoring's to own:

  gate   -> reject an action that names more than one resource (here)
  score  -> decide fast-path vs strict for actions that passed (scoring.py, row 8)

What counts as "not a single, named resource ID": a blank target, glob metacharacters, a tag
selector, or several resources in one string. A full ARN is accepted — it names exactly one
resource, and it is the form `infra/policies/executor-policy.json` pins.

Run over BOTH the primary action and the rollback action — the rollback is a path to the
same Executor, so an unchecked rollback is an unchecked action.

Residual risk: two resources sharing an ID by config error. This rule checks the *shape* of
a target, not its existence; it cannot know that two services answer to one name.
"""

from __future__ import annotations

from typing import Literal

from ops_sentinel.schemas import Action, RuleOutcome

RISK_ROW = 1
RULE = "blast_radius"

_Subject = Literal["action", "rollback_action"]

_WILDCARD_CHARS = frozenset("*?[]")
_TAG_PREFIX = "tag:"
_LIST_SEPARATORS = frozenset(",;")


def check(action: Action, subject: _Subject = "action") -> RuleOutcome:
    """Return the outcome of the blast radius rule. Never raises on bad input."""
    target = action.target_resource_id
    stripped = target.strip()

    if not stripped:
        return _fail(f"Target resource ID is blank: {target!r}; it names no resource", subject)

    if any(char in _WILDCARD_CHARS for char in stripped):
        return _fail(
            f"Target resource ID {target!r} contains a wildcard; it matches an unknown "
            f"number of resources rather than naming one",
            subject,
        )

    if stripped.lower().startswith(_TAG_PREFIX) or "=" in stripped:
        return _fail(
            f"Target resource ID {target!r} is a tag pattern; it resolves to however many "
            f"resources carry the tag",
            subject,
        )

    if any(char in _LIST_SEPARATORS for char in stripped) or len(stripped.split()) > 1:
        return _fail(
            f"Target resource ID {target!r} names more than one resource; an action targets "
            f"exactly one",
            subject,
        )

    return RuleOutcome(
        rule=RULE,
        risk_row=RISK_ROW,
        passed=True,
        detail=f"{action.action_type} is scoped to the single resource {stripped}",
        subject=subject,
    )


def _fail(detail: str, subject: _Subject) -> RuleOutcome:
    return RuleOutcome(
        rule=RULE, risk_row=RISK_ROW, passed=False, detail=detail, subject=subject
    )
