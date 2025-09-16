# Agent Notes

This file tracks working notes for the IaC migration so context persists across sessions.

## PHASE 0 — Pre‑Flight (Inventory, Safety)
- Status: in progress
- Checklist reference: see `IAC_TODO.md` Phase 0 / Phase 1

### Snapshot: Key Identifiers
- AWS Account: (collecting…)
- Region: us-west-1
- EC2 instance: (collecting…)
- Instance role: `jb-ec2-ssm-role`
- Buckets:
  - Images: `japanesebirdcookingspaghetti-assets`
  - Artifacts: `cee-artifacts-prod-780997964150-usw1`

### Snapshot: Route 53
- cee.photography — ZoneId: (collecting…)
- hollings.photography — ZoneId: (collecting…)
- DNS TTLs (apex + www): (collecting…)

### Snapshot: Server Config
- `/etc/nginx/conf.d/cee.conf` captured (server_name mappings, feed proxy, images proxy)
- `/srv/cee/.env` essentials (AWS_DEFAULT_REGION, S3_BUCKET)
- `cee-api.service` active (uvicorn on 127.0.0.1:9002)

### Notes
- Plan to lower DNS TTLs to 60s during cutovers; record current TTLs first.
- No changes applied in Phase 0 beyond safe reads and documentation.
