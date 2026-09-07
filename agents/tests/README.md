# Tests

| Path | What it proves |
|---|---|
| `unit/validator/` | Each Validator rule rejects its crafted violation and passes the clean case. One test file per rule module. |
| `integration/` | Graph topology: no path from `worker` to `executor` bypasses `validator` and `approval`. |
| `fixtures/` | Proposal fixtures — one clean, one violation per risk row, plus the crafted prompt-injection case. |

The injection test (risk row 5) is not optional. It is the check that chaos trigger #3
exists to prove, and one of the four things the cut-line list in `docs/sprints.md` says
is never cut.
