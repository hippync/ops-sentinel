# ADR-0008 — Decision-point extraction between the Validator and the approval gate

**Status:** Accepted · **Date:** 2026-09-08

**Depends on:** [ADR-0005](0005-approval-surface.md) (the surface that renders the cards) and
[ADR-0006](0006-audit-log-store.md) (the store that holds them).
**Measured by:** [ADR-0009](0009-extraction-evaluation-harness.md).

## Context and problem statement

The approval gate hands a human a `FixProposal` and asks them to approve or reject it. The
architecture calls this "an explicit, inspectable safety gate" — and the *gate* is inspectable,
because the Validator's rules are deterministic and its verdict is per-rule. What is not
inspectable is the **path**: the sequence of judgments the Triage and Worker agents made on the
way to that proposal.

So the approver signs something they have no practical means of examining. That is a signature
without a reading: documented responsibility with no epistemic basis behind it. The audit trail
records *that* a named person approved; it does not put that person in a position to have
deserved the authority.

This is an instance of a general problem, not a quirk of this project. Supervision
infrastructure is built for **artifacts** — a diff, a contract, a case file: something a person
reads and signs. Agents produce **trajectories** — tool calls, intermediate state, a final
answer, and a log nobody opens. Legal and professional accountability still attaches to a named
individual either way, so the accountability survives the transition and the epistemic basis
does not.

Ops Sentinel is an unusually good place to attack this because it already has the two things
the problem needs: a human who is formally on the hook, and a pipeline whose safety argument is
written down well enough to say what "the moments that mattered" would even mean.

## Decision drivers

- The approver must be able to *read something* before signing, not merely *see something*.
- Whatever is added must not weaken the gate. Design principle 1 — "the safety gate contains no
  LLM judgment" — and [ADR-0003](0003-no-llm-in-validator.md) are the project's central claim.
- It must be measurable. A layer that produces plausible-looking cards with no signal about
  whether it caught what mattered is the exact failure mode this project exists to argue
  against, reproduced one level up.
- One semester, part-time. The layer has to be cuttable in pieces.

## Considered options

**1. Show the raw trajectory.** Attach the full tool-call log to the approval message. Honest,
zero inference, and useless — it is the log nobody opens, moved somewhere more expensive to
ignore. It converts "no basis" into "a basis nobody will use," which is worse because it looks
like a fix.

**2. Have the Worker explain itself.** Ask the model to summarise its own reasoning into the
proposal. Cheapest option and the most common one in the wild. Rejected: a self-report from the
component being supervised is not supervision, which is the same argument design principle 6
already makes about `iterations_used` — a limit reported by the thing it limits is not a limit.
A self-narrated trajectory is a narrative optimised to be approved.

**3. Extend the Validator.** Add rules that surface judgment moments. Rejected: it conflates two
different jobs. The Validator checks the *output* against explicit rules and its verdict gates
execution. Extraction reads the *path* and gates nothing. Merging them puts non-deterministic
content inside the component whose whole value is being deterministic.

**4. A separate extraction layer between Validator and approval.** Chosen.

## Decision

Insert a **decision-point extraction layer** between the Validator and the approval gate. It
reads OpenTelemetry spans emitted by the pipeline and produces 3–5 `DecisionPoint` records,
each answering four questions:

- **What was chosen** at this moment in the trajectory
- **What alternatives were viable** — the branches not taken that were genuinely available
- **What it rests on** — the evidence or assumption the choice depends on
- **What breaks downstream if it is wrong**

These render above the approve/reject buttons on the ADR-0005 Slack message, and land in the
ADR-0006 register alongside the proposal and the approval.

This is **distinct from the Validator and complementary to it**. The Validator checks the output
against explicit rules; the extractor exposes which moments in the path actually required human
judgment. Neither subsumes the other, and the extractor never re-litigates a rule outcome.

### Six commitments that keep this from weakening the gate

1. **The extractor is not a gate.** It cannot pass, reject, re-score, or modify a proposal. It
   has no edge to the Executor. A reviewer must not be able to read component 4 below as LLM
   judgment creeping into the safety path, because it is not: the classifier's output is display
   text on a card a human reads, never a verdict and never an action.
2. **It never touches `proposal_hash`.** Extraction is read-only over spans plus the proposal.
   Cards are keyed *by* the hash and are never part of the hashed content. This is the same
   lesson `secrets.py` already encodes by rejecting rather than scrubbing: mutating a proposal
   breaks the chain the Executor verifies against.
3. **Extraction failure downgrades fast-path to strict.** Fail-closed in the repo's idiom
   without blocking incident response. A card reading "extraction unavailable" is itself
   information for the approver, and the run continues.
4. **Cards render through `audit/redaction`.** Decision points quote `Evidence.excerpt`-derived
   text — untrusted, attacker-influenced content arriving at a human surface. Same pattern set
   as the gate, so the two cannot disagree about what a secret is.
5. **Fast-path proposals still get cards.** The click stays a single click; the cards sit above
   the button. Fast-path is *where the problem is worst* — a low-severity, high-confidence,
   reversible proposal is exactly the one a tired engineer approves without reading.
6. **Extraction runs on the reject path too.** A rejected proposal pages a human, and that human
   needs the path as much as an approver does. Cards attach to the `AuditRecord` either way.

### What it reads

