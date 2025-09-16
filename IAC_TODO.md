# Infra-as-Code Migration TODO

Scope: codify the current cee.photography stack and safely migrate to managed TLS/routing with clear rollback at each step. No changes should be applied without a successful dry-run and a written revert path.

## Phase 0 — Pre‑Flight (Inventory, Safety)
- [x] Confirm AWS account/region (780997964150, us-west-1) and active profile for automation.
- [x] Snapshot current server config: `/etc/nginx/conf.d/cee.conf` (server_name lines), `/srv/cee/.env` (key vars), `systemctl status cee-api.service` (excerpt).
- [x] Note critical IDs: EC2 `i-04bd4457fe443c716`, role `jb-ec2-ssm-role`, buckets: images `japanesebirdcookingspaghetti-assets`, artifacts `cee-artifacts-prod-780997964150-usw1`.
- [x] Route53 zones: `cee.photography`, `hollings.photography` (record sets for apex + www) and TTLs.
- [ ] Set low DNS TTLs (60s) on apex/www A/CNAME during migration windows.

## Phase 1 — Terraform Baseline (Import Live)
- [x] Create Terraform backend S3 state bucket: `cee-tf-state-780997964150-usw1`
- [x] Configure S3 backend without DynamoDB locking (optional to add later)
- [x] Scaffold repo: providers (AWS), remote state, and modules (`route53`, `s3`, `iam`, `ec2`, `ssm`).
- [x] Import Route53 hosted zones (cee + hollings) and their A/CNAME/TXT records.
- [x] Import S3 buckets: images (public read on image prefixes only), artifacts (private, SSE-S3, lifecycle).
  - [x] Images bucket (japanesebirdcookingspaghetti-assets): imported
  - [x] Artifacts bucket (cee-artifacts-prod-780997964150-usw1): imported
- [x] Import IAM instance role `jb-ec2-ssm-role` and policy attachments (S3 images r/w, artifacts read, SSM).
- [x] Import EC2 instance, Security Group(s), and any EBS volumes.
- [ ] Write exact resource definitions to match current live configuration (policies, lifecycle, SG rules, tags).
- [x] Run `terraform plan` → expect NO CHANGES; fix drift in code until plan is empty.
- [ ] Add CI job: plan on PR, apply on main (manual approval optional).
- [ ] Rollback plan: retain backups; if something is off, do not apply. Revert code or state to previous commit.

### Phase 1 — Hygiene
- [ ] Unify Terraform tree at `infra/terraform`; archive/remove `source/photography/infra/terraform` to avoid drift.
- [ ] Add drift-only CI: on push to `infra/terraform/**`, run `terraform plan` (no imports) and fail on drift; always upload plan artifacts.

### Optional Hardening in Phase 1
- [ ] Allocate and attach an Elastic IP to the EC2 instance.
- [ ] Update apex A records (both zones) to the EIP via Terraform.
- [ ] Rollback: point A back to old public IP (TTL=60), detach/release EIP later.

## Phase 2A — Managed TLS + ALB (Canary on hollings)
- [ ] Provision ACM cert (DNS-validated) for `hollings.photography` + `www` (Route53 validation).
- [ ] Create ALB + Security Group + Target Group; register existing EC2 backend.
- [ ] ALB listener 443 (hollings ACM) → TG; health check defined (see notes for options).
- [ ] Route53 A/ALIAS for hollings apex + www → ALB.
- [ ] ALB rule: block `/manage` for Host=hollings.* (404).
- [ ] Manual canary cutover on hollings; verify TLS, /photos, /feed.xml, /images.
- [ ] Rollback: flip A/ALIAS back to instance IP (TTL=60), ALB remains for retry.

## Phase 2B — ALB + ACM (cee) after canary is stable
- [ ] ACM cert for `cee.photography` + `www`.
- [ ] ALB 443 listener (cee ACM) → TG.
- [ ] Route53 A/ALIAS for cee apex + www → ALB.
- [ ] Confirm `/manage` allowed only on cee.
- [ ] Rollback: flip records back to instance IP.

## Phase 2B — CloudFront + S3 for SPA (Optional, start with hollings)
- [ ] Create private S3 SPA buckets: `spa-cee.photography`, `spa-hollings.photography` (OAC/OAI restricted).
- [ ] Create CloudFront distributions (in us-east-1 ACM) with alternate CNAMEs per domain.
- [ ] Behaviors: `/images/*` → images S3 origin; `/feed.xml` and `/photos*` → ALB origin; `/*` → SPA origin.
- [ ] CI: upload SPA build to S3 and issue CloudFront invalidations on deploy.
- [ ] Flip hollings CNAME to CloudFront; validate; rollback by pointing back to apex/ALB.
- [ ] Repeat for cee when satisfied.

## Phase 3 — ECS Fargate Backend (Optional)
- [ ] Create ECR repo and CI step to build/push backend image.
- [ ] Terraform ECS cluster, task definition (env from SSM), service behind ALB TG.
- [ ] Register EC2 and ECS in separate target groups; shift traffic gradually.
- [ ] Rollback: shift ALB weight back to EC2 target group.

## Cross‑Cutting Enhancements
- [ ] Move app config from `.env` to SSM Parameter Store (secure strings); load at boot.
- [ ] Enable CloudWatch Logs (Nginx + Uvicorn via CW agent) and ALB/CF access logs.
- [ ] Add alarms: 5xx spikes, instance memory pressure, disk space, cert expiry (if any).
- [ ] Document `/manage` access (cee only) and ensure it is blocked on hollings (ALB or app layer).

## Validation & Rollback Playbook
- [ ] Pre/post deploy checks: `systemctl status`, `journalctl`, Nginx test, local curls to backend.
- [ ] DNS flips have explicit rollback: ALIAS/CNAME back to previous target; TTL=60 during changes.
- [ ] Nginx config changes keep `.bak` and reload only after `nginx -t` passes; revert with single mv + reload.
- [ ] Keep EC2 path intact until ALB/ECS paths are proven; never decommission the old path without a tested fallback.

Notes:
- Start with Phase 1 only if schedule is tight; it stops drift without changing traffic.
- Use hollings.photography for canary in Phase 2 to avoid impacting cee.photography.
