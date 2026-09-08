# ADR-0009 — Evaluation harness for decision-point extraction

**Status:** Accepted · **Date:** 2026-09-08

**Measures:** [ADR-0008](0008-decision-point-extraction.md). Separate from it deliberately — the
measurement approach is its own architectural commitment, and it survives ADR-0008's kill
criterion.

## Context and problem statement

Anyone can wire an LLM to traces and produce plausible-looking decision cards. Almost nobody can
state how often their system misses what mattered. The second thing is the deliverable; the
first is a demo.

This matters more here than it would elsewhere, because ADR-0008's failure mode is *a card that
looks authoritative and is wrong* — output that substitutes for the reading it was meant to
enable. That is the project's own problem statement — "plausible-looking output with no signal
about whether it's safe to trust" — reproduced one layer up. Shipping the extraction layer
without a measured miss rate would be the sharpest possible self-inflicted wound.

So: **a published miss rate on a reproducible harness, plus the curve between that rate and the
number of decision points surfaced.** Nothing measurable is claimed until it is measured; every
number in this ADR is a target or a protocol, not a result.

## Decision drivers

- A reviewer must be able to clone the repo and reproduce the number. A metric that requires the
  author's AWS account is a screenshot, not a measurement.
- The harness must survive the kill criterion. If extraction is dropped, this stays.
- It must be honest about its own validity, in a repo whose credibility rests on naming its own
  gaps before a reviewer finds them ([ADR-0007](0007-row-4-cannot-live-in-iam.md) is the
  precedent).

## Considered options

**Live AWS sandbox, scenarios seeded against real ECS and CloudWatch.** Rejected. It puts the
headline deliverable behind Sprint 5, which `docs/sprints.md` names as cut-line #1 by deliberate
resequence — infrastructure is cuttable, the gate is not. It costs ~$65/mo while running, and no
reviewer can reproduce it. The project already decided that everything demoable is built against
recorded payloads with zero AWS spend; this follows that decision rather than reopening it.

**Live model in the loop, scenarios replayed end to end.** Rejected as the primary measurement —
see "Trajectory variance" below. Retained as a secondary measurement.

**Recorded payloads + recorded spans + the fake executor.** Chosen.

## Decision

### Scenarios

**~20 seeded incident scenarios**, each a recorded alarm payload plus recorded read-only tool
responses, driven through the pipeline with the fake AWS backend from Sprint 3. These are the
same fixtures [`scripts/replay-alarm.sh`](../../scripts/README.md) already needs, extended —
not a second corpus.

Each scenario has **one known critical decision**: the moment where, had the pipeline chosen
differently, the outcome would have materially differed.

### Metric

**Miss rate** = the fraction of scenarios in which the labeled critical decision does not appear
among the surfaced decision points. Recall against a known target.

This is recall only, and the ADR says so rather than implying more. Precision is not measured
because there is no ground truth for "this surfaced point was not worth surfacing" — one labeled
decision per scenario supports "did you find it," not "how much noise did you add." The curve
below is what stands in for the precision question.

### Trajectory variance — measured separately, not folded in

With a model in Triage and the Worker, the same scenario yields a different trajectory run to
run. Folding that into the miss rate would mean the headline number carries variance from a
component the extractor does not control.

So the harness has two tiers:

- **Tier 1 — extraction accuracy (the published number).** Trajectories are recorded once as
  span sets and committed as fixtures. Extraction is measured over those fixed spans, so the
  measurement is deterministic and a reviewer's run reproduces the author's exactly.
- **Tier 2 — trajectory stability.** The same scenarios re-run live, N times, reporting how
  often the labeled decision *appears in the trajectory at all*. This is a property of the
  pipeline, not the extractor, and it bounds what tier 1 can mean.

Reporting a single number that silently mixes the two would be the kind of unexamined metric
this project exists to argue against.

### Labeling protocol

The critical decision for each scenario is labeled **before any extraction rule is written**,
and committed in a **separate, earlier commit** than the extractor. The commit history is the
evidence that the targets were not fitted to the rules.

This is a partial mitigation, not a fix — see open question 1.

### Reproducibility

The harness runs in CI on the fixture corpus, and writes results to a committed file so the
miss rate moves in diffs and its history is visible. `pytest`, no AWS credentials, no Slack
workspace — [ADR-0005](0005-approval-surface.md)'s CLI approval path exists partly for this.

### The threshold that gates component 4

ADR-0008 builds the LLM classifier **only if the rules alone leave the miss rate too high.**
"Too high" is a number **chosen and written down before the first measurement**, in the same
discipline risk row 8 already applies to false-positive tolerance: *decided now, not justified
later.* The number itself is not set in this ADR — see open question 3.

## Consequences

**Positive:**

- The harness is the deliverable that outlives the layer. If ADR-0008's kill criterion fires,
  this remains as the thing that made the kill decision defensible.
- It generalises: a reproducible corpus of recorded pipeline trajectories with labeled critical
  moments is reusable for anything else that reads trajectories.
- It forces the extraction work to be falsifiable, which is the property that distinguishes it
  from the plausible-card version.

**Negative:**

- Fixtures drift. Recorded spans encode the pipeline's shape at the moment of recording; a
  Sprint 5 change to Triage silently invalidates them. The harness must fail loudly on schema
  drift rather than quietly measuring a stale corpus.
- **Recorded trajectories are not live trajectories.** Tier 2 exists to bound this and does not
  eliminate it.
- Labeling 20 scenarios is real work, and it is the least interesting work in the layer.

## Open questions

These are flagged rather than resolved. Each must be closed before the number is published.

1. **Labeling validity — the largest threat to the headline number.** One person labels the
   critical decisions *and* writes the rules that must find them. The
   label-before-rules-in-an-earlier-commit protocol is a real constraint but not independence. A
   second labeler on a subset, or labels drawn from an independent source, would be stronger.
   Unresolved, and the published number must carry this caveat rather than bury it.

2. **The curve has no dial yet.** "The curve between miss rate and number of decision points
   surfaced" requires a ranking, and boolean rules produce a *set*, not a ranking — there is
   nothing to sweep. Two candidate dials, which measure different things:
   - each rule emits a score, and the curve sweeps top-k;
   - the curve sweeps rule-family subsets (which of the five families are enabled).
   The first answers "how many points must I show to catch it," the second answers "which rules
   earn their place." Both are useful; the deliverable as stated implies the first.

3. **The gating threshold is undefined.** The miss rate above which component 4 gets built has
   to be a number, chosen before measuring. It is not chosen here.

4. **The kill criterion needs an operational form.** ADR-0008 says "consistently surfaces either
   everything or nothing useful" after ~10 scenarios. That needs a test — e.g. *≥N of 10
   scenarios where the surfaced count is 0, or equals every eligible span.* N is undecided.

5. **Rule family 2 ("external write") is nearly empty in v1.** The Worker is read-only by
   design, so it fires almost exclusively on the proposed action — which the Validator already
   inspects and the approver already sees. It may contribute nothing to the miss rate, and the
   harness should be able to report that per family rather than only in aggregate.

6. **Scenario diversity is bounded by the domain.** Three incident types and three action types
   means ~20 scenarios is roughly seven per incident type. Whether that supports a *published*
   rate — as opposed to an internal one used to make the kill decision — is a real question, and
   the answer affects how the number should be presented.
