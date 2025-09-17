# Agent Notes

This file tracks working notes for the IaC migration so context persists across sessions.

## PHASE 0 — Pre‑Flight (Inventory, Safety)
- Status: in progress
- Checklist reference: see `IAC_TODO.md` Phase 0 / Phase 1

### Snapshot: Key Identifiers
- AWS Account: 780997964150
- ARN: arn:aws:iam::780997964150:user/codex-macbook
- Region: us-west-1
- EC2 instance: i-04bd4457fe443c716
- Public IP: 52.52.3.178
- Instance role: `jb-ec2-ssm-role`
- Buckets:
  - Images: `japanesebirdcookingspaghetti-assets`
  - Artifacts: `cee-artifacts-prod-780997964150-usw1`

### Snapshot: Route 53
- cee.photography — ZoneId: /hostedzone/Z01435361IWP4CZW2QPIX
  - apex A TTL: 60 → 52.52.3.178
  - www A TTL: 60 → 52.52.3.178
- hollings.photography — ZoneId: /hostedzone/Z0616182IMHS71ROTURQ
  - apex A TTL: 300 → 52.52.3.178
  - www CNAME TTL: 300 → hollings.photography

### Snapshot: Server Config
- server_name lines:

```
7:  server_name cee.photography www.cee.photography;
15:  server_name ALT_cee.photography WWW_ALT_cee.photography;
23:  server_name www.cee.photography;
32:  server_name cee.photography;
```

- .env (first 10 lines):

```
CEE_API_VERSION=0.1.0
DATABASE_URL=sqlite:////srv/cee/data/photos.db
AWS_DEFAULT_REGION=us-west-1
S3_BUCKET=japanesebirdcookingspaghetti-assets
```

- `cee-api.service` active (uvicorn on 127.0.0.1:9002)

#### cee-api.service (status excerpt)

```
● cee-api.service - cee.photography FastAPI service
     Loaded: loaded (/etc/systemd/system/cee-api.service; enabled; preset: disabled)
     Active: active (running) since Tue 2025-09-16 05:28:45 UTC; ~now
     Main PID: uvicorn
     Notes: Uvicorn running on http://127.0.0.1:9002
```

### Notes
- Plan to lower DNS TTLs to 60s during cutovers; record current TTLs first.
- No changes applied in Phase 0 beyond safe reads and documentation.
- Local Terraform runs via `AWS_PROFILE=codex` + Terraform 1.6.6 (provider pinned to ~>5.67).

## PHASE 1 — Terraform Baseline (Scaffold)
- Status: baseline captured — S3 backend configured; imports succeeded; plan is zero‑diff
- Path: `infra/terraform` in this repo
- Contents:
  - bootstrap/main.tf — creates remote state S3 bucket + DynamoDB lock table (optional)
  - backend.hcl — remote state config (fill with names), then `terraform init -backend-config=backend.hcl`
  - providers.tf, versions.tf — AWS provider + pins
  - main.tf — codified Route53 zones/records, S3 buckets, IAM role, and security group
  - import_route53_s3.sh — helper that discovers zone IDs and prints/imports terraform import commands

Next steps:
- [ ] (Optional) Run bootstrap to create state bucket/table
- [ ] Init backend; run import script (dry-run first), then with APPLY=1
- [ ] terraform plan (expect no changes); adjust stubs if any drift shows

#### CI Workflow
- Added GitHub Actions workflow: `.github/workflows/infra-import-plan.yml`
  - Steps: bootstrap state (S3/Dynamo), terraform init, import (Route53 + S3), plan
  - Trigger: Manual (workflow_dispatch) or push to `infra/terraform/**`
  - Uses repo AWS secrets (same as deploy) and region `us-west-1`
  - Artifacts: uploads plan files (plan.txt, plan-full.txt)

To run:
1) In GitHub Actions, run “Infra Import and Plan” (keep apply_imports=true)
2) Review plan artifacts; we expect zero changes

State naming (for clarity):
- S3 state bucket: `cee-tf-state-780997964150-usw1`
- DynamoDB lock table: (omitted for now; backend configured without locking)

Backend status:
- S3-only backend (no DynamoDB lock) to minimize required IAM
- Remote state bucket: `cee-tf-state-780997964150-usw1`

### Import commands (dry‑run output)

```
terraform import aws_route53_zone.cee /hostedzone/Z01435361IWP4CZW2QPIX
terraform import aws_route53_zone.hollings /hostedzone/Z0616182IMHS71ROTURQ
terraform import aws_route53_record.cee_apex_a /hostedzone/Z01435361IWP4CZW2QPIX_cee.photography._A
terraform import aws_route53_record.cee_www_cname /hostedzone/Z01435361IWP4CZW2QPIX_www.cee.photography._CNAME
terraform import aws_route53_record.cee_atproto /hostedzone/Z01435361IWP4CZW2QPIX__atproto.cee.photography._TXT
terraform import aws_route53_record.hol_apex_a /hostedzone/Z0616182IMHS71ROTURQ_hollings.photography._A
terraform import aws_route53_record.hol_www_cname /hostedzone/Z0616182IMHS71ROTURQ_www.hollings.photography._CNAME
terraform import aws_s3_bucket.artifacts cee-artifacts-prod-780997964150-usw1
terraform import aws_s3_bucket_server_side_encryption_configuration.artifacts cee-artifacts-prod-780997964150-usw1
terraform import aws_s3_bucket_lifecycle_configuration.artifacts cee-artifacts-prod-780997964150-usw1
terraform import aws_iam_role_policy_attachment.ec2_ssm_managed jb-ec2-ssm-role/arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
terraform import aws_iam_role_policy.ec2_artifacts_read jb-ec2-ssm-role:CeeArtifactsRead
terraform import aws_iam_role_policy.ec2_assets_rw jb-ec2-ssm-role:S3DeployAndPhoto
terraform import aws_iam_role_policy.ec2_assets_read jb-ec2-ssm-role:S3DeployRead
terraform import aws_iam_role.ec2_role jb-ec2-ssm-role
terraform import aws_instance.web i-04bd4457fe443c716
terraform import aws_security_group.web_sg sg-06af0ab526b6b570b
terraform import aws_ebs_volume.root vol-00fbbd879177c3638
```

Notes:
- “www.cee.photography” is an A record (not CNAME) and is modeled/imported accordingly.
- Import scripts are idempotent (skip addresses already in state).

## PHASE 1 — Hygiene (Planned)
- Unify Terraform to `infra/terraform`; retire the duplicate `source/photography/infra/terraform` tree to avoid drift.
- Add drift-only CI on pushes to `infra/terraform/**` that runs plan and fails on drift; always upload plan artifacts.
- (Optional) Add DynamoDB state locking once IAM allows CreateTable.

## PHASE 2 — ALB + ACM (Plan)
Objective: serve both domains behind an ALB with ACM TLS and keep /manage only on cee.

Adds:
- ACM certs (DNS-validated) per domain.
- One ALB with host-based listeners (443): hollings and cee certs.
- Target Group attaching existing EC2.
- Route53 A/ALIAS for apex + www per domain → ALB.
- ALB fixed-response rule (404) for `/manage` on Host=hollings.*

Health check options (choose one):
- HTTPS 443 → `/feed.xml` with host header override to each domain (valid certs exist).
- HTTP 80 → `/health` if we add a non-redirect exception in Nginx.

Rollout sequence:
1) Canary hollings only → verify; rollback is a single Route53 flip to instance IP.
2) Cut over cee → verify /manage and feed; rollback similarly.
- Images bucket import: still gated — bucket policy denies `s3:GetBucket*`; need temporary allow or manual dump before codifying.
