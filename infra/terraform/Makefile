SHELL := /bin/bash
TFDIR := $(shell pwd)

.PHONY: help bootstrap init import plan

help:
	@echo "Targets:"
	@echo "  bootstrap  - create remote state S3 bucket + DynamoDB lock table (run once)"
	@echo "  init       - terraform init with backend.hcl"
	@echo "  import     - show import commands (set APPLY=1 to execute)"
	@echo "  plan       - terraform plan (requires imports and backend configured)"

bootstrap:
	cd bootstrap && terraform init && terraform apply -auto-approve \
	  -var "state_bucket_name=cee-tf-state-usw1" \
	  -var "lock_table_name=cee-tf-locks"

init:
	terraform init -backend-config=backend.hcl

import:
	./import_route53_s3.sh

plan:
	terraform plan

