# Ops Sentinel — working notes for Claude

Multi-agent AI-SRE pipeline whose point is the **deterministic safety gate**, not the diagnosis.
`agents/src/ops_sentinel/validator/` is the portfolio piece; everything else exists to give it
something real to reject.

**Status: Sprint 1 of 6.** Most of `validator/` is still `raise NotImplementedError("Sprint 1")`.
Never describe a stub as working code — in the README, a docstring, a commit message, or a reply.
`docs/sprints.md` is the source of truth for what is done.

## The spec lives in the repo

Do not invent requirements. For any Validator rule, the spec is three things that already exist:

1. the numbered row in `docs/ops-sentinel-risk-register.md`
2. the ADRs it cites (`docs/adr/`)
3. **the module's own docstring** — these are precise, and where a docstring resolves a design
   fork it supersedes the register's original wording. `secrets.py` is the example: the register
   says "scrubs/rejects", the module says *rejects only*, and explains why scrubbing would break
   the `proposal_hash` chain. The docstring wins.

`docs/architecture.md` covers stage boundaries. `docs/review-2026-09-07.md` is an adversarial
review of this repo — read it before writing any prose about the project.

## Style exemplars — match these, don't improvise

- `agents/src/ops_sentinel/validator/rollback.py`
- `agents/tests/unit/validator/test_rollback.py`

The conventions they encode:

- One module per risk row, one test file per module, 1:1.
- Module docstring opens `Risk row N — <name>`, explains what the rule covers **and what it does
  not**, and closes with `Residual risk:`.
- Module constants `RISK_ROW` and `RULE`.
- `check(...)` returns a `RuleOutcome`. It **never raises** — a crashing validator fails open.
  Every rule has a `test_..._never_raises` equivalent.
- `RuleOutcome.subject` distinguishes `action` from `rollback_action`; rules that run over both
  must set it.
- Failure `detail` names the offending value, so the audit log is readable without the code.
- Tests mutate the shared `clean_proposal` fixture (`agents/tests/conftest.py`) rather than
  building proposals inline.

## Hard rules

- **No model call in `validator/` or `executor/`.** ADR-0003. A gate judged by an LLM is not a
  gate. This is not negotiable for convenience.
- **Never weaken a test to make it pass.** If a test is wrong, say so and stop.
- **Never write a number into a doc that has not been measured.** Miss rates, time savings,
  false-positive rates are targets until there is a committed results file. The README already
  had to have uncited statistics removed once.
- **Never choose a threshold.** `CONFIDENCE_FAST_PATH_MIN`, `MAX_DESIRED_COUNT`, the ADR-0009 miss
  rate and kill criterion are human judgment calls, made before measurement. Propose options and
  their trade-offs; the author picks.
- **Never label an evaluation scenario** (ADR-0009). AI-written labels scored by AI-written rules
  is the circularity the whole harness exists to avoid.
- **Never set an ADR to `Status: Accepted`.** Draft it as `Proposed`.
- `proposal_hash` is a `computed_field`, never a settable field.
- Limits are enforced outside the thing they limit — the Worker's iteration cap lives in the
  graph runtime, not the prompt (risk row 3).

## Prose follows code

The repo's known failure mode, named in its own review: excellent writing about barely-implemented
code. So a README, ADR, or docs change needs a code change behind it — in the same commit or a
later one, never earlier. If asked to document something unbuilt, say so and offer to build it.

## Commands

```bash
cd agents && pytest -q          # tests
cd agents && ruff check .       # lint
cd agents && mypy src           # types (strict)
python3 scripts/check_iam_scope.py   # risk row 6 drift: ActionType vs executor-policy.json
cd sandbox-app && ./mvnw -B verify   # Java
```

CI runs all of these, path-filtered (`.github/workflows/ci.yml`).

## Commits

Imperative, naming the behaviour change, in the voice of the existing history:

```
Implement the rollback rule end to end; resolve two design forks
Make proposal_hash unforgeable and action params typed
Fix CI path filters; verify row 4 cannot be enforced in IAM
```

Not `feat: Add framework alignment section to README`. `docs/sprints.md` says the history is part
of the artifact. Commit per module. Tick the sprint checkbox in the **same** commit as the code
that earns it, never ahead of it.
