# Infrastructure

Terraform for the sandbox AWS account. Two things live here, and the second is the
reason this directory is in version control rather than the console:

1. **The sandbox app's runtime** — ECS Fargate, RDS Postgres, ALB, CloudWatch, EventBridge
2. **The Executor's IAM role** — scoped at deploy time to its exact known action set

## Why the IAM policy is a reviewed artifact

Risk row 6 is the strongest guarantee in the system, and it is the only one that doesn't
depend on the Validator being correct. Even a fully manipulated agent cannot act outside
the action list in [`policies/executor-policy.json`](policies/executor-policy.json).

That property only holds if the policy is reviewed rather than accumulated. Console clicks
and `"just in case"` permissions are exactly how ad hoc agent tooling ends up over-privileged.
So: the policy is a file, changes to it are diffs, and the action set it grants must match
the `ActionType` enum in `agents/src/ops_sentinel/schemas/models.py`. If those two drift,
the guarantee is gone.

## Listener split — deliberate

| Listener | Reaches | Exposure |
|---|---|---|
| Public ALB | Orders API only | Internet |
| Internal | Orders API **and** `/admin/chaos/*` | VPN / SSM port-forward only |

Chaos triggers must never be on the public listener. This is asserted in the Terraform,
not left to convention.

## Layout

```
terraform/
  modules/          reusable pieces (extract only if flat config gets unwieldy — see cut-lines)
  envs/sandbox/     the single v1 environment
policies/
  executor-policy.json   minimum-privilege IAM for the Executor
```

## Usage

```bash
cd terraform/envs/sandbox
terraform init
terraform plan     # always read the plan; this touches IAM
terraform apply
```

**Never commit:** `*.tfstate`, `*.tfvars` with real values, or an admin API key.
