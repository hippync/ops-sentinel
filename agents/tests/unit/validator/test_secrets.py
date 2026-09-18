"""Risk row 2 — the secrets rule.

Two properties carry the design fork the module resolved, and each has a test here that
fails if the fork is reopened:

* `check` does not mutate the proposal — scrubbing would change `proposal_hash`;
* the rejection `detail` names the pattern and where it matched, never the matched text —
  the detail is written to the audit log, so quoting the value would leak the secret
  through the very gate that rejected it.

The example credentials below are deliberately non-functional: AWS's own documented
example key, the jwt.io sample token, and obviously fake values elsewhere.
"""

from __future__ import annotations

import pytest

from ops_sentinel.schemas import FixProposal, RuleOutcome
from ops_sentinel.validator import secrets

AKIA_EXAMPLE = "AKIAIOSFODNN7EXAMPLE"
JWT_EXAMPLE = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIn0"
    ".dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
)
# Split across the prefix on purpose. GitHub's push protection rejects a literal of this
# shape even when the value is fabricated for a test of the rule that detects it, and the
# repo would rather assemble the fixture than hold an unblock exception for a token shape.
# `secrets.check` sees the joined string, so the case it exercises is unchanged.
SLACK_EXAMPLE = "xox" + "b-1234567890-0987654321-aBcDeFgHiJkLmNoP"


def test_clean_proposal_passes(clean_proposal: FixProposal) -> None:
    outcome = secrets.check(clean_proposal)
    assert outcome.passed
    assert outcome.risk_row == 2
    assert outcome.rule == "secrets"
    assert outcome.subject == "proposal"