Spans from **Triage and the Worker**. The Validator is deterministic and already reports
per-rule outcomes; its rules are not moments that required judgment, and re-describing them as
such would inflate the decision count with things the approver can already see.

### Components, in build order

Each is independently useful, which is what makes the layer cuttable in pieces.

**1. OpenTelemetry instrumentation** on the agent pipeline, using the GenAI semantic
conventions. Lands in Sprint 2 with the graph, because that is when spans first exist. Useful
for debugging regardless of everything below it, and it is what
[ADR-0009](0009-extraction-evaluation-harness.md) records to build a deterministic corpus.

**2. Rule-based extractor.** Deterministic, cheap, reliable — and written in the same idiom as
the Validator, so it is readable by anyone who has read `validator/`. Five families:

| # | Family | Fires on | Ties to |
|---|---|---|---|
| 1 | Irreversible action | `Verdict.reversible` is false, or the chosen action has no clean rollback | risk row 7 |
| 2 | External write | A span that mutates rather than reads | risk row 1 |
| 3 | Out-of-scope resource access | A span touching a resource absent from `incident.affected_resource_ids` | risk row 5 |
| 4 | Triage's `incident_type` classification | Always — it is one span | risk row 5 |
| 5 | Diagnosis changed between Worker iterations | Evidence reinterpreted mid-trajectory | risk row 3 |

Families 4 and 5 are additions to the brief's original three. Family 4 earns its place because
`incident_type` selects the playbook, and the playbook is what `injection.py` uses to constrain
every legal action downstream — it is plausibly the highest-leverage single decision in the run
and it is invisible in the current approval message. Family 5 catches the moment a trajectory
turned, which is where a reader's attention belongs.

**3. Evaluation harness.** [ADR-0009](0009-extraction-evaluation-harness.md).

**4. LLM classifier** over remaining spans, for moments where several branches were plausible
and no rule fires. **Built only if the rules alone leave the miss rate above the threshold
ADR-0009 commits to in advance.** Its output is `surfaced_by: classifier` and is visually
distinguished on the card, so a reader always knows which points are deterministic. It reads
attacker-influenced span content, so it inherits the ingestion rule: structured span attributes
in instruction position, raw excerpts as data only.

**5. Renderer.** Block Kit sections on the ADR-0005 approval message. Small, but not "no new
component" — ADR-0005 was only decided alongside this ADR, so there is no pre-existing Slack
format to reuse.

### New contracts

Described here; implemented in Sprint 3. `DecisionPoint` carries the trace and span reference,
the stage, the four answers above, `surfaced_by` (`rule:<name>` or `classifier`), and a score.
`DecisionRegisterEntry` is what ADR-0006 stores. Neither is a field on `FixProposal` —
commitment 2 forbids it.

## Consequences

**Positive:**

- The approver gets something to read. Whether they read it is not an engineering problem, but
  "there was nothing to read" stops being the answer.
- The audit log becomes a **decision register rather than an approval history** — a record of
  what was decided and on what basis, not a list of who clicked yes. That is a materially
  stronger artifact for the demo, and it is what drove ADR-0006.
- OTel instrumentation is worth having on its own merits and would be defensible even if the
  rest of this ADR is killed.
- It attacks a problem with no good published answer, which is a better use of a portfolio
  project than a fifth validator rule.

**Negative:**

- **More surface between the gate and the human.** Every commitment above exists to stop that
  surface from becoming load-bearing, but the honest statement is that the pipeline is longer
  and there is more to get wrong.
- **A card that looks authoritative and is wrong is worse than no card**, because it substitutes
  for the reading it was meant to enable. This is the layer's own version of risk row 8 and it
  is the reason ADR-0009 is a separate, non-cuttable commitment.
- Component 4 puts a model in the pipeline in a place a careless reader will mistake for the
  gate. Commitment 1 is the answer, and it has to be repeated wherever the layer is described.
- Real cost against a fixed December date, on a project that is 1 of 6 validator rules into
  Sprint 1.

## Kill criterion

If after ~10 scenarios the extractor consistently surfaces either everything or nothing useful,
the hypothesis is wrong for this domain and **the layer is dropped**. The OTel instrumentation
and the evaluation harness stay — they are valuable to Ops Sentinel independently.

Dropping it is a legitimate outcome and the retro reports it as a result, not a failure. But it
must distinguish two different findings, because they have opposite implications: *the
hypothesis is wrong*, versus *this pipeline is too small to test it*. See open question 2.

## Open questions

1. **Does a decision-point taxonomy transfer across domains?** Incident response → credit
   decisioning → legal review. Unknown, and only answerable empirically. **Recorded as open;
   deliberately not resolved here.** If it transfers, the interesting artifact is the taxonomy
   rather than this implementation.
2. **Is this pipeline's trajectory thick enough to test the hypothesis?**
   `WORKER_MAX_ITERATIONS` defaults to 5, over three action types constrained by a
   per-incident-type playbook. Extracting 3–5 decision points from that may mean the decision
   points *are* the trajectory — in which case extraction is trivially complete here and the
   result says nothing about the general case. This is the most serious threat to the value of
   the measurement and it is flagged before any of it is built.
3. **Should a fast-path proposal whose cards reveal a viable alternative be downgraded to
   strict?** That would make the extractor influence the approval path, which brushes against
   commitment 1. Left open until there are real cards to look at.
