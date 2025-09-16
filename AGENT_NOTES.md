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
  - apex A TTL: 60
  - www CNAME TTL: 300
- hollings.photography — ZoneId: /hostedzone/Z0616182IMHS71ROTURQ
  - apex A TTL: 300
  - www CNAME TTL: 300

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
