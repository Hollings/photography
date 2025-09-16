# Remote state backend (fill with your actual bucket/table before init)
bucket         = "cee-tf-state-usw1"
key            = "prod/terraform.tfstate"
region         = "us-west-1"
dynamodb_table = "cee-tf-locks"
encrypt        = true

