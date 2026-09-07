"""Risk row 2 — credentials and PII.

DESIGN FORK, resolved: this rule REJECTS. It does not scrub.

Scrubbing mutates the proposal, which changes its content-derived `proposal_hash`,
which breaks the chain the Executor verifies against — so a scrubbing gate would
quietly undermine the trust boundary in section 3.5 of the architecture. Redaction is
therefore a *rendering* concern, not a gate concern, and lives in
`ops_sentinel.audit.redaction`, applied at every human- and log-facing boundary.

  gate    -> reject the proposal outright (here)
  render  -> redact on the way to a human or the audit log (audit.redaction)

Both use the same pattern set so the two can never disagree about what a secret is.

Residual risk: novel secret formats not covered by the pattern set.
"""

from __future__ import annotations

from ops_sentinel.schemas import FixProposal, RuleOutcome

RISK_ROW = 2
RULE = "secrets"


def check(proposal: FixProposal) -> RuleOutcome:
    raise NotImplementedError("Sprint 1")
