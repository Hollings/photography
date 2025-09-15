Deploy Notes

- Buckets
  - `ASSETS_BUCKET`: Public-read for image prefixes only (`full/`, `medium/`, `small/`, `thumbnail/`). Nginx proxies `/images/*` to this bucket. Backend writes originals/variants here.
  - `ARTIFACTS_BUCKET`: Private bucket for deploy artifacts (`cee/deploy/*`, `cee/patch/*`). Used by GitHub Actions to upload build outputs and by SSM on the instance to download them.

- GitHub Actions
  - Workflow: `.github/workflows/deploy.yml`
  - Upload step pushes artifacts to `ARTIFACTS_BUCKET`.
  - SSM deploy step downloads from `ARTIFACTS_BUCKET`, but writes app env `S3_BUCKET` using `ASSETS_BUCKET` (so the app still targets the images bucket).
  - Cleanup step deletes artifacts from `ARTIFACTS_BUCKET`.

- Instance
  - `/srv/cee/.env` contains `S3_BUCKET` (images bucket) and region.
  - `/etc/nginx/conf.d/cee.conf` proxies `/images/*` to `${ASSETS_BUCKET}.s3.${AWS_REGION}.amazonaws.com`.

Security posture
  - Images bucket policy allows public `GetObject` only on the four image prefixes; ListBucket is denied.
  - Artifacts bucket has public access blocked and default SSE-S3 encryption.

