#!/usr/bin/env python3
"""PostToolUse hook: run this repo's own CI checks the moment a file is edited.

Why this exists: CI is otherwise the only thing that runs ruff/mypy/pytest and the risk
row 6 drift check. That is a long feedback loop for an agent writing code — it produces a
plausible-looking module, moves on, and the failure surfaces minutes later in a push.
Running the checks here puts the failure in the same turn as the edit.

Three concerns, keyed off the edited path:

    agents/**/*.py                  -> ruff (file) + mypy (src) + the full pytest suite
    schemas/models.py               -> scripts/check_iam_scope.py
    infra/policies/*.json           -> scripts/check_iam_scope.py
    .claude/hooks/*.py              -> this file's own tests

The IAM check is here because risk row 6's guarantee holds only if `ActionType` and
`executor-policy.json` agree, and those two files get edited in different sessions.

WHY PYTHON, AND WHY THE DECISION LOGIC IS PURE: the failure mode that matters for a check
like this is not crashing, it is passing silently — the same failure mode the Validator's
`check()` functions are written to avoid. So `classify`, `relative_path` and `read_payload`
take no I/O and are unit-tested in `test_post_edit_checks.py`, and only `main` touches the
filesystem. A hook nothing tests is exactly the kind of unverified check this repo argues
against.

Runs under ambient `python3`, NOT `agents/.venv` — reporting that the venv is missing is
one of its jobs. Standard library only, and no syntax newer than 3.9.

Exit 2 feeds stderr back to Claude as a blocking error; exit 0 is silent success.
"""

from __future__ import annotations

import json

# Runs this repo's own pinned dev tools with a fixed argv and no shell.
import subprocess  # noqa: S404
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import IO, NamedTuple

# `from __future__ import annotations` above makes every annotation a lazily-evaluated
# string, so `X | None` and `list[...]` are safe here despite the 3.9 floor.

MISSING_VENV = (
    "agents/.venv is missing, so the edit checks did not run. Create it with: "
    'python3.12 -m venv agents/.venv && agents/.venv/bin/pip install -e "agents[dev]"'
)

IAM_TRIGGER_FILES = frozenset({"agents/src/ops_sentinel/schemas/models.py"})
IAM_TRIGGER_DIR = "infra/policies/"
HOOK_DIR = ".claude/hooks/"
CLAUDE_DIR = ".claude/"


class Checks(NamedTuple):
    """Which check groups an edited path calls for."""

    python: bool
    iam: bool
    hook_self_test: bool
    frontmatter: bool

    def any_requested(self) -> bool:
        return self.python or self.iam or self.hook_self_test or self.frontmatter


class Failure(NamedTuple):
    label: str
    output: str


def classify(rel: str) -> Checks:
    """Decide which checks a repo-relative path calls for. Pure; no filesystem access."""
    parts = rel.split("/")
    # An edit inside the virtualenv is not this project's source, and running the whole
    # suite because a dependency changed on disk would be noise.
    inside_venv = ".venv" in parts

    python = rel.startswith("agents/") and rel.endswith(".py") and not inside_venv
    iam = rel in IAM_TRIGGER_FILES or (
        rel.startswith(IAM_TRIGGER_DIR) and rel.endswith(".json")
    )
    hook_self_test = rel.startswith(HOOK_DIR) and rel.endswith(".py")
    frontmatter = rel.startswith(CLAUDE_DIR) and rel.endswith(".md")
    return Checks(
        python=python, iam=iam, hook_self_test=hook_self_test, frontmatter=frontmatter
    )


