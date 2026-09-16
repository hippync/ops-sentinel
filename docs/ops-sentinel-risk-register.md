# Ops Sentinel — Risk register & business case (block 1)

**Purpose of this document:** before writing any orchestration code, this register maps the risks of letting an agentic system act on production infrastructure to the specific developer gap each risk represents, and the specific Ops Sentinel mechanism designed to close it. This is the foundation the rest of the business case builds on.

**Framing:** on-call engineers currently lose the first ~45 minutes of most incidents to investigation before they can even start deciding what to do. Ops Sentinel's value is compressing that investigation phase — but only if the compression itself doesn't introduce new, worse risks. This register exists to prove that trade-off is sound before a single line of orchestration code is written.

---

## Risk register

| # | Risk category | What could go wrong | Detection signal | Hard rule (deterministic, not LLM-judged) | Residual risk | Developer gap this closes |
|---|---|---|---|---|---|---|
| 1 | **Execution risk (blast radius)** | Fix targets more resources than intended (e.g. a pattern match instead of a specific resource ID) | Worker's proposed action references a wildcard/tag pattern instead of a single resource ID | Validator rejects any action that isn't scoped to a single, named resource ID — blank, a wildcard (`*?[]`), a tag selector, or several resources in one string. Rejection is the only disposition this rule has: a `RuleOutcome` carries `passed` plus `detail` and no approval-path channel, so "route to strict approval" was never expressible here — that is scoring's concern (row 8). Runs over the rollback action too | Two resources sharing the same ID by config error (rare, but not zero). The pattern set is also literal rather than a regex: regex metacharacters and alternation between two names are not detected, which is residual rather than a hole only because the Executor and its IAM policy both require an exact service ARN | Today, a tired on-call engineer under time pressure is the only check against a broad, unscoped fix — no consistent second check exists |
| 2 | **Data risk** | Diagnosis step surfaces or the fix proposal includes credentials, secrets, or PII pulled from logs | Proposal text matches credential-shaped strings, key patterns, or known PII formats | Validator scrubs/rejects any proposal containing raw log content matching secret or PII patterns before it's shown to a human | Novel secret formats not covered by pattern rules | Logs routinely contain sensitive fragments today; there's no automated gate before a human reads a diagnosis — this adds one |
| 3 | **Cost risk — LLM calls** | Worker loops indefinitely, burning tokens without converging (a "denial-of-wallet" pattern) | Iteration count exceeds a fixed cap without a validated proposal | Hard iteration cap on the Worker agent; on cap breach, fail loudly and page a human instead of continuing | None of significance if the cap is enforced outside the LLM's own control | No equivalent exists in ad hoc Copilot-style agent use — nothing currently stops a run from silently spinning |
| 4 | **Cost risk — infrastructure** | Proposed fix itself causes unbounded spend (e.g. an autoscale fix with no ceiling) | Proposal includes a scale/resize action with no upper bound specified | Validator enforces a fixed max-instance-count / max-spend-delta rule, independent of the Worker's own reasoning | A legitimate spike that genuinely needs more than the ceiling allows. Not IAM-bounded ([ADR-0007](adr/0007-row-4-cannot-live-in-iam.md)): if the code checks fail, spend is bounded only by account-level limits and detection — see the pre-mortem answer below | Manual fixes today are bounded by the engineer's judgment in the moment; an automated system needs that same ceiling made explicit and enforced in code |
| 5 | **Security risk — prompt injection** | Log content or alert text contains attacker- or bug-crafted text that looks like an instruction to the Worker or Validator | Proposal or reasoning trace references an action not derivable from the actual incident data | Treat all ingested log/alert content as data, never as instructions; test this explicitly with a crafted injection case in the demo | Novel injection techniques not covered by the test suite | Almost no student or portfolio agent projects test for this — it is a known, cited failure mode industry-wide and currently untested in most agent tooling |
| 6 | **Security risk — over-privileged execution** | Executor's IAM role has broader access than its known action set requires | Executor role includes permissions not exercised by any defined action | Executor IAM role scoped to the minimum action set at deploy time — even a fully manipulated agent cannot act outside that list | Privilege scope must be re-reviewed if the action set grows | This is the strongest guarantee in the whole system, and it doesn't depend on the Validator being correct — except for row 4's ceiling, which IAM cannot express ([ADR-0007](adr/0007-row-4-cannot-live-in-iam.md)) — most ad hoc agent tooling grants broad access "just in case" |
| 7 | **Availability / cascading risk** | The fix itself triggers a new incident (e.g. a restart causing a cold-start cascade elsewhere) | No rollback plan attached to the proposal | Validator rejects any proposal with no defined rollback step | Rollback plans can be wrong or untested themselves | Manual fixes today often lack a documented rollback too — this makes the omission visible and blocking, instead of silent |
| 8 | **Trust / reputational risk** | Validator too permissive → one bad auto-approved fix kills trust in the system; too strict → engineers route around it | Approval rate and false-positive/false-negative rate over time | Explicit, documented tolerance for false-positive rate as a designed trade-off, not an accident | Any threshold is a judgment call and will need tuning | Today there's no equivalent because there's no automated system to (dis)trust — this row exists specifically because Ops Sentinel introduces this new risk, it doesn't reduce an existing one |

