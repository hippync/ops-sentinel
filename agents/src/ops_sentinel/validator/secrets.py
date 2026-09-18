"""Risk row 2 — credentials and PII.

DESIGN FORK, resolved: this rule REJECTS. It does not scrub.

Scrubbing mutates the proposal, which changes its content-derived `proposal_hash`,
which breaks the chain the Executor verifies against — so a scrubbing gate would
quietly undermine the trust boundary in section 3.5 of the architecture. Redaction is
therefore a *rendering* concern, not a gate concern, and lives in
`ops_sentinel.audit.redaction`, applied at every human- and log-facing boundary.

  gate    -> reject the proposal outright (here)
  render  -> redact on the way to a human or the audit log (audit.redaction)

The intent is that both use the same pattern set, so the two can never disagree about
what a secret is. `SENSITIVE_PATTERNS` is that set, and it is public so that
`audit.redaction` can import it rather than restate it. **That import does not exist
yet** — `redaction.py` is still a Sprint 1 stub — so today nothing enforces the
agreement, and the test that will enforce it lands with the renderer.

What is scanned: every string *value* in the proposal, found by walking its serialised
form rather than a hand-listed set of fields — `Evidence.excerpt` is the carrier this row
names, but the Worker quotes log lines into `diagnosis` and `rollback.description` too,
and a field added to the schema later should not silently escape the scan. The derived
`proposal_hash` is excluded; it is computed, not ingested.

The failure `detail` names the pattern and the field path, and deliberately NOT the
matched value — the one place this repo's "detail names the offending value" convention
is inverted. The obvious objection is that the `AuditRecord` carries the raw proposal
anyway, so withholding here protects nothing. Three reasons it still does: `detail`
travels to surfaces the record does not, and each is its own redaction obligation (the
approval card, CLI output, exception text); `audit.redaction` is a stub, so this gate is
currently the only control there is; and once it exists, a quoted value would render as
`[REDACTED]`, carrying strictly less information than the field path already carries.
Quoting is pure downside.

`subject` stays `"proposal"`. Unlike row 1 this rule has no per-action disposition to
report: one match anywhere rejects the whole proposal, and the field path in the detail
is finer-grained than `subject` could be.

Residual risk:

* Novel secret formats not covered by the pattern set — the register's own residual.
* **Six length bounds are judgment calls, not measured values**, and every one of them is
  a row 8 false-positive/false-negative dial: `_MIN_CREDENTIAL_VALUE_CHARS` below, and the
  minimum match lengths inside `bearer_token` (16), `basic_auth_header` (16),
  `github_token` (36), `slack_token` (10) and `jwt` (8 per segment). Raising any of them
  narrows the false-positive surface and widens the corresponding miss.
* `assigned_credential` is the only general-purpose pattern, and it is where that trade is
  sharpest: an assigned value shorter than `_MIN_CREDENTIAL_VALUE_CHARS` reads as prose,
  so `token: retry` passes.
* `email_address` also matches host-qualified identifiers — `ec2-user@ip-10-0-1-7.internal`
  is rejected as PII. Those are common in ops log lines, so this is the pattern most likely
  to reject a legitimate proposal. `test_secrets.py` pins the current behaviour.
* `payment_card_number` covers the four issuer ranges under the register's "known PII
  formats", in the 4-4-4-n grouping and in Amex's 4-6-5. A long unseparated digit run
  beginning with a card prefix is a false positive — `?trace=4123456789012345` rejects;
  an issuer outside those ranges, or a grouping outside those two, is a miss.
* Detection is per-field, so a secret split across two fields matches neither.
* `_walk` yields string *values*, not dict keys. No field on `FixProposal` is a free-form
  mapping today; one added later (the shape `Incident.raw_alarm` already has) would need
  its keys walked too.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from ops_sentinel.schemas import FixProposal, RuleOutcome

RISK_ROW = 2
RULE = "secrets"

_MIN_CREDENTIAL_VALUE_CHARS = 12
"""How long an assigned value must be before `assigned_credential` calls it a credential.
A judgment call on row 8's axis, not a measured number: below it, ordinary log prose like
`token: retry` would reject a legitimate fix mid-incident."""

SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Specific shapes first, so the detail names the precise family rather than the
    # catch-all. Order is fixed, so the same input always reports the same pattern.
    ("private_key_block", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA|ABIA|ACCA|A3T[A-Z0-9])[A-Z0-9]{16}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[\w.~+/-]{16,}=*")),
    ("basic_auth_header", re.compile(r"(?i)\bbasic\s+[\w+/]{16,}={0,2}")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "database_uri_password",
        re.compile(
            r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://"
            r"[^\s:@/]+:[^\s@/]+@"
        ),
    ),
    ("us_ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "payment_card_number",
        re.compile(
            # 4-4-4-n, which covers Visa, Mastercard, Discover and an unseparated Amex...
            r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6011)[ -]?\d{4}[ -]?\d{4}[ -]?\d{2,4}\b"
            # ...and Amex's own 4-6-5 grouping, which the shape above does not match once
            # it is written out with separators, the way a card copied from a log is.
            r"|\b3[47]\d{2}[ -]?\d{6}[ -]?\d{5}\b"
        ),
    ),
    ("email_address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    (
        "assigned_credential",
        re.compile(
            r"(?i)(?:password|passwd|pwd|secrets?|tokens?|api[_-]?key|access[_-]?key"
            r"|private[_-]?key|authorization|credentials?)"
            # No leading \b: env-var names prefix these words (ADMIN_API_KEY=...), and
            # \w* after them lets a suffix follow (aws_secret_access_key_id=...).
            rf"\w*\s*[:=]\s*[\"']?\S{{{_MIN_CREDENTIAL_VALUE_CHARS},}}"
        ),
    ),
)


def check(proposal: FixProposal) -> RuleOutcome:
    """Return the outcome of the secrets rule. Never raises, and never mutates."""
    try:
        fields = list(_text_fields(proposal))
    except Exception as exc:
        # Unlike the other rules, this one serialises the proposal to walk it, so it has a
        # failure mode that pure attribute access does not. An unscannable proposal is
        # rejected, never passed: a gate that raises fails open. Only the exception type is
        # reported, for the same reason the match itself is withheld above — `str(exc)` can
        # quote the field that failed to serialise. Nothing pages on this path: the
        # rejection looks ordinary, and the audit record is what makes it discoverable.
        #
        # Only the scan is inside the `try`. Building the RuleOutcome is not, so a fault
        # there cannot re-enter this handler and escape through it.
        return _fail(
            f"Proposal could not be scanned for credentials or PII "
            f"({type(exc).__name__}); an unscannable proposal is rejected, not passed"
        )

    for path, text in fields:
        for name, pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                return _fail(
                    f"Matched the {name} pattern at {path}; the proposal is rejected rather "
                    f"than scrubbed, and the value is withheld from this detail because this "
                    f"detail reaches the audit log"
                )

    return RuleOutcome(
        rule=RULE,
        risk_row=RISK_ROW,
        passed=True,
        detail=f"No credential or PII pattern matched in {len(fields)} text fields",
    )


def _text_fields(proposal: FixProposal) -> Iterator[tuple[str, str]]:
    """Yield `(path, text)` for every string in the proposal, hash excluded."""
    payload = proposal.model_dump(mode="json", exclude={"proposal_hash"})
    yield from _walk("", payload)


def _walk(path: str, node: object) -> Iterator[tuple[str, str]]:
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(f"{path}.{key}" if path else str(key), value)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(f"{path}.{index}", value)


def _fail(detail: str) -> RuleOutcome:
    return RuleOutcome(rule=RULE, risk_row=RISK_ROW, passed=False, detail=detail)
