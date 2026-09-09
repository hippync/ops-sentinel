---
description: Reconcile docs/sprints.md against what is actually in the tree
---

Report where `docs/sprints.md` and the repository disagree. Both directions matter, but they are
not equally bad: a checkbox ticked ahead of its code is the failure this project's own review
named, and it goes at the top of your report.

## Method

Verify by reading the tree, never by trusting the doc. For the current sprint and every earlier
one:

1. For each `[x]`, find the artifact that earns it — the module (implemented, not
   `raise NotImplementedError`), the tests, the ADR, the script. Name the file.
2. For each `[ ]`, check whether it is in fact done. Work that shipped but was never ticked is
   also drift, and it undersells the repo.
3. Run the checks so the report rests on a current result, not an assumption:
   `cd agents && .venv/bin/pytest -q`, `.venv/bin/ruff check .`, `.venv/bin/mypy src`, and
   `agents/.venv/bin/python scripts/check_iam_scope.py`.
4. Check the README's build-status banner against what you found. It claims a specific sprint and
   a specific set of working features; if either has moved, that is a finding — the banner is the
   first thing a reviewer reads.

## Output

- **Current sprint:** N of M checkboxes complete, with the open ones listed in the order
  `docs/sprints.md` puts them.
- **Ticked without code** — worst first, with the file that should exist and does not.
- **Done but unticked.**
- **README banner accuracy** — accurate, or what it now overstates or understates.
- **Check results** — tests passing, lint, types, IAM drift.

Report only. Do not tick checkboxes, edit the README, or commit; the author decides what the
status is.