---

## Approval-path scoring rubric

Rather than a single approve/reject signal, each proposed fix is scored on three axes to decide its approval path:

- **Severity** — how bad if the fix is wrong
- **Confidence** — how sure the Worker agent is, based on diagnostic signal strength
- **Reversibility** — whether a clean rollback exists

**Low severity + high confidence + reversible** → fast-path human approval (single click, pre-validated)
**High severity OR irreversible** → strict gate regardless of confidence — always full review, never fast-pathed

This keeps the Validator's judgment inspectable and defensible rather than a black box, and makes the "not fully restrictive" design goal a deliberate policy instead of a guess.

---

## Pre-mortem question (answer before writing orchestration code)

> For the specific sandbox app used in v1: if every check in this register silently failed at once, what is the worst plausible outcome — and is that outcome already bounded by IAM scoping alone (row 6), independent of whether the Validator logic works correctly?

If the answer isn't a confident yes, the IAM scope for the Executor needs to shrink before v1 starts, not after.

### Answer (2026-09-15): no — not a confident yes

Worked under [ADR-0007](adr/0007-row-4-cannot-live-in-iam.md) as revised on the same date. "Every check failed" includes the Validator, the approval gate and the Executor's re-check, so what remains is the Executor's IAM policy and the sandbox account itself.

| Worst outcome if every check fails | Bounded by IAM? | What bounds it instead |
|---|---|---|
| Scale-out with no ceiling — unbounded spend | **No.** No condition key exists for `desiredCount`, and Service Auto Scaling max capacity does not block the call | Only account-level limits and time-to-detection. **Choice of bound still open** — see below |
| Service pointed at another family's task definition, and that family's task role | **Yes**, provided [ADR-0010](adr/0010-pin-updateservice-condition-keys.md) (Proposed) holds: an `ecs:task-definition` condition keeps it on the `orders-api` family. This pins the family name, not its task role — it holds because the Executor cannot register new revisions | — |
| Rollback to a known-bad revision inside the family (chaos #1's, for one) | No | Nothing. Residual: availability of one sandbox service with no real users |
| `desiredCount` set to 0 | No | Nothing. Same residual |
| Tasks moved to other subnets, or a wider security group attached | Subnet: a condition key exists, not pinned until subnet IDs exist. Security group: no key exists | Account hygiene, once the account exists: no permissive security group to attach (a Sprint 5 item) |
| Plaintext secrets read from any task definition | No — `DescribeTaskDefinition` has no resource-level permissions, so it is granted on `*` | Bounded only if task definitions reference secrets through Secrets Manager or SSM, never plain `environment` (a Sprint 5 item) |
| A secret shown in Slack or the audit log (rows 2, 5) | Not IAM's domain | Sandbox-only credentials that can be rotated |

**In one line:** everything except spend and one service's availability can be bounded by IAM plus account hygiene, once Sprint 5's hygiene items exist. Spend cannot — outside this repo's code, its only bounds are account-level limits and how quickly someone notices.

**What the "no" shrank.** The Executor's `ecs:UpdateService` grant now carries two conditions, proposed in [ADR-0010](adr/0010-pin-updateservice-condition-keys.md): `ecs:task-definition` limited to the `orders-api` family, and `ecs:enable-execute-command` fixed to `false`. `scripts/check_iam_scope.py` fails if either is removed, widened, or has its operator changed, and a committed test covers each case. Both use `IfExists`, which is read from the AWS docs rather than observed; Sprint 5 confirms it with real denied calls.

**Why "before v1 starts" is still met.** No Executor role exists before Sprint 5 — Sprints 1–3 run a fake executor. The rule's "before v1 starts" therefore means "before the role is applied", and `docs/sprints.md` puts the spend bound ahead of applying the role.

**Still open — the author's call.** How to bound spend outside the code. Each option is either a block or a lagging correction:

- **Fargate vCPU service quota** — a block, if the quota can be set low enough. Whether a quota can be lowered without a support request is **unverified**.
- **AWS Budgets action attaching a deny policy to the Executor role** — a lagging correction. Budgets act on billing data that lags usage, and a deny stops further calls without scaling down tasks already running.
- **A separate actuator role holding `ecs:UpdateService`**, which enforces the ceiling itself — a block, but made of code, and it changes the Executor's design (an ADR-0004 input).

Removing `set_desired_count` from the action set would not help: `UpdateService` permits `desiredCount` changes whether or not an `ActionType` uses them.

**Precondition this answer assumes.** The Executor's credentials are separate from the pipeline's. If the Worker's process can act with the Executor role, row 6 bounds nothing. This is an input to [ADR-0004](adr/0004-pipeline-runtime.md).

---

## Status

This is block 1 of the business case. Not yet covered, planned for later blocks: cost-benefit framing against the 45-minute baseline, the chosen sandbox app and specific incident types for the v1 demo, and the presentation/demo-video plan.
