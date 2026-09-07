#!/usr/bin/env python3
"""Fail if the Executor's IAM policy and the ActionType enum have drifted apart.

Risk row 6 claims: "even a fully manipulated agent cannot act outside that list."
That claim holds only if the policy actually grants the action set the code knows
about — and nothing but this check stops the two drifting silently as actions are
added over a semester.

This is a coarse check by necessity. One IAM action (ecs:UpdateService) covers three
ActionTypes, so it cannot verify a 1:1 mapping. What it CAN do is fail when an
ActionType exists with no declared IAM mapping at all, which is the realistic drift.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
POLICY = ROOT / "infra" / "policies" / "executor-policy.json"
MODELS = ROOT / "agents" / "src" / "ops_sentinel" / "schemas" / "models.py"
MAPPING = ROOT / "infra" / "policies" / "action-mapping.json"


def main() -> int:
    policy = json.loads(POLICY.read_text())
    mapping: dict[str, list[str]] = json.loads(MAPPING.read_text())["action_type_to_iam"]

    source = MODELS.read_text()
    enum_block = source.split("class ActionType(StrEnum):")[1].split("\nclass ")[0]
    action_types = set(re.findall(r'=\s*"(ecs:[a-z_]+)"', enum_block))

    granted: set[str] = set()
    for statement in policy["Statement"]:
        actions = statement["Action"]
        granted.update([actions] if isinstance(actions, str) else actions)

    errors: list[str] = []

    unmapped = action_types - set(mapping)
    if unmapped:
        errors.append(f"ActionType(s) with no IAM mapping declared: {sorted(unmapped)}")

    stale = set(mapping) - action_types
    if stale:
        errors.append(f"Mapping declares ActionType(s) that no longer exist: {sorted(stale)}")

    for action_type, required in mapping.items():
        missing = set(required) - granted
        if missing:
            errors.append(f"{action_type} needs IAM action(s) the policy does not grant: {sorted(missing)}")

    required_everywhere = {iam for actions in mapping.values() for iam in actions}
    excess = granted - required_everywhere
    if excess:
        errors.append(
            f"Policy grants IAM action(s) no ActionType requires: {sorted(excess)} "
            "— over-privilege is exactly what row 6 exists to prevent"
        )

    if errors:
        print("IAM scope drift detected (risk row 6):\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"OK: {len(action_types)} ActionType(s) map onto {len(granted)} granted IAM action(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
