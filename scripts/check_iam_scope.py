#!/usr/bin/env python3
"""Fail if the Executor's IAM policy and the ActionType enum have drifted apart.

Risk row 6 claims: "even a fully manipulated agent cannot act outside that list."
That claim holds only if the policy actually grants the action set the code knows
about — and nothing but this check stops the two drifting silently as actions are
added over a semester.

This is a coarse check by necessity. One IAM action (ecs:UpdateService) covers three
ActionTypes, so it cannot verify a 1:1 mapping. What it CAN do is fail when an
ActionType exists with no declared IAM mapping at all, which is the realistic drift.

It also guards the condition pins in docs/adr/0010-pin-updateservice-condition-keys.md.
`required_conditions` in action-mapping.json lists, per IAM action, the exact operator,
key and value that every Allow statement granting that action must carry. Removing a
condition, widening its value, swapping its operator, or adding a second Allow statement
without it all leave the granted action set unchanged, so the action comparison alone
would pass. Allow statements using NotAction fail outright: they grant everything outside
a list, which this check cannot reason about.

What it does not check: the policy Terraform renders and applies. It reads the template
in this repo, with REGION and ACCOUNT as literal placeholders.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
POLICY = ROOT / "infra" / "policies" / "executor-policy.json"
MODELS = ROOT / "agents" / "src" / "ops_sentinel" / "schemas" / "models.py"
MAPPING = ROOT / "infra" / "policies" / "action-mapping.json"

Pins = dict[str, dict[str, dict[str, Any]]]


def _allow_statements(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return [statement for statement in policy["Statement"] if statement.get("Effect") == "Allow"]


def _actions(statement: dict[str, Any]) -> list[str]:
    actions = statement.get("Action", [])
    return [actions] if isinstance(actions, str) else list(actions)


def _sid(statement: dict[str, Any]) -> str:
    return str(statement.get("Sid", "<no Sid>"))


def _action_set_errors(
    action_types: set[str], mapping: dict[str, list[str]], granted: set[str]
) -> list[str]:
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
            errors.append(
                f"{action_type} needs IAM action(s) the policy does not grant: {sorted(missing)}"
            )

    required_everywhere = {iam for actions in mapping.values() for iam in actions}
    excess = granted - required_everywhere
    if excess:
        errors.append(
            f"Policy grants IAM action(s) no ActionType requires: {sorted(excess)} "
            "— over-privilege is exactly what row 6 exists to prevent"
        )

    return errors


def _not_action_errors(statements: list[dict[str, Any]]) -> list[str]:
    return [
        f"Statement {_sid(statement)} uses NotAction, which grants everything outside a "
        "list — this check cannot bound it"
        for statement in statements
        if "NotAction" in statement
    ]


def _pin_errors(statements: list[dict[str, Any]], required: Pins) -> list[str]:
    errors: list[str] = []
    for iam_action, pinned in required.items():
        expected_pins = [
            (operator, key, value)
            for operator, keys in pinned.items()
            for key, value in keys.items()
        ]
        for statement in statements:
            if iam_action not in _actions(statement):
                continue
            conditions = statement.get("Condition", {})
            for operator, key, expected in expected_pins:
                actual = conditions.get(operator, {}).get(key)
                if actual != expected:
                    errors.append(
                        f"Statement {_sid(statement)} grants {iam_action} without "
                        f"{operator} {key} = {expected!r} (found {actual!r})"
                    )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Risk row 6 drift check.")
    parser.add_argument("--policy", type=pathlib.Path, default=POLICY)
    parser.add_argument("--mapping", type=pathlib.Path, default=MAPPING)
    args = parser.parse_args(argv)

    policy = json.loads(args.policy.read_text())
    mapping_file = json.loads(args.mapping.read_text())
    mapping: dict[str, list[str]] = mapping_file["action_type_to_iam"]
    required_conditions: Pins = mapping_file.get("required_conditions", {})

    source = MODELS.read_text()
    enum_block = source.split("class ActionType(StrEnum):")[1].split("\nclass ")[0]
    action_types = set(re.findall(r'=\s*"(ecs:[a-z_]+)"', enum_block))

    allow = _allow_statements(policy)
    granted = {action for statement in allow for action in _actions(statement)}

    errors = _action_set_errors(action_types, mapping, granted)
    errors.extend(_not_action_errors(allow))
    errors.extend(_pin_errors(allow, required_conditions))

    if errors:
        print("IAM scope drift detected (risk row 6):\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(action_types)} ActionType(s) map onto {len(granted)} granted IAM action(s); "
        f"pinned conditions intact on {len(required_conditions)} action(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
