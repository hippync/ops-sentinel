"""Executor — deterministic execution of an approved proposal.

NO LLM. A dispatch table from ActionType to a boto3 call, nothing more.

Re-verifies the approval record and proposal hash before acting rather than trusting
what it is handed; a mismatch is dropped and logged as a security event, since it
indicates a bypass attempt.

The supported action set IS the IAM policy in infra/policies/ (risk row 6) — the
strongest guarantee in the system, and the one that holds even if the Validator is
wrong.
"""
