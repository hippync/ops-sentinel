"""Risk row 6 — the IAM drift check in scripts/check_iam_scope.py.

A drift check that passes because it compares the wrong things is worse than none. Each
test takes the committed Executor policy, weakens it the way a reviewer (or a hurried
edit) would, and asserts the check notices.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
from types import ModuleType
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "check_iam_scope.py"
POLICY = ROOT / "infra" / "policies" / "executor-policy.json"
SERVICE_ARN = "arn:aws:ecs:REGION:ACCOUNT:service/ops-sentinel-sandbox/orders-api"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_iam_scope", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_iam_scope = _load_script()


@pytest.fixture
def policy() -> dict[str, Any]:
    return json.loads(POLICY.read_text())


def _update_service(policy: dict[str, Any]) -> dict[str, Any]:
    return next(s for s in policy["Statement"] if s["Sid"] == "UpdateOnlyTheOrdersService")


def _run(policy: dict[str, Any], tmp_path: pathlib.Path) -> int:
    path = tmp_path / "executor-policy.json"
    path.write_text(json.dumps(policy))
    result: int = check_iam_scope.main(["--policy", str(path)])
    return result


def test_committed_policy_passes(policy: dict[str, Any], tmp_path: pathlib.Path) -> None:
    assert _run(policy, tmp_path) == 0


def test_removed_task_definition_pin_fails(
    policy: dict[str, Any], tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    del _update_service(policy)["Condition"]["ArnLikeIfExists"]

    assert _run(policy, tmp_path) == 1
    err = capsys.readouterr().err
    assert "UpdateOnlyTheOrdersService" in err
    assert "ecs:task-definition" in err


def test_widened_task_definition_pin_fails(
    policy: dict[str, Any], tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    widened = "arn:aws:ecs:*:*:task-definition/*"
    _update_service(policy)["Condition"]["ArnLikeIfExists"]["ecs:task-definition"] = widened

    assert _run(policy, tmp_path) == 1
    assert widened in capsys.readouterr().err


def test_swapped_operator_fails(policy: dict[str, Any], tmp_path: pathlib.Path) -> None:
    condition = _update_service(policy)["Condition"]
    condition["StringNotEqualsIfExists"] = condition.pop("StringEqualsIfExists")

    assert _run(policy, tmp_path) == 1


def test_shadowing_allow_statement_fails(policy: dict[str, Any], tmp_path: pathlib.Path) -> None:
    _update_service(policy)["Effect"] = "Deny"
    policy["Statement"].append(
        {
            "Sid": "Shadow",
            "Effect": "Allow",
            "Action": "ecs:UpdateService",
            "Resource": SERVICE_ARN,
            "Condition": {
                "Null": {"ecs:task-definition": "true", "ecs:enable-execute-command": "true"}
            },
        }
    )

    assert _run(policy, tmp_path) == 1


def test_not_action_statement_fails(policy: dict[str, Any], tmp_path: pathlib.Path) -> None:
    policy["Statement"].append(
        {"Sid": "Broad", "Effect": "Allow", "NotAction": "iam:*", "Resource": "*"}
    )

    assert _run(policy, tmp_path) == 1


def test_action_no_action_type_requires_fails(
    policy: dict[str, Any], tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    policy["Statement"].append(
        {"Sid": "Extra", "Effect": "Allow", "Action": "ecs:RegisterTaskDefinition", "Resource": "*"}
    )

    assert _run(policy, tmp_path) == 1
    assert "ecs:RegisterTaskDefinition" in capsys.readouterr().err
