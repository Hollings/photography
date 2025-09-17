# Import-first resource stubs. Import existing resources, then run plan.
# These blocks are protected with prevent_destroy and ignore_changes to avoid
# accidental drift. Remove ignore_changes gradually as you codify exact config.

locals {
  cee_zone_name      = "cee.photography"
  hollings_zone_name = "hollings.photography"
  assets_bucket      = "japanesebirdcookingspaghetti-assets"
  artifacts_bucket   = "cee-artifacts-prod-780997964150-usw1"
  ec2_instance_id    = "i-04bd4457fe443c716"
  ec2_role_name      = "jb-ec2-ssm-role"
  ec2_sg_id          = "sg-06af0ab526b6b570b"
  ec2_volume_id      = "vol-00fbbd879177c3638"
}

resource "aws_route53_zone" "cee" {
  name = local.cee_zone_name

  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}

resource "aws_route53_zone" "hollings" {
  name = local.hollings_zone_name

  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}

# Apex A and www CNAME for cee.photography
resource "aws_route53_record" "cee_apex_a" {
  zone_id = aws_route53_zone.cee.zone_id
  name    = local.cee_zone_name
  type    = "A"
  ttl     = 60
  records = ["52.52.3.178"]

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_route53_record" "cee_www_a" {
  zone_id = aws_route53_zone.cee.zone_id
  name    = "www.${local.cee_zone_name}"
  type    = "A"
  ttl     = 60
  records = ["52.52.3.178"]

  lifecycle {
    prevent_destroy = true
  }
}

# Apex A and www CNAME for hollings.photography
resource "aws_route53_record" "hol_apex_a" {
  zone_id = aws_route53_zone.hollings.zone_id
  name    = local.hollings_zone_name
  type    = "A"
  ttl     = 300
  records = ["52.52.3.178"]

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_route53_record" "hol_www_cname" {
  zone_id = aws_route53_zone.hollings.zone_id
  name    = "www.${local.hollings_zone_name}"
  type    = "CNAME"
  ttl     = 300
  records = ["${local.hollings_zone_name}."]

  lifecycle {
    prevent_destroy = true
  }
}

# TXT example: _atproto (if present)
resource "aws_route53_record" "cee_atproto" {
  zone_id = aws_route53_zone.cee.zone_id
  name    = "_atproto.${local.cee_zone_name}"
  type    = "TXT"
  ttl     = 300
  records = ["\"did=did:plc:xb2urvqt5f4zzccjs46hysbf\""]

  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}

# S3 buckets
resource "aws_s3_bucket" "artifacts" {
  bucket = local.artifacts_bucket

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "expire-patch-30d"
    status = "Enabled"

    filter {
      prefix = "cee/patch/"
    }

    expiration {
      days = 30
    }
  }
}

resource "aws_s3_bucket" "assets" {
  bucket = local.assets_bucket

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "assets" {
  bucket = aws_s3_bucket.assets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyListToPublic"
        Effect = "Deny"
        NotPrincipal = {
          AWS = "arn:aws:iam::780997964150:user/codex-macbook"
        }
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning",
          "s3:GetBucketAcl",
          "s3:GetBucketPolicy"
        ]
        Resource = "arn:aws:s3:::${local.assets_bucket}"
      },
      {
        Sid       = "AllowPublicReadImagesOnly"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource = [
          "arn:aws:s3:::${local.assets_bucket}/full/*",
          "arn:aws:s3:::${local.assets_bucket}/medium/*",
          "arn:aws:s3:::${local.assets_bucket}/small/*",
          "arn:aws:s3:::${local.assets_bucket}/thumbnail/*"
        ]
      }
    ]
  })
}

# IAM role used by the EC2 instance (import-only stub)
resource "aws_iam_role" "ec2_role" {
  name                 = local.ec2_role_name
  path                 = "/"
  max_session_duration = 3600

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy_attachment" "ec2_ssm_managed" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "ec2_artifacts_read" {
  name = "CeeArtifactsRead"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ArtifactsReadAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::cee-artifacts-prod-780997964150-usw1/cee/deploy/*",
          "arn:aws:s3:::cee-artifacts-prod-780997964150-usw1/cee/patch/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "ec2_assets_rw" {
  name = "S3DeployAndPhoto"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::japanesebirdcookingspaghetti-assets/deploy/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "arn:aws:s3:::japanesebirdcookingspaghetti-assets/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "ec2_assets_read" {
  name = "S3DeployRead"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::japanesebirdcookingspaghetti-assets/deploy/*"
        ]
      }
    ]
  })
}

# EC2 instance (import-only stub)
resource "aws_instance" "web" {
  ami                     = "ami-xxxxxxxx" # placeholder, ignored
  instance_type           = "t3.micro"     # placeholder, ignored
  disable_api_termination = false

  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}

# Security group protecting the instance (import-only stub)
resource "aws_security_group" "web_sg" {
  name        = "jb-web-sg"
  description = "Web SG for japanesebird"
  vpc_id      = "vpc-7d1c1b1a"

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"
    cidr_blocks = [
      "4.148.0.0/16",
      "4.149.0.0/18",
      "4.149.64.0/19",
      "4.149.96.0/19",
      "4.149.128.0/17",
      "4.150.0.0/18",
      "4.150.64.0/18",
      "4.150.128.0/18",
      "4.150.192.0/19",
      "4.150.224.0/19",
      "4.151.0.0/16",
      "4.152.0.0/15",
      "4.154.0.0/15",
      "4.156.0.0/15",
      "4.175.0.0/16",
      "4.180.0.0/16",
      "4.207.0.0/16",
      "4.208.0.0/15",
      "4.210.0.0/17",
      "4.210.128.0/17",
      "4.227.0.0/17",
      "4.227.128.0/17",
      "4.231.0.0/17",
      "4.231.128.0/17",
      "4.236.0.0/17",
      "4.236.128.0/17",
      "4.242.0.0/17",
      "4.242.128.0/17",
      "4.245.0.0/17",
      "4.245.128.0/17",
      "4.246.0.0/17",
      "4.246.128.0/17",
      "4.249.0.0/17",
      "4.249.128.0/17",
      "4.255.0.0/17",
      "4.255.128.0/17",
      "9.163.0.0/16",
      "9.169.0.0/17",
      "9.169.128.0/17",
      "9.234.0.0/17",
      "9.234.128.0/17",
      "13.64.0.0/16",
      "13.65.0.0/16",
      "13.66.0.0/17",
      "13.66.128.0/17",
      "13.67.128.0/20",
      "13.67.144.0/21",
      "13.67.152.0/24",
      "13.67.153.0/28",
      "13.67.153.32/27",
      "13.67.153.64/26",
      "13.67.153.128/25",
      "13.67.155.0/24",
      "13.67.156.0/22",
      "13.67.160.0/19",
      "13.67.192.0/18",
      "13.68.0.0/17",
      "13.68.128.0/17"
    ]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "jb-web-sg"
    Project = "japanesebird"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Root EBS volume (import-only stub)
resource "aws_ebs_volume" "root" {
  availability_zone = "us-west-1a"
  size              = 8

  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
