---
description: Implement the Validator rule for a risk register row, tests first
argument-hint: <risk row number>
---

Implement the Validator rule for risk register row **$1**.

This applies to rows 1–8, and to row 13. Rows 9–12 are specification and are **not** Validator
rules — they are enforced in the Executor or the graph runtime; see the register's "enforced in /
earliest it can land" table before starting one. Row 13 *is* a Validator rule: it lands as
`validator/classification.py` with `RISK_ROW = 13`, consumed by `scoring.py`, and the register's
sub-table is its spec.

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
- each violation the row names is rejected, with a `detail` that names the offending value —
  assert **both** `not outcome.passed` and the `detail` substring, never `detail` alone. A rule's
  pass-path detail can quote the very value its fail path does (`blast_radius` quotes the target
  on both paths), and then a detail-only assertion is satisfied by the pass path and proves nothing
- the rule returns a `RuleOutcome` rather than raising, even on degenerate input — a crashing
  validator fails open, so this test is not optional
- if the rule runs over the rollback action as well as the primary one, both are covered and
  `RuleOutcome.subject` distinguishes them

For each test, be able to say what change to the source would make it fail. If the answer is
"nothing", the test is decoration — rewrite it.

Then prove that rather than asserting it. Once the suite is green, disable each guard in the
source in turn (`if False:` in place of its condition) and confirm at least one test fails for
it; restore the source afterwards. A guard whose removal breaks nothing is untested.

Do not expect the failures to line up one-to-one with the guard, and do not "fix" a test that
fails for a neighbouring one: a `never_raises` test depends on *some* guard rejecting, so it
fails alongside whichever one you switched off, and that is the test working rather than a
broken test. Expect the post-edit hook to go red on each mutation for the same reason — that
is the suite doing its job, not a mistake to revert.

This is the executable form of the paragraph above, and it is not optional: it has already
caught a row 1 test that passed through the pass path while the guard it was meant to cover
was switched off.

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
