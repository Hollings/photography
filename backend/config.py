import logging
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us‑east‑1")
S3_BUCKET  = os.getenv("S3_BUCKET")
AWS_KEY    = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.getenv("AWS_SECRET_ACCESS_KEY")
DB_URL     = os.getenv("DATABASE_URL", "sqlite:///photos.db")
LOG_LEVEL  = os.getenv("LOG_LEVEL", "INFO").upper()

if not all([S3_BUCKET, AWS_KEY, AWS_SECRET]):
    raise RuntimeError(
        "S3_BUCKET, AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set"
    )

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y‑%m‑%d %H:%M:%S",
)
logger = logging.getLogger("photo_service")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET,
)