def frontmatter_problems(text: str) -> list[str]:
    """Catch the one YAML frontmatter mistake this repo has actually made.

    An unquoted scalar containing ": " is read by YAML as a nested mapping, so
    `description: Use this before prose: README edits` fails with "mapping values are not
    allowed in this context" — which is how GitHub refused to render an agent definition.
    The subagent's description is what tells Claude when to use it, so a break here is
    silent in exactly the way this hook exists to prevent.

    Deliberately NOT a YAML parser: it checks one known failure, and says so, rather than
    reimplementing YAML badly and implying broader coverage than it has.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return []

    problems = []
    for raw in lines[1:]:
        if raw.strip() == "---":
            break
        key, sep, value = raw.partition(":")
        # Only top-level `key: value` lines; nested and continuation lines are out of scope.
        if not sep or not key.strip() or raw[:1] in (" ", "\t", "-"):
            continue
        value = value.strip()
        if not value:
            continue
        quoted = len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'"
        if not quoted and ": " in value:
            problems.append(
                f"{key.strip()}: unquoted value contains ': ', which YAML reads as a "
                f"nested mapping. Wrap the value in double quotes."
            )
    return problems


def relative_path(file: str, repo_root: Path) -> str | None:
    """Repo-relative POSIX path, or None if the edit is outside the repo.

    Deliberately does not call `resolve()`: on macOS that rewrites /tmp to /private/tmp
    and would make the comparison depend on symlink layout.
    """
    if not file:
        return None
    path = Path(file)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return None


def read_payload(stream: IO[str]) -> str:
    """Pull the edited file path out of the hook's stdin JSON. Never raises."""
    try:
        data = json.load(stream)
    except ValueError:  # JSONDecodeError and UnicodeDecodeError both subclass this
        return ""
    if not isinstance(data, dict):
        return ""
    for section, key in (("tool_response", "filePath"), ("tool_input", "file_path")):
        block = data.get(section)
        if isinstance(block, dict):
            value = block.get(key)
            if isinstance(value, str) and value:
                return value
    return ""


def run(label: str, args: Sequence[str], cwd: Path) -> Failure | None:
    """Run one check. Returns a Failure on non-zero exit, None on success."""
    try:
        proc = subprocess.run(  # noqa: S603
            list(args), cwd=str(cwd), capture_output=True, text=True
        )
    except OSError as exc:  # tool missing or not executable — report, never swallow
        return Failure(label, str(exc))
    if proc.returncode != 0:
        return Failure(label, (proc.stdout + proc.stderr).strip())
    return None


def format_failures(failures: Sequence[Failure]) -> str:
    return "".join(f"--- {f.label} failed ---\n{f.output}\n" for f in failures)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    venv = repo_root / "agents" / ".venv"

    rel = relative_path(read_payload(sys.stdin), repo_root)
    if rel is None:
        return 0

    checks = classify(rel)
    if not checks.any_requested():
        return 0

    # Runs before the venv gate: it needs no tooling, and a broken agent definition
    # should still be reported on a machine that has not been set up yet.
    if checks.frontmatter:
        try:
            problems = frontmatter_problems((repo_root / rel).read_text(encoding="utf-8"))
        except OSError as exc:
            problems = [str(exc)]
        if problems:
            sys.stderr.write(format_failures([Failure(f"frontmatter {rel}", "\n".join(problems))]))
            return 2
        if not checks.python and not checks.iam and not checks.hook_self_test:
            return 0

    if not (venv / "bin" / "python").exists():
        # Say so out loud rather than passing silently. A check that quietly does nothing
        # is worse than no check, especially in this repo.
        print(json.dumps({"systemMessage": MISSING_VENV}))
        return 0

    agents = repo_root / "agents"
    results: list[Failure | None] = []

    if checks.python:
        results.append(
            run(
                f"ruff check {rel}",
                [str(venv / "bin" / "ruff"), "check", str(repo_root / rel)],
                agents,
            )
        )
        results.append(run("mypy src", [str(venv / "bin" / "mypy"), "src"], agents))
        results.append(run("pytest", [str(venv / "bin" / "pytest"), "-q"], agents))

    if checks.iam:
        # Risk row 6: the policy and the ActionType enum must agree, or the guarantee is fiction.
        results.append(
            run(
                "check_iam_scope.py",
                [str(venv / "bin" / "python"), "scripts/check_iam_scope.py"],
                repo_root,
            )
        )

    if checks.hook_self_test:
        results.append(
            run("hook self-test", [str(venv / "bin" / "pytest"), "-q", HOOK_DIR], repo_root)
        )

    failures = [f for f in results if f is not None]
    if failures:
        sys.stderr.write(format_failures(failures))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
