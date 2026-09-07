# ADR-0004 — Where the pipeline runs

**Status:** Proposed — **blocks [ADR-0002](0002-langgraph-orchestration.md)**
**Date opened:** 2026-09-07 · **Must be decided:** before any orchestration code (Sprint 1)

## Context

Three candidates, and the choice interacts with the approval gate rather than being
independent of it:

| Option | Fits if | Problem |
|---|---|---|
| Lambda | The run is short and approval is out-of-process | 15-minute ceiling sits awkwardly against a capped retry loop; cold starts |
| Long-running ECS task | The pipeline holds state in memory across the approval pause | Pays for idle; a crash during the pause loses the run unless checkpointed anyway |
| Step Functions wrapping LangGraph nodes | Durable state and human approval are wanted at the AWS layer | Two orchestrators; LangGraph collapses to a node body, which would supersede ADR-0002 |

## Why this blocks 0002

ADR-0002's load-bearing argument is durable suspend/resume across a human approval. If
this ADR lands on Step Functions, AWS provides that and the LangGraph dependency loses
its justification. Deciding the orchestration library before the runtime was backwards;
this note records the correction.

## Next step

Decide in Sprint 1, alongside the approval-surface issue, before orchestration code is
written. Prototype the pause: the deciding question is what happens to an in-flight run
when the process dies while waiting for a human.
