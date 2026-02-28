terraform {
  backend "s3" {
    bucket         = "my-real-estate-dp-tf-state"
    key            = "dev/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}