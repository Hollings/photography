#!/usr/bin/env bash
set -euo pipefail

# Imports Route53 zones/records and S3 buckets into Terraform state.
# Dry-run by default; set APPLY=1 to execute imports.

AWS_REGION=${AWS_REGION:-us-west-1}
APPLY=${APPLY:-0}

say() { printf "\033[1;34m%s\033[0m\n" "$*"; }
do_or_echo() {
  if [[ "$APPLY" == "1" ]]; then
    eval "$1"
  else
    echo "$1"
  fi
}

# Import helper: only import if address not already in state
import_if_missing() {
  local addr="$1"; shift
  local id="$1"; shift || true
  if terraform state list | grep -qx "$addr"; then
    echo "skip: $addr already in state"
  else
    do_or_echo "terraform import $addr $id"
  fi
}

say "Discovering Route53 zone IDs..."
CEE_ZONE=$(aws route53 list-hosted-zones-by-name --dns-name cee.photography --query 'HostedZones[0].Id' --output text)
HOL_ZONE=$(aws route53 list-hosted-zones-by-name --dns-name hollings.photography --query 'HostedZones[0].Id' --output text)

CEE_ZONE="${CEE_ZONE#/hostedzone/}"
HOL_ZONE="${HOL_ZONE#/hostedzone/}"

if [[ -z "$CEE_ZONE" || -z "$HOL_ZONE" || "$CEE_ZONE" == "None" || "$HOL_ZONE" == "None" ]]; then
  echo "ERROR: Could not resolve hosted zone IDs."
  exit 1
fi

say "Importing zones..."
import_if_missing aws_route53_zone.cee ${CEE_ZONE}
import_if_missing aws_route53_zone.hollings ${HOL_ZONE}

say "Importing cee.photography records..."
import_if_missing aws_route53_record.cee_apex_a ${CEE_ZONE}_cee.photography._A
import_if_missing aws_route53_record.cee_www_a ${CEE_ZONE}_www.cee.photography._A
import_if_missing aws_route53_record.cee_atproto ${CEE_ZONE}__atproto.cee.photography._TXT

say "Importing hollings.photography records..."
import_if_missing aws_route53_record.hol_apex_a ${HOL_ZONE}_hollings.photography._A
import_if_missing aws_route53_record.hol_www_cname ${HOL_ZONE}_www.hollings.photography._CNAME

say "Importing S3 buckets..."
import_if_missing aws_s3_bucket.assets japanesebirdcookingspaghetti-assets
import_if_missing aws_s3_bucket.artifacts cee-artifacts-prod-780997964150-usw1

say "Done. If this was a dry run, re-run with APPLY=1 to execute."

say "Importing IAM role and EC2 instance (stubs)..."
import_if_missing aws_iam_role.ec2_role jb-ec2-ssm-role
import_if_missing aws_instance.web i-04bd4457fe443c716
import_if_missing aws_security_group.web_sg sg-06af0ab526b6b570b
import_if_missing aws_ebs_volume.root vol-00fbbd879177c3638
