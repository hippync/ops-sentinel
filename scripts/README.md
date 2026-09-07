# Scripts

Local development and demo drivers. Built alongside the sprints that need them.

| Script | Sprint | Purpose |
|---|---|---|
| `dev-up.sh` | 2 | Postgres + sandbox app locally via docker-compose |
| `trigger-chaos.sh` | 2 | Fire a chaos endpoint against the internal listener |
| `deploy-broken-revision.sh` | 3 | Chaos #1 — roll out a deliberately broken task definition |
| `replay-alarm.sh` | 4 | Feed a recorded alarm payload to the pipeline without touching AWS |

`replay-alarm.sh` matters more than it looks: it decouples Sprint 4 from Sprint 3's AWS
wiring, which is the plan's riskiest dependency.
