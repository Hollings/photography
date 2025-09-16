# Terraform Skeleton (prod)

This directory contains a minimal, import‑first Terraform layout to codify the
current cee.photography infrastructure without changing traffic. The pattern is:

1) Bootstrap remote state (S3 + DynamoDB) — optional if you already have these
2) Init Terraform with backend
3) Import existing resources (Route53 zones/records, S3 buckets)
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

If plan shows drift, stop and adjust the stubs (or add ignore_changes) before any apply.

## Notes
- The resource stubs have `prevent_destroy` and `ignore_changes = all` to safely assume
  management. Remove `ignore_changes` gradually as you codify exact attributes (policies,
  lifecycle rules, etc.) and validate plans.
- EC2/IAM are included as stubs to complete the baseline; they are set to ignore all changes so
  plans should be no‑diff after import. We’ll codify exact attributes later.
