# Scripts

Local development and demo drivers. Built alongside the sprints that need them.

| Script | Sprint | Purpose |
|---|---|---|
| `check_iam_scope.py` | 0 | Risk row 6 drift check — runs in CI |
| `replay-alarm.sh` | 1 | Feed a recorded alarm payload to the pipeline without touching AWS |
| `eval-extraction.py` | 3 | Run the decision-point harness over the recorded span sets and write the miss rate to a committed results file |
| `dev-up.sh` | 4 | Postgres + sandbox app locally via docker-compose |
| `trigger-chaos.sh` | 4 | Fire a chaos endpoint against the internal listener |
| `deploy-broken-revision.sh` | 5 | Chaos #1 — roll out a deliberately broken task definition |

`replay-alarm.sh` matters more than it looks: it decouples the whole pipeline from the AWS
wiring, which was the plan's riskiest dependency. It was pulled forward to Sprint 1 in the
2026-09-07 resequence — the sprint numbers above follow `docs/sprints.md` as it stands now,
not the pre-resequence plan.

`eval-extraction.py` is the one that produces a deliverable rather than a convenience. It runs
in CI with no AWS credentials and no Slack workspace, which is what makes
[ADR-0009](../docs/adr/0009-extraction-evaluation-harness.md)'s miss rate reproducible by
someone who just cloned the repo.
