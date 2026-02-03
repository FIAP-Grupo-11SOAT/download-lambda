variable "aws_region" {
  description = "AWS region to deploy Lambda"
  type        = string
  default     = "us-east-1"
}

variable "lambda_path" {
  description = "Path to Lambda Node file (relative to the infra directory)"
  type        = string
  default = "../lanchonete_lambda/authorization/lanchonete_lambda.zip"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "media-processor"
}

variable "lambda_role_arn" {
  description = "ARN of the IAM Role for Lambda"
  type        = string
  default     = "arn:aws:iam::961624804946:role/lambda-role"
}
