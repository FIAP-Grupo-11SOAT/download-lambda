terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/download-function"
  retention_in_days = 14
}

# Lambda Function
resource "aws_lambda_function" "download_processor" {
  filename         = "../download-lambda/src/main/download-lambda.zip"
  function_name    = "download-function"
  role            = var.lambda_role_arn
  handler         = "download-function.lambda_handler"
  runtime         = "python3.11"
  timeout         = 900  # 15 minutos
  memory_size     = 2048 # 2GB

  source_code_hash = filebase64sha256("../download-lambda/src/main/download-lambda.zip")

  environment {
    variables = {
      BUCKET   = "upload-bucket-11soat"
      TABLE    = "upload"
    }
  }

  ephemeral_storage {
    size = 2048 # 2GB de storage temporário
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_log_group
  ]
}