import logging
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

# Normalize to a standard ASCII hyphen in default
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-west-1")
S3_BUCKET  = os.getenv("S3_BUCKET")
DB_URL     = os.getenv("DATABASE_URL", "sqlite:///photos.db")
LOG_LEVEL  = os.getenv("LOG_LEVEL", "INFO").upper()

if not S3_BUCKET:
    raise RuntimeError("S3_BUCKET must be set")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("photo_service")

# Use default AWS credential resolution (env, instance profile, etc.)
s3_client = boto3.client("s3", region_name=AWS_REGION)
