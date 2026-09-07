# Architecture Decision Records

One file per decision that has actually been made: the context, the choice, and what it
costs. An ADR is written *when the decision is taken*, not reserved in advance — an ADR
whose Decision section reads "not yet made" is an issue wearing a costume, and a
directory of those reads as padding.

Open questions live in GitHub issues labelled `decision`, and become ADRs on resolution.

Format: `NNNN-short-title.md`. Status is `Proposed`, `Accepted`, or `Superseded by NNNN`.

| # | Decision | Status |
|---|---|---|
| [0001](0001-monorepo.md) | Monorepo over split repos | Accepted |
| [0002](0002-langgraph-orchestration.md) | LangGraph for orchestration | Accepted, conditional on 0004/0005 |
| [0003](0003-no-llm-in-validator.md) | No LLM in the Validator | Accepted |
| [0004](0004-pipeline-runtime.md) | Where the pipeline runs | **Proposed — blocks 0002** |
| [0007](0007-row-4-cannot-live-in-iam.md) | Row 4's ceiling cannot be enforced in IAM | Accepted |

0005 (approval surface) and 0006 (audit log store) were removed from this directory and
tracked as issues until they are decided.
