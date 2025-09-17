# Terraform Skeleton (prod)

This directory contains a minimal, import‑first Terraform layout to codify the
current cee.photography infrastructure without changing traffic. The pattern is:

1) Bootstrap remote state (S3 + DynamoDB) — optional if you already have these
2) Init Terraform with backend
3) Import existing resources (Route53 zones/records, S3 buckets, IAM, EC2)
4) Run plan (expect no changes). Only then consider expanding coverage

No terraform apply is expected until imports are clean and plans are zero‑diff.

## Layout
- `bootstrap/` — creates the S3 state bucket + DynamoDB lock table (run once)
- `backend.hcl` — remote state configuration (fill with your bucket/table)
- `providers.tf`, `versions.tf` — provider & version pins
- `main.tf` — resource stubs for import (Route53 zones/records, S3 buckets)
- `import_route53_s3.sh` — helper to import live R53/S3 into state (dry‑run by default)

## Quickstart (import‑only)
1. Bootstrap state (optional — or use an existing state bucket/table):

   cd bootstrap
   terraform init
   terraform apply -auto-approve -var "state_bucket_name=cee-tf-state-usw1" -var "lock_table_name=cee-tf-locks"

2. Configure backend (edit `backend.hcl` as needed), then init at repo root:

   cd ..
   terraform init -backend-config=backend.hcl

3. Create an empty state and import Route53 + S3 + IAM/EC2 (dry run prints commands):

   ./import_route53_s3.sh           # prints import commands
   APPLY=1 ./import_route53_s3.sh   # executes the imports

4. Plan (expect no changes):

   terraform plan

If plan shows drift, stop and adjust the stubs before any apply.

## Notes
- Many resources started life as import-only stubs with `prevent_destroy`. As you encode
  real configuration (Route53 targets, S3 lifecycle/SSE, IAM role policies, SG ingress/egress)
  drop the blanket `ignore_changes` and rely on Terraform for drift detection.
- `import_route53_s3.sh` skips addresses already in state and now covers S3 encryption/lifecycle
  plus IAM role policy attachments and inline policies.
- The assets bucket stays gated behind `TF_VAR_manage_assets_bucket` until we have IAM access
  and a codified public-access posture.
