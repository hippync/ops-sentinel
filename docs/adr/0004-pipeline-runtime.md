# ADR-0004 — Where the pipeline runs

**Status:** Proposed · **Date:** 2026-09-07

## Context
Lambda (cold starts, 15-min ceiling vs a capped Worker loop), a long-running ECS task, or Step Functions wrapping LangGraph nodes. Cost, cold-start behavior under a capped retry loop, and how cleanly the audit trail falls out each differ.

## Decision
Not yet made.

## Next step
Resolve in Sprint 3, once the EventBridge trigger is real.
