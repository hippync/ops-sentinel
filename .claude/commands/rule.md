---
description: Implement the Validator rule for a risk register row, tests first
argument-hint: <risk row number>
---

Implement the Validator rule for risk register row **$1**.

## Read the spec before writing anything

The spec already exists in three places. Read all three; do not invent requirements.

1. Row $1 of `docs/ops-sentinel-risk-register.md` — the risk, the hard rule, the residual risk.
2. Any ADR the row or the module cites, in `docs/adr/`.
3. **The module's own docstring**, already written in `agents/src/ops_sentinel/validator/`. This
   is the most precise of the three and it resolves design forks the register left open. Where it
   contradicts the register, the docstring wins.

Then read `agents/src/ops_sentinel/validator/rollback.py` and
`agents/tests/unit/validator/test_rollback.py`. They are the pattern; match them rather than
improvising a new one.

## Write the tests first

The docstring names the failure modes, so the tests are derivable before the implementation is.
Write them first, watch them fail, then implement. Cover:

- the clean case passes (use the `clean_proposal` fixture from `agents/tests/conftest.py`, mutated
  away from — do not build proposals inline)
- each violation the row names is rejected, with a `detail` that names the offending value
- the rule returns a `RuleOutcome` rather than raising, even on degenerate input — a crashing
  validator fails open, so this test is not optional
- if the rule runs over the rollback action as well as the primary one, both are covered and
  `RuleOutcome.subject` distinguishes them

For each test, be able to say what change to the source would make it fail. If the answer is
"nothing", the test is decoration — rewrite it.

## Then implement

Keep `RISK_ROW` and `RULE`. No model call — ADR-0003 is not negotiable for convenience. If the
rule needs a threshold, read it from `agents/src/ops_sentinel/config.py`; if the threshold does
not exist there yet, stop and ask. Threshold values are the author's judgment call, made before
measurement, and you do not choose them.

## Finish

The post-edit hook runs ruff, mypy and pytest on every edit, so failures surface as you go. When
green, report:

- what the rule rejects and what it deliberately does not (the residual risk, in the row's own terms)
- any place the register, an ADR, or the docstring turned out to be wrong or underspecified —
  say so rather than quietly implementing around it
- the exact `docs/sprints.md` checkbox this closes

Do not tick the checkbox or commit. Both happen together, in one commit, after the author reviews.
