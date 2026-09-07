# Infrastructure

Terraform for the sandbox AWS account. Two things live here, and the second is the
reason this directory is in version control rather than the console:

1. **The sandbox app's runtime** — ECS Fargate, RDS Postgres, ALB, CloudWatch, EventBridge
2. **The Executor's IAM role** — scoped at deploy time to its exact known action set

---

## Cost — budgeted, because row 4 would be ironic otherwise

Risk row 4 is "runaway infrastructure cost." A project that enforces a spend ceiling on
its agent and has none of its own is making an argument it doesn't apply to itself.

Estimated monthly, running continuously:

| Item | ~USD/mo | Note |
|---|---|---|
| ECS Fargate (1 task, 0.5 vCPU / 1 GB) | 30 | |
| ALB | 18 | |
| RDS Postgres `t4g.micro` | 13 | |
| ~~NAT Gateway~~ | ~~32~~ → **0** | **Avoided — see below** |
| CloudWatch logs/metrics | ~3 | Container Insights is the bulk |
| **Total** | **~65** | Down from ~97 |

**The NAT gateway decision.** A NAT gateway would be the single largest line item, and it
exists only to give private-subnet tasks outbound internet. For a sandbox, Fargate tasks
run in **public subnets with `assignPublicIp: ENABLED` and tight security groups**:
equivalent isolation in practice, ~$32/mo saved, and one sentence to defend. This is a
sandbox trade-off and would not be made in production.

**Teardown is part of the demo runbook**, not an afterthought: `terraform destroy` runs
after each recorded demo. The environment is not left standing between sprints.

---

## Why the IAM policy is a reviewed artifact

Risk row 6 is the strongest guarantee in the system. That property only holds if the
policy is reviewed rather than accumulated — console clicks and "just in case"
permissions are exactly how ad hoc agent tooling ends up over-privileged. So: the policy
is a file, changes to it are diffs, and [`scripts/check_iam_scope.py`](../scripts/check_iam_scope.py)
fails CI if it drifts from the `ActionType` enum in either direction.

### Two honest caveats

Both were found by review and are stated here rather than left for a reader to discover:

1. **`ecs:UpdateService` is one IAM action covering all three `ActionType`s**, plus the
   ability to point the service at any task-definition revision in the account. IAM
   cannot tell a rollback from a restart from a scale. Row 6's guarantee is real but
   coarser than "one IAM action per action type."
2. **Risk row 4's ceiling cannot be enforced in IAM at all** — AWS exposes no condition
   key for `desiredCount` on `UpdateService`. It is enforced in the Validator, in ECS
   Service Auto Scaling max capacity, and in the Executor's re-check instead. See
   [ADR-0007](../docs/adr/0007-row-4-cannot-live-in-iam.md).

`application-autoscaling:*` is deliberately **not** granted to the Executor, so the agent
cannot raise its own ceiling.

---

## Listener split — deliberate, and not a boundary on its own

| Listener | Reaches | Exposure |
|---|---|---|
| Public ALB | Orders API only | Internet |
| Internal | Orders API **and** `/admin/chaos/*` | VPN / SSM port-forward only |

Both listeners hit the same target group and the same container port, so the split is a
network control, not an application one. `/admin/**` is therefore **also** enforced in
the app (admin key filter, and the app refuses to boot with chaos enabled and a blank
key). Layered enforcement is the argument the rest of the project makes; it applies here
too.

---

## Layout

```
terraform/
  modules/          reusable pieces (extract only if flat config gets unwieldy)
  envs/sandbox/     the single v1 environment
policies/
  executor-policy.json   minimum-privilege IAM — no comments, AWS rejects unknown keys
  action-mapping.json    ActionType -> IAM actions, with the known weaknesses recorded
```

## Usage

```bash
cd terraform/envs/sandbox
terraform init
terraform plan     # always read the plan; this touches IAM
terraform apply
terraform destroy  # after each demo — see the cost note above
```

**Never commit:** `*.tfstate`, `*.tfvars` with real values, or an admin API key.
