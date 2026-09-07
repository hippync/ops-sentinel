"""Single source of truth for the deterministic limits.

These values are enforced outside the components they constrain (design principle 6).
They are read once here so that a limit can never disagree between the Validator, the
Executor, and the infrastructure that backstops it.

`MAX_DESIRED_COUNT` in particular has THREE enforcement points, deliberately:
  1. this Validator ceiling (rejects the proposal),
  2. ECS Service Auto Scaling max capacity (rejects the effect),
  3. the Executor's own re-check before the boto3 call.
It cannot be enforced in IAM — see docs/adr/0007-row-4-cannot-live-in-iam.md.
"""

from __future__ import annotations

import os

WORKER_MAX_ITERATIONS: int = int(os.environ.get("WORKER_MAX_ITERATIONS", "5"))
"""Risk row 3. Enforced by the graph runtime, never by the Worker itself."""

MAX_DESIRED_COUNT: int = int(os.environ.get("MAX_DESIRED_COUNT", "4"))
"""Risk row 4. See module docstring for why this needs three enforcement points."""

CONFIDENCE_FAST_PATH_MIN: float = float(os.environ.get("CONFIDENCE_FAST_PATH_MIN", "0.85"))
"""Risk row 8. The documented false-positive trade-off; chosen before the demo."""
