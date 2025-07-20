import mimetypes
from pathlib import Path

from config import AWS_REGION, S3_BUCKET, logger, s3_client

class S3Storage:
    def __init__(self, bucket: str = S3_BUCKET, region: str = AWS_REGION):
        self.bucket = bucket
        self.region = region
        self.client = s3_client

    def public_url(self, key: str) -> str:
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"

    def upload_file(self, path: Path, key: str) -> str:
        mimetype, _ = mimetypes.guess_type(path.name)
        logger.info("Uploading %s → %s", path.name, key)
        self.client.upload_file(
            str(path),
            self.bucket,
            key,
            ExtraArgs={"ACL": "public-read", "ContentType": mimetype or "application/octet-stream"},
        )
        return self.public_url(key)

    def delete_file(self, key: str) -> None:
        logger.info("Deleting key=%s from S3", key)
        self.client.delete_object(Bucket=self.bucket, Key=key)
