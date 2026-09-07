# Ops Sentinel — Risk register & business case (block 1)

**Purpose of this document:** before writing any orchestration code, this register maps the risks of letting an agentic system act on production infrastructure to the specific developer gap each risk represents, and the specific Ops Sentinel mechanism designed to close it. This is the foundation the rest of the business case builds on.

**Framing:** on-call engineers currently lose the first ~45 minutes of most incidents to investigation before they can even start deciding what to do. Ops Sentinel's value is compressing that investigation phase — but only if the compression itself doesn't introduce new, worse risks. This register exists to prove that trade-off is sound before a single line of orchestration code is written.

---

## Risk register

| # | Risk category | What could go wrong | Detection signal | Hard rule (deterministic, not LLM-judged) | Residual risk | Developer gap this closes |
|---|---|---|---|---|---|---|
| 1 | **Execution risk (blast radius)** | Fix targets more resources than intended (e.g. a pattern match instead of a specific resource ID) | Worker's proposed action references a wildcard/tag pattern instead of a single resource ID | Validator rejects any action that isn't scoped to a single, named resource ID; pattern-matched actions always route to strict approval, never fast-path | Two resources sharing the same ID by config error (rare, but not zero) | Today, a tired on-call engineer under time pressure is the only check against a broad, unscoped fix — no consistent second check exists |
| 2 | **Data risk** | Diagnosis step surfaces or the fix proposal includes credentials, secrets, or PII pulled from logs | Proposal text matches credential-shaped strings, key patterns, or known PII formats | Validator scrubs/rejects any proposal containing raw log content matching secret or PII patterns before it's shown to a human | Novel secret formats not covered by pattern rules | Logs routinely contain sensitive fragments today; there's no automated gate before a human reads a diagnosis — this adds one |
| 3 | **Cost risk — LLM calls** | Worker loops indefinitely, burning tokens without converging (a "denial-of-wallet" pattern) | Iteration count exceeds a fixed cap without a validated proposal | Hard iteration cap on the Worker agent; on cap breach, fail loudly and page a human instead of continuing | None of significance if the cap is enforced outside the LLM's own control | No equivalent exists in ad hoc Copilot-style agent use — nothing currently stops a run from silently spinning |
| 4 | **Cost risk — infrastructure** | Proposed fix itself causes unbounded spend (e.g. an autoscale fix with no ceiling) | Proposal includes a scale/resize action with no upper bound specified | Validator enforces a fixed max-instance-count / max-spend-delta rule, independent of the Worker's own reasoning | A legitimate spike that genuinely needs more than the ceiling allows | Manual fixes today are bounded by the engineer's judgment in the moment; an automated system needs that same ceiling made explicit and enforced in code |
| 5 | **Security risk — prompt injection** | Log content or alert text contains attacker- or bug-crafted text that looks like an instruction to the Worker or Validator | Proposal or reasoning trace references an action not derivable from the actual incident data | Treat all ingested log/alert content as data, never as instructions; test this explicitly with a crafted injection case in the demo | Novel injection techniques not covered by the test suite | Almost no student or portfolio agent projects test for this — it is a known, cited failure mode industry-wide and currently untested in most agent tooling |
| 6 | **Security risk — over-privileged execution** | Executor's IAM role has broader access than its known action set requires | Executor role includes permissions not exercised by any defined action | Executor IAM role scoped to the minimum action set at deploy time — even a fully manipulated agent cannot act outside that list | Privilege scope must be re-reviewed if the action set grows | This is the strongest guarantee in the whole system, and it doesn't depend on the Validator being correct — most ad hoc agent tooling grants broad access "just in case" |
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

---

## Status

This is block 1 of the business case. Not yet covered, planned for later blocks: cost-benefit framing against the 45-minute baseline, the chosen sandbox app and specific incident types for the v1 demo, and the presentation/demo-video plan.
