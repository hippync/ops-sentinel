"""Redaction at rendering boundaries.

`Evidence.excerpt` carries raw ingested log content, which is where secrets and PII enter
the pipeline. It reaches the AuditRecord — and the audit trail is a demo deliverable
shown on a screen. Rejecting a proposal at the gate (validator.secrets) does not remove
that content from the record of the rejection.

So: the gate rejects, and this module redacts everything on its way to a human, a log, or
the demo.

This module will import `validator.secrets.SENSITIVE_PATTERNS` rather than restate it, so
that the two cannot disagree about what a secret is. That import lands with this module —
today it is a stub, and nothing enforces the agreement.
"""

from __future__ import annotations

from ops_sentinel.schemas import AuditRecord

REDACTED = "[REDACTED]"


def redact_audit_record(record: AuditRecord) -> AuditRecord:
    """Return a copy safe to render. Never mutates the original."""
    raise NotImplementedError("Sprint 1")
