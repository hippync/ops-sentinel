# Claude Code harness

The AI-assisted build configuration, committed rather than kept local. The reasoning —
what is delegated, what is refused, and why — is in
[`docs/agentic-workflow.md`](../docs/agentic-workflow.md); this file is just the map.

| Path | What it does |
|---|---|
| [`settings.json`](settings.json) | Allowlist for read-only and test commands; registers the edit hook |
| [`hooks/post_edit_checks.py`](hooks/post_edit_checks.py) | ruff + mypy + pytest on `agents/**/*.py` edits; the risk row 6 IAM drift check on `ActionType` and policy edits; YAML frontmatter validity on the definitions in this directory |
| [`hooks/test_post_edit_checks.py`](hooks/test_post_edit_checks.py) | The hook's own tests — 41 cases over path classification, payload parsing, and frontmatter validity |
| [`hooks/ruff.toml`](hooks/ruff.toml) | Mirrors `agents/pyproject.toml`, because `cd agents && ruff check .` cannot reach this directory |
| [`agents/adversarial-reviewer.md`](agents/adversarial-reviewer.md) | Re-runs the stance of [the Sprint 0 review](../docs/review-2026-09-07.md) against a diff. Read-only |
| [`agents/risk-row-auditor.md`](agents/risk-row-auditor.md) | Checks that register row → module → test is still 1:1. Read-only |
| [`commands/rule.md`](commands/rule.md) | `/rule <n>` — implement a Validator rule from its risk row, tests first |
| [`commands/sprint-status.md`](commands/sprint-status.md) | `/sprint-status` — reconcile `docs/sprints.md` against the actual tree |
| [`commands/adr.md`](commands/adr.md) | `/adr <topic>` — draft in the house format; never marks one `Accepted` |

[`CLAUDE.md`](../CLAUDE.md) at the repo root holds the standing context: build status, the
conventions, and the hard rules.

## The hook is held to the standard it enforces

`post_edit_checks.py` is Python with pure, unit-tested decision logic rather than a shell
script, for the same reason `check()` returns a `RuleOutcome` instead of raising: the
dangerous failure mode is not crashing, it is **passing silently**. An unverified check
that gates the build would be the exact thing this repo argues against. Editing the hook
runs the hook's own tests.

Note that those tests run locally only — CI's path filters do not cover `.claude/`.

## Setup

The hook needs the dev environment; without it, it says so rather than passing quietly.

```bash
python3.12 -m venv agents/.venv
agents/.venv/bin/pip install -e "agents[dev]"
```

Personal overrides go in `settings.local.json`, which is gitignored.
