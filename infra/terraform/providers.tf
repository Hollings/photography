variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-1"
}

provider "aws" {
  region = var.aws_region
}

