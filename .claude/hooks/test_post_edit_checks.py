"""Tests for the PostToolUse edit hook.

The hook's dangerous failure mode is passing silently — running no checks, or reporting
success, when it should have run something. So every test below asserts on *which* checks
a path selects, not merely that the function returns.

Run: agents/.venv/bin/pytest -q .claude/hooks
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from post_edit_checks import (
    Failure,
    classify,
    format_failures,
    frontmatter_problems,
    read_payload,
    relative_path,
)

REPO = Path("/repo")


# ----------------------------------------------------------------------------------
# classify — which checks a path calls for
# ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel",
    [
        "agents/src/ops_sentinel/validator/blast_radius.py",
        "agents/src/ops_sentinel/config.py",
        "agents/tests/unit/validator/test_rollback.py",
        "agents/tests/conftest.py",
    ],
)
def test_project_python_files_run_the_python_checks(rel: str) -> None:
    checks = classify(rel)
    assert checks.python
    assert not checks.hook_self_test


def test_edits_inside_the_venv_run_nothing() -> None:
    """A dependency changing on disk is not a reason to run this project's suite."""
    checks = classify("agents/.venv/lib/python3.12/site-packages/pydantic/main.py")
    assert not checks.any_requested()


def test_models_py_runs_both_python_and_iam_checks() -> None:
    """Risk row 6: ActionType lives here, so an edit can silently break the IAM mapping."""
    checks = classify("agents/src/ops_sentinel/schemas/models.py")
    assert checks.python
    assert checks.iam


@pytest.mark.parametrize(
    "rel", ["infra/policies/executor-policy.json", "infra/policies/action-mapping.json"]
)
def test_policy_files_run_the_iam_check_only(rel: str) -> None:
    checks = classify(rel)
    assert checks.iam
    assert not checks.python


def test_the_hook_itself_runs_its_own_tests() -> None:
    checks = classify(".claude/hooks/post_edit_checks.py")
    assert checks.hook_self_test
    assert not checks.python


@pytest.mark.parametrize(
    "rel",
    [
        "README.md",
        "docs/sprints.md",
        "infra/policies/notes.txt",
        "sandbox-app/src/main/java/com/opssentinel/orders/OrdersSandboxApplication.java",
        "agents/pyproject.toml",
    ],
)
def test_unrelated_files_run_nothing(rel: str) -> None:
    assert not classify(rel).any_requested()


# ----------------------------------------------------------------------------------
# relative_path
# ----------------------------------------------------------------------------------


def test_absolute_path_inside_the_repo_becomes_relative() -> None:
    assert relative_path("/repo/agents/src/ops_sentinel/config.py", REPO) == (
        "agents/src/ops_sentinel/config.py"
    )


def test_path_outside_the_repo_is_ignored() -> None:
    assert relative_path("/etc/passwd", REPO) is None


def test_empty_path_is_ignored() -> None:
    assert relative_path("", REPO) is None


def test_relative_path_is_passed_through() -> None:
    assert relative_path("agents/src/ops_sentinel/config.py", REPO) == (
        "agents/src/ops_sentinel/config.py"
    )


# ----------------------------------------------------------------------------------
# read_payload — must never raise, whatever the harness sends
# ----------------------------------------------------------------------------------


def test_tool_response_path_wins_over_tool_input() -> None:
    """tool_response carries the path actually written; tool_input is the request."""
    payload = (
        '{"tool_response": {"filePath": "/repo/a.py"}, '
        '"tool_input": {"file_path": "/repo/b.py"}}'
    )
    assert read_payload(io.StringIO(payload)) == "/repo/a.py"


def test_falls_back_to_tool_input() -> None:
    assert read_payload(io.StringIO('{"tool_input": {"file_path": "/repo/b.py"}}')) == "/repo/b.py"


@pytest.mark.parametrize(
    "payload",
    [
        "",
        "not json",
        "[]",
        "null",
        '{"tool_input": {}}',
        '{"tool_input": null}',
        '{"tool_response": {"filePath": null}}',
        '{"tool_response": {"filePath": ""}}',
    ],
)
def test_malformed_payloads_yield_no_path_and_never_raise(payload: str) -> None:
    assert read_payload(io.StringIO(payload)) == ""


# ----------------------------------------------------------------------------------
# format_failures
# ----------------------------------------------------------------------------------


def test_claude_markdown_files_get_a_frontmatter_check() -> None:
    checks = classify(".claude/agents/adversarial-reviewer.md")
    assert checks.frontmatter
    assert not checks.python


# ----------------------------------------------------------------------------------
# frontmatter_problems — the regression guard for the bug GitHub caught
# ----------------------------------------------------------------------------------


def test_the_bug_that_actually_shipped_is_caught() -> None:
    """Verbatim shape of the line GitHub rejected: an unquoted description with ': '."""
    text = (
        "---\n"
        "name: adversarial-reviewer\n"
        "description: Use before committing anything containing prose: README edits, ADRs.\n"
        "tools: Read, Grep\n"
        "---\n\nBody.\n"
    )
    problems = frontmatter_problems(text)
    assert len(problems) == 1
    assert problems[0].startswith("description:")


def test_quoting_the_value_fixes_it() -> None:
    text = (
        "---\n"
        'description: "Use before committing anything containing prose: README edits."\n'
        "---\n"
    )
    assert frontmatter_problems(text) == []


def test_single_quotes_also_count_as_quoted() -> None:
    text = "---\ndescription: 'a: b'\n---\n"
    assert frontmatter_problems(text) == []


def test_the_repos_real_frontmatter_is_clean() -> None:
    """Guards every committed agent and command definition, not just a synthetic case."""
    hooks_dir = Path(__file__).resolve().parent
    for path in sorted((hooks_dir.parent).rglob("*.md")):
        assert frontmatter_problems(path.read_text(encoding="utf-8")) == [], path


@pytest.mark.parametrize(
    "text",
    [
        "",
        "No frontmatter here, just prose: with a colon.\n",
        "---\ndescription: a plain value\n---\n",
        "---\ntools: Read, Grep, Glob\n---\n",  # commas are fine, only ': ' breaks
        "---\nargument-hint: <risk row number>\n---\n",
        "---\ndescription: ends with a colon:\n---\n",  # no trailing space, still valid YAML
    ],
)
def test_valid_frontmatter_reports_nothing(text: str) -> None:
    assert frontmatter_problems(text) == []


def test_body_prose_after_the_closing_marker_is_not_scanned() -> None:
    """The check stops at the closing ---; body text routinely contains 'word: thing'."""
    text = "---\nname: x\n---\n\nUse this before: README edits, ADRs, and docstrings.\n"
    assert frontmatter_problems(text) == []


def test_every_failure_is_reported_with_its_label() -> None:
    text = format_failures([Failure("mypy src", "boom"), Failure("pytest", "1 failed")])
    assert "mypy src failed" in text
    assert "boom" in text
    assert "pytest failed" in text
    assert "1 failed" in text
