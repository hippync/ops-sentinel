# Sandbox environment

The single v1 environment. Built in Sprint 3 — see [`docs/sprints.md`](../../../../docs/sprints.md).

Planned contents:

- VPC with public and private subnets
- ECS Fargate service running `orders-sandbox`
- RDS Postgres for Orders data
- ALB: **public listener → Orders API only**; internal listener carries `/admin/chaos/*`
- CloudWatch: Container Insights, log groups, alarms on 5xx rate and memory utilization
- EventBridge rule: alarm state change → pipeline invocation
- Executor IAM role from `infra/policies/executor-policy.json` — nothing broader
