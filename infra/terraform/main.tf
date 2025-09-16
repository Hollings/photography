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
  records = ["0.0.0.0"] # placeholder; import will override

  lifecycle { prevent_destroy = true, ignore_changes = all }
}

resource "aws_route53_record" "cee_www_cname" {
  zone_id = aws_route53_zone.cee.zone_id
  name    = "www.${local.cee_zone_name}"
  type    = "CNAME"
  ttl     = 300
  records = [local.cee_zone_name]

  lifecycle { prevent_destroy = true, ignore_changes = all }
}

# Apex A and www CNAME for hollings.photography
resource "aws_route53_record" "hol_apex_a" {
  zone_id = aws_route53_zone.hollings.zone_id
  name    = local.hollings_zone_name
  type    = "A"
  ttl     = 300
  records = ["0.0.0.0"] # placeholder

  lifecycle { prevent_destroy = true, ignore_changes = all }
}

resource "aws_route53_record" "hol_www_cname" {
  zone_id = aws_route53_zone.hollings.zone_id
  name    = "www.${local.hollings_zone_name}"
  type    = "CNAME"
  ttl     = 300
  records = [local.hollings_zone_name]

  lifecycle { prevent_destroy = true, ignore_changes = all }
}

# TXT example: _atproto (if present)
resource "aws_route53_record" "cee_atproto" {
  zone_id = aws_route53_zone.cee.zone_id
  name    = "_atproto.${local.cee_zone_name}"
  type    = "TXT"
  ttl     = 300
  records = ["\"did=did:plc:xb2urvqt5f4zzccjs46hysbf\""]

  lifecycle { prevent_destroy = true, ignore_changes = all }
}

# S3 buckets (images + artifacts)
resource "aws_s3_bucket" "assets" {
  bucket = local.assets_bucket

  lifecycle { prevent_destroy = true, ignore_changes = all }
}

resource "aws_s3_bucket" "artifacts" {
  bucket = local.artifacts_bucket

  lifecycle { prevent_destroy = true, ignore_changes = all }
}

# IAM role used by the EC2 instance (import-only stub)
resource "aws_iam_role" "ec2_role" {
  name               = local.ec2_role_name
  assume_role_policy = jsonencode({}) # placeholder; real policy managed outside until codified

  lifecycle { prevent_destroy = true, ignore_changes = all }
}

# EC2 instance (import-only stub)
resource "aws_instance" "web" {
  ami                    = "ami-xxxxxxxx"   # placeholder, ignored
  instance_type          = "t3.micro"       # placeholder, ignored
  disable_api_termination = false

  lifecycle { prevent_destroy = true, ignore_changes = all }
}

# Security group protecting the instance (import-only stub)
resource "aws_security_group" "web_sg" {
  name   = "cee-web-sg"
  vpc_id = "vpc-xxxxxxxx" # placeholder

  lifecycle { prevent_destroy = true, ignore_changes = all }
}

# Root EBS volume (import-only stub)
resource "aws_ebs_volume" "root" {
  availability_zone = "us-west-1a"
  size              = 8

  lifecycle { prevent_destroy = true, ignore_changes = all }
}
