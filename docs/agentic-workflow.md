# The agentic workflow used to build this

**Status:** adopted 2026-09-08, start of Sprint 1 · **Scope:** how Ops Sentinel is built with
AI assistance, and where that assistance is deliberately refused

This repository is built with Claude Code. Documenting that is not a disclaimer — it is the same
argument the system makes, applied to its own construction. Ops Sentinel's thesis is that agentic
tooling fails by *lacking self-validation*: it produces plausible-looking output with no signal
about whether it is safe to trust. A repo arguing that, built by pointing an agent at a spec and
committing whatever came back, would refute itself.

So the build has a gate too.

## The problem this workflow is shaped around

The [Sprint 0 review](review-2026-09-07.md) found the honest version of where this repo stood:
a README describing an A-grade system, and about forty lines of executable logic, six of which
were `raise NotImplementedError`. Its verdict — *"as of today the repo reads as someone who is
very good at writing about engineering"* — is the specific risk an LLM makes worse, because
fluent prose about unbuilt systems is the thing these tools are best at.

Every choice below follows from that. The workflow is tuned to make **tested executable code**
the cheap path and **more prose** the expensive one.

## The loop

One `docs/sprints.md` checkbox is one session.

1. **Plan mode first** for anything touching more than one file or resolving a design fork.
   The prompt points at paths rather than pasting content: *"Implement risk row 4, the cost
   ceiling. Spec is the row in the risk register, ADR-0007, and the docstring already in
   `cost_ceiling.py`. Match `rollback.py`."* The docs are a good enough spec to be used as one.
2. **Tests before implementation.** Every Validator module's docstring already names its failure
   modes, so the tests are derivable before the code exists. This is also what keeps the
   [ADR-0009](adr/0009-extraction-evaluation-harness.md) discipline visible in git order.
3. **Implement.** A `PostToolUse` hook runs `ruff`, `mypy` and the full pytest suite on every edit
   to `agents/**/*.py`, and the risk row 6 IAM drift check on every edit to `ActionType` or the
   Executor policy. Failures land in the same turn as the edit rather than in CI minutes later.

   The hook is written in Python rather than shell, and its decision logic is pure and unit
   tested, for one reason: the failure mode that matters for a check like this is not crashing,
   it is **passing silently** — the same failure mode `check()` returning a `RuleOutcome` instead
   of raising exists to avoid. An untested hook is the kind of unverified check this repo argues
   against everywhere else, so editing the hook runs the hook's own tests.
4. **Review.** `/code-review high` on the diff, then the `adversarial-reviewer` subagent on
   anything containing prose. That agent runs the stance of the Sprint 0 review, which is the
   review that produced the resequence, the removed statistics, and ADR-0007.
5. **Security review** before committing anything touching `executor/`, `injection.py`,
   `secrets.py`, or the IAM policy.
6. **Commit per module.** The `docs/sprints.md` checkbox is ticked in the same commit as the code
   that earns it — never earlier. On a portfolio repo the history is part of the artifact.
7. **Clear context between checkboxes.** A Validator session should not carry Terraform context.

## Where Claude is trusted, and where it is not

| Surface | Delegation |
|---|---|
| `sandbox-app/` (Java), `infra/` (Terraform), `scripts/` | Large chunks, diff reviewed. This is scaffolding that exists to give the gate something to reject. |
| `validator/`, `executor/`, `schemas/` | Tests first, small diffs, every one reviewed. This is the portfolio piece. |
| ADRs, README, risk register | Claude drafts structure and prose. The author owns every claim, and every `Status: Accepted`. |
| **The ~20 evaluation scenario labels** | **Never.** See below. |
| **Threshold values** — the miss rate, the kill criterion, `CONFIDENCE_FAST_PATH_MIN`, `MAX_DESIRED_COUNT` | **Never.** See below. |

### The two refusals, and why they are load-bearing

**Labels.** [ADR-0009](adr/0009-extraction-evaluation-harness.md) measures the extraction layer's
miss rate against ~20 scenarios, each with its critical decision labeled by hand, in a commit that
precedes any extraction rule. The commit order is the only evidence the labels were not fitted to
the rules. If an LLM wrote the labels, the published number would be an LLM's rules scored against
an LLM's ground truth — a closed loop reporting on itself, which is the exact failure the harness
exists to detect. The labels are handwritten, and the caveat that they have a single labeler is
published alongside the result.

**Numbers.** Risk row 8 makes the false-positive tolerance a *designed trade-off, decided before
the demo rather than justified after it*. A threshold an agent picked mid-implementation is a
threshold chosen to make the tests pass. These are the author's judgment calls, committed before
the first measurement.

Both refusals cost time. Both are the difference between a measurement and a demo.

## The three anti-patterns

- **Prose ahead of code.** Asking for a README section about an unbuilt feature is exactly what
  the Sprint 0 review flagged. Code first, always; docs changes need a code change behind them.
- **Treating a green suite as evidence.** The question is not whether tests pass but what change
  would make them fail. `test_rejection_never_raises` is the model — it tests a failure mode.
- **Long sessions across sprint boundaries.** Context bleed produces code that half-matches two
  conventions.

## What is in the repo

| Path | What it does |
|---|---|
| `CLAUDE.md` | Standing context: status, conventions, hard rules, the exemplar files to match |
| `.claude/settings.json` | Read-only/test command allowlist; the `PostToolUse` check hook |
| `.claude/hooks/post_edit_checks.py` | ruff + mypy + pytest on Python edits; IAM drift check on schema and policy edits |
| `.claude/hooks/test_post_edit_checks.py` | The hook's own tests — it is held to the standard it enforces |
| `.claude/agents/adversarial-reviewer.md` | The Sprint 0 review stance, repeatable, read-only |
| `.claude/agents/risk-row-auditor.md` | Verifies register → module → test traceability still holds |
| `.claude/commands/rule.md` | `/rule <n>` — implement a Validator rule from its risk row, tests first |
| `.claude/commands/sprint-status.md` | `/sprint-status` — reconcile `docs/sprints.md` against the tree |
| `.claude/commands/adr.md` | `/adr <topic>` — draft in the house format; never marks one Accepted |

Personal overrides (`.claude/settings.local.json`) are gitignored. Everything else here is
committed, because a workflow that cannot be inspected is the same kind of claim this project
declines to make anywhere else.

## Local setup

The hooks need the dev environment to exist:

```bash
python3.12 -m venv agents/.venv
agents/.venv/bin/pip install -e "agents[dev]"
```

Without it the hook says so out loud rather than passing silently — a check that quietly does
nothing is the failure mode this repo is about.
