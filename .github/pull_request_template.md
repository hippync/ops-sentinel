## What changed

<!-- One or two sentences. -->

## Risk register

<!-- Which numbered rows in docs/ops-sentinel-risk-register.md does this touch? "None" is a
     valid answer, but say it explicitly rather than leaving this blank. -->

Rows touched:

- [ ] This change does **not** widen the Executor's IAM scope
- [ ] This change does **not** introduce a path from Worker to Executor that skips the Validator
- [ ] This change does **not** put model judgment inside the Validator (ADR-0003)
- [ ] If it adds a new `ActionType`, `infra/policies/executor-policy.json` is updated to match

## Testing

<!-- What proves this works? For a Validator rule: the violation fixture it now rejects. -->