def test_credential_in_an_evidence_excerpt_is_rejected(clean_proposal: FixProposal) -> None:
    """`Evidence.excerpt` is raw ingested log content — the carrier this row exists for."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.evidence[0].excerpt = f"OrdersClient boot: aws_access_key_id={AKIA_EXAMPLE}"
    outcome = secrets.check(proposal)
    assert not outcome.passed
    assert "aws_access_key_id" in outcome.detail
    assert "evidence.0.excerpt" in outcome.detail
    # Pinned on the rejection path too: _fail() would otherwise be free to drift to
    # subject="action", which is the choice the module docstring spends a paragraph
    # arguing against.
    assert outcome.subject == "proposal"


def test_detail_never_quotes_the_matched_secret(clean_proposal: FixProposal) -> None:
    """The detail reaches the audit log. Naming the value would leak it past the gate.

    This is the one place the house convention ("failure detail names the offending
    value") is deliberately inverted, so it is asserted rather than assumed.
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.evidence[0].excerpt = f"boot: aws_access_key_id={AKIA_EXAMPLE}"
    outcome = secrets.check(proposal)
    assert not outcome.passed
    assert AKIA_EXAMPLE not in outcome.detail


def test_check_does_not_mutate_the_proposal(clean_proposal: FixProposal) -> None:
    """The fork this module resolved: it rejects, it does not scrub.

    A scrubbing gate would change the content-derived `proposal_hash` and break the chain
    the Executor verifies against, so an unchanged hash is the property under test.
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.evidence[0].excerpt = f"boot: aws_access_key_id={AKIA_EXAMPLE}"
    hash_before = proposal.proposal_hash

    assert not secrets.check(proposal).passed

    assert proposal.proposal_hash == hash_before
    assert AKIA_EXAMPLE in proposal.evidence[0].excerpt


def test_credential_in_the_diagnosis_is_rejected(clean_proposal: FixProposal) -> None:
    """The Worker quotes log lines into its own prose; that path carries secrets too."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.diagnosis = f"The task definition hardcodes aws_access_key_id={AKIA_EXAMPLE}."
    outcome = secrets.check(proposal)
    assert not outcome.passed
    assert "diagnosis" in outcome.detail


def test_credential_in_the_rollback_description_is_rejected(
    clean_proposal: FixProposal,
) -> None:
    """The rollback half of the proposal is rendered to a human like everything else."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.rollback.description = (
        f"Redeploy revision 42, which still carries aws_access_key_id={AKIA_EXAMPLE}."
    )
    outcome = secrets.check(proposal)
    assert not outcome.passed
    assert "rollback.description" in outcome.detail


def test_credential_in_a_later_evidence_item_is_rejected(clean_proposal: FixProposal) -> None:
    """The scan walks the whole proposal; it does not stop at the first evidence item."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.evidence.append(proposal.evidence[0].model_copy(deep=True))
    proposal.evidence[1].excerpt = f"retry with aws_access_key_id={AKIA_EXAMPLE}"
    outcome = secrets.check(proposal)
    assert not outcome.passed
    assert "evidence.1.excerpt" in outcome.detail


# (pattern name, an excerpt it must reject, the sensitive substring within that excerpt).
# The third element carries the no-leak invariant into every case: a pattern added to the
# set cannot be tested without also proving its match stays out of the audit log.
PATTERN_CASES = [
    (
        "private_key_block",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA",
        "BEGIN RSA PRIVATE KEY",
    ),
    ("aws_access_key_id", f"credentials file: {AKIA_EXAMPLE}", AKIA_EXAMPLE),
    ("jwt", f"upstream call rejected: {JWT_EXAMPLE}", JWT_EXAMPLE),
    (
        "bearer_token",
        "GET /orders authorization: Bearer 4f3c8a91b2d7e6054c1a9b8f2e7d",
        "4f3c8a91b2d7e6054c1a9b8f2e7d",
    ),
    (
        "basic_auth_header",
        "proxy sent Basic b3JkZXJzOmh1bnRlcjJodW50ZXIy",
        "b3JkZXJzOmh1bnRlcjJodW50ZXIy",
    ),
    (
        "github_token",
        "checkout failed for ghp_0123456789abcdefghijklmnopqrstuvwxyz",
        "ghp_0123456789abcdefghijklmnopqrstuvwxyz",
    ),
    ("slack_token", f"notifier init {SLACK_EXAMPLE}", SLACK_EXAMPLE),
    (
        "database_uri_password",
        "postgres://orders:hunter2hunter2@db.internal:5432/orders",
        "hunter2hunter2",
    ),
    ("us_ssn", "customer record 078-05-1120 read during checkout", "078-05-1120"),
    (
        "payment_card_number",
        "declined card 4111 1111 1111 1111 on order 8812",
        "4111 1111 1111 1111",
    ),
    # Amex's 4-6-5 grouping, which the 4-4-4-n shape misses once separators are written
    # out. A second case under the same pattern name; the 1:1 test compares name sets.
    (
        "payment_card_number",
        "declined card 3782 822463 10005 on order 8813",
        "3782 822463 10005",
    ),
    (
        "email_address",
        "order placed by jane.doe@example.com from 10.0.1.7",
        "jane.doe@example.com",
    ),
    # Deliberately well past _MIN_CREDENTIAL_VALUE_CHARS: an example sitting exactly on the
    # bound would fail here when the author raises it, in a table about patterns rather than
    # about the bound. test_the_credential_length_bound_tracks_the_constant owns that.
    (
        "assigned_credential",
        "env dump: ADMIN_API_KEY=h9Wq2LmZ4tRvX1pK7sNb3dQe",
        "h9Wq2LmZ4tRvX1pK7sNb3dQe",
    ),
]


@pytest.mark.parametrize(("pattern_name", "excerpt", "sensitive"), PATTERN_CASES)
def test_each_pattern_family_is_rejected(
    clean_proposal: FixProposal, pattern_name: str, excerpt: str, sensitive: str
) -> None:
    """One case per entry in the shared pattern set, named so the audit log is readable.

    Asserts the no-leak invariant for every pattern, not only the one in
    `test_detail_never_quotes_the_matched_secret` — the regression risk is highest on
    whichever pattern is added next.
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.evidence[0].excerpt = excerpt
    outcome = secrets.check(proposal)
    assert not outcome.passed
    assert pattern_name in outcome.detail
    assert sensitive not in outcome.detail


def test_every_pattern_in_the_set_has_a_case_here() -> None:
    """The pattern set and this file stay 1:1, so adding a pattern cannot skip its test.

    `audit/redaction.py` is intended to render with the same set once it is built, so an
    untested pattern here would become an untested redaction there too.
    """
    assert {name for name, _, _ in PATTERN_CASES} == {
        name for name, _ in secrets.SENSITIVE_PATTERNS
    }


def test_the_scan_covers_the_ingested_fields_and_excludes_the_derived_hash(
    clean_proposal: FixProposal,
) -> None:
    """Asserted on the walk directly, because `check` cannot observe it.

    No pattern in the set can match a 64-character hex digest, so removing the exclusion
    would change no verdict — which would leave the docstring's claim about it untested.
    """
    paths = {path for path, _ in secrets._text_fields(clean_proposal)}
    assert "proposal_hash" not in paths
    assert {"diagnosis", "rollback.description", "evidence.0.excerpt"} <= paths


def test_prose_mentioning_a_credential_keyword_passes(clean_proposal: FixProposal) -> None:
    """The deliberate false-negative edge of the keyword pattern (risk row 8's trade-off).

    A short assigned value is prose, not a credential. Rejecting this line would block a
    legitimate fix mid-incident over the word "token".
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.evidence[0].excerpt = "token: retry after backoff"
    assert secrets.check(proposal).passed


def test_the_credential_length_bound_tracks_the_constant(clean_proposal: FixProposal) -> None:
    """Both sides of the bound, derived from the constant rather than from a literal.

    Hard-coded example lengths would pin the constant only to a range, so the author could
    change it and every test would still pass while the documented behaviour moved.
    """
    bound = secrets._MIN_CREDENTIAL_VALUE_CHARS
    proposal = clean_proposal.model_copy(deep=True)

    proposal.evidence[0].excerpt = f"token: {'x' * (bound - 1)}"
    assert secrets.check(proposal).passed

    proposal.evidence[0].excerpt = f"token: {'x' * bound}"
    outcome = secrets.check(proposal)
    assert not outcome.passed
    assert "assigned_credential" in outcome.detail


def test_a_host_qualified_identifier_is_rejected_as_an_email(
    clean_proposal: FixProposal,
) -> None:
    """Pins the open question in `email_address`'s residual bullet, in its current direction.

    `user@host` is ordinary in ops log lines, so this is the pattern most likely to reject a
    legitimate proposal (risk row 8). The author may want it inverted; this test is here so
    that inverting it is a visible decision rather than a silent drift.
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.evidence[0].excerpt = "ec2-user@ip-10-0-1-7.internal restarted the task"
    outcome = secrets.check(proposal)
    assert not outcome.passed
    assert "email_address" in outcome.detail


def test_an_unscannable_proposal_is_rejected_not_passed(
    clean_proposal: FixProposal, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate's own failure mode. Unlike the other rules, this one serialises first.

    Garbage strings do not make `model_dump` fail, so `test_check_never_raises` cannot
    reach this path; only a raising `model_dump` can.
    """

    def boom(*args: object, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("unserialisable field")

    monkeypatch.setattr(FixProposal, "model_dump", boom)
    outcome = secrets.check(clean_proposal)
    assert not outcome.passed
    assert "could not be scanned" in outcome.detail


def test_an_ordinary_timestamped_log_line_passes(clean_proposal: FixProposal) -> None:
    """The over-reach case: dates, latencies and status codes are digits, not PII.

    A gate that rejected this would be rejected by its users instead (risk row 8).
    """
    proposal = clean_proposal.model_copy(deep=True)
    proposal.evidence[0].excerpt = (
        "2026-09-07 12:00:00,123 ERROR OrderController 502 after 1234 ms, attempt 3"
    )
    assert secrets.check(proposal).passed


def test_check_never_raises(clean_proposal: FixProposal) -> None:
    """The gate must return a verdict, not an exception. A crashing validator fails open."""
    proposal = clean_proposal.model_copy(deep=True)
    proposal.diagnosis = ""
    proposal.evidence[0].excerpt = "\x00\udcff ��� " * 64
    outcome = secrets.check(proposal)
    assert isinstance(outcome, RuleOutcome)
    assert isinstance(outcome.passed, bool)

    proposal.evidence[0].excerpt += f" aws_access_key_id={AKIA_EXAMPLE}"
    assert secrets.check(proposal).passed is False
