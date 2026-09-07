"""The Validator — the deterministic safety gate between proposal and execution.

This package contains NO model calls, by design (see docs/adr/0003-no-llm-in-validator.md).
A validator judged by an LLM inherits every failure mode it exists to catch.

One module per rule, one test file per module. Each maps to a numbered row in
docs/ops-sentinel-risk-register.md.
"""
