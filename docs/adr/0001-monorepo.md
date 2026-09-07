# ADR-0001 — Monorepo over split repos

**Status:** Accepted · **Date:** 2026-09-07

## Context
Ops Sentinel has three deployable parts: the Python agent pipeline, the Java sandbox app it watches,
and the Terraform that provisions both. These could be separate repositories.

## Decision
One repository, with `agents/`, `sandbox-app/`, `infra/`, and `docs/` as top-level directories.

## Rationale
- The chaos triggers in `sandbox-app/` map 1:1 to rows in the risk register, and the Validator's
  tests consume incidents that app produces. Split repos allow version skew between an injected
  failure and the test asserting it's defended — precisely the coupling that must not drift.
- `infra/` provisions the app *and* the CloudWatch alarms and EventBridge rule that trigger the
  pipeline. Splitting it means one repo's `terraform apply` owns resources the other depends on.
- This is a portfolio project. One link, one README, one history showing the whole system. The Java
  app alone is unremarkable; its value is being the thing the agents watch.

## Consequences
- CI must path-filter so a Java change doesn't run the Python suite and vice versa.
- If the sandbox app is ever reused elsewhere, extracting it is a real (if bounded) cost.
- The split-repo benefits — independent release cadence, per-team access, smaller CI surface —
  require multiple teams or cadences to matter. Neither applies to a solo one-semester project.
